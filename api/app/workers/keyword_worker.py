from __future__ import annotations

import time
from collections.abc import Callable

from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import get_settings
from app.services.keywords.job_runner import KeywordJobRunSummary, process_next_jobs


def run_once(db: SQLAlchemySession, *, limit: int | None = None) -> KeywordJobRunSummary:
    return process_next_jobs(db, limit=limit)


def run_loop(
    db_factory: Callable[[], SQLAlchemySession],
    *,
    interval_seconds: int | None = None,
    limit: int | None = None,
) -> None:
    settings = get_settings()
    interval = interval_seconds or settings.keyword_worker_interval_seconds
    while True:
        db = db_factory()
        try:
            run_once(db, limit=limit)
        finally:
            db.close()
        time.sleep(max(interval, 1))
