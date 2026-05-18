import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    internal_error_handler,
    validation_error_handler,
)
from app.db.session import SessionLocal, get_engine
from app.workers.keyword_worker import run_once

logger = logging.getLogger(__name__)


def _run_keyword_worker_batch(limit: int):
    db = SessionLocal(bind=get_engine())
    try:
        return run_once(db, limit=limit)
    finally:
        db.close()


async def _keyword_worker_loop() -> None:
    settings = get_settings()
    interval = max(settings.keyword_worker_interval_seconds, 1)
    limit = settings.keyword_worker_batch_size

    while True:
        try:
            summary = await asyncio.to_thread(_run_keyword_worker_batch, limit)
            if summary.claimed_count:
                logger.info(
                    "keyword_worker_batch claimed=%s succeeded=%s retry_wait=%s failed=%s excluded=%s fallback_used=%s keywords=%s",
                    summary.claimed_count,
                    summary.succeeded_count,
                    summary.retry_wait_count,
                    summary.failed_count,
                    summary.excluded_count,
                    summary.fallback_used_count,
                    summary.created_keyword_count,
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("keyword worker batch failed")

        await asyncio.sleep(interval)
from app.core.logging import setup_logging


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        worker_task = None
        if settings.keyword_worker_enabled:
            worker_task = asyncio.create_task(_keyword_worker_loop())
            app.state.keyword_worker_task = worker_task
            logger.info("keyword worker background loop started")
        try:
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task

    app = FastAPI(
        title="Maeumnamu API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
