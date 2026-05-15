from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.db.session import SessionLocal, get_engine
from app.workers.keyword_worker import run_loop, run_once


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run keyword job worker.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Process one batch and exit.")
    mode.add_argument("--loop", action="store_true", help="Process batches until interrupted.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum jobs per batch.")
    parser.add_argument("--interval", type=int, default=None, help="Loop interval in seconds.")
    return parser


def _new_db_session():
    return SessionLocal(bind=get_engine())


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    settings = get_settings()
    limit = args.limit or settings.keyword_worker_batch_size

    if args.once:
        db = _new_db_session()
        try:
            summary = run_once(db, limit=limit)
        finally:
            db.close()
        print(
            "claimed={claimed} succeeded={succeeded} retry_wait={retry_wait} "
            "failed={failed} excluded={excluded} fallback_used={fallback_used} keywords={keywords}".format(
                claimed=summary.claimed_count,
                succeeded=summary.succeeded_count,
                retry_wait=summary.retry_wait_count,
                failed=summary.failed_count,
                excluded=summary.excluded_count,
                fallback_used=summary.fallback_used_count,
                keywords=summary.created_keyword_count,
            )
        )
        return

    try:
        run_loop(
            _new_db_session,
            interval_seconds=args.interval or settings.keyword_worker_interval_seconds,
            limit=limit,
        )
    except KeyboardInterrupt:
        print("keyword worker stopped")


if __name__ == "__main__":
    main()
