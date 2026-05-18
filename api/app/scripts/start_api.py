from __future__ import annotations

import os
import subprocess
import sys

from app.core.config import get_settings


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _run_step(args: list[str]) -> None:
    print(f"startup_step {' '.join(args)}", flush=True)
    subprocess.run(args, check=True)


def _dev_seed_exists() -> bool:
    from sqlalchemy import func, select

    from app.db.session import SessionLocal, get_engine
    from app.models.event import Event
    from app.models.question import Question
    from app.scripts.seed_dev import EVENT_SLUG
    from app.scripts.seed_questions import EXPECTED_QUESTION_COUNT

    with SessionLocal(bind=get_engine()) as db:
        event = db.execute(select(Event).where(Event.slug == EVENT_SLUG)).scalar_one_or_none()
        if event is None:
            return False

        question_count = db.execute(
            select(func.count(Question.id)).where(Question.event_id == event.id)
        ).scalar_one()
        return int(question_count or 0) >= EXPECTED_QUESTION_COUNT


def _should_seed_dev() -> bool:
    raw_value = os.getenv("AUTO_SEED_DEV", "false").strip().lower()
    if raw_value in {"missing", "if_missing", "auto"}:
        if _dev_seed_exists():
            print("startup_step seed_dev skipped existing_seed=true", flush=True)
            return False
        return True
    return raw_value in {"1", "true", "yes", "y", "on", "force"}


def _should_seed_dummy_content() -> bool:
    if not _env_flag("AUTO_SEED_DUMMY_CONTENT"):
        return False

    app_env = os.getenv("APP_ENV", "local").strip().lower()
    if app_env == "production" and not _env_flag("DUMMY_CONTENT_ALLOW_PRODUCTION"):
        print(
            "startup_step seed_dummy_content skipped production_without_explicit_allow=true",
            flush=True,
        )
        return False

    return True


def _dummy_content_seed_args() -> list[str]:
    return [
        sys.executable,
        "-m",
        "app.scripts.seed_dummy_content",
        "--event-slug",
        os.getenv("DUMMY_CONTENT_EVENT_SLUG", "fire-expo-2026"),
        "--cards",
        os.getenv("DUMMY_CONTENT_CARDS", "100"),
        "--replies",
        os.getenv("DUMMY_CONTENT_REPLIES", "100"),
        "--keywords",
        os.getenv("DUMMY_CONTENT_KEYWORDS", "100"),
        "--batch-label",
        os.getenv("DUMMY_CONTENT_BATCH_LABEL", "dummy-content-v1"),
        "--mode",
        os.getenv("DUMMY_CONTENT_SEED_MODE", "missing"),
    ]


def main() -> None:
    settings = get_settings()

    if _env_flag("AUTO_MIGRATE"):
        _run_step(["alembic", "upgrade", "head"])

    if _should_seed_dev():
        _run_step([sys.executable, "-m", "app.scripts.seed_dev"])
    elif _env_flag("AUTO_BOOTSTRAP_ADMIN"):
        _run_step([sys.executable, "-m", "app.scripts.bootstrap_admin"])

    if _should_seed_dummy_content():
        _run_step(_dummy_content_seed_args())

    host = os.getenv("API_HOST", settings.api_host)
    port = os.getenv("API_PORT", str(settings.api_port))
    os.execvp(
        "uvicorn",
        [
            "uvicorn",
            "app.main:app",
            "--host",
            host,
            "--port",
            str(port),
        ],
    )


if __name__ == "__main__":
    main()
