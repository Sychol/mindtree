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


def main() -> None:
    settings = get_settings()

    if _env_flag("AUTO_MIGRATE"):
        _run_step(["alembic", "upgrade", "head"])

    if _should_seed_dev():
        _run_step([sys.executable, "-m", "app.scripts.seed_dev"])
    elif _env_flag("AUTO_BOOTSTRAP_ADMIN"):
        _run_step([sys.executable, "-m", "app.scripts.bootstrap_admin"])

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
