from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from time import monotonic

from fastapi import Request

from app.core.config import get_settings
from app.db.session import SessionLocal, get_engine
from app.schemas.display import DisplaySnapshotResponse
from app.services.display_aggregate import build_display_snapshot
from app.services.sse import format_sse_event


def snapshot_to_event(snapshot: DisplaySnapshotResponse) -> str:
    return format_sse_event(
        "keyword_snapshot",
        snapshot.model_dump(mode="json", exclude_none=True),
    )


def heartbeat_event() -> str:
    return format_sse_event(
        "heartbeat",
        {
            "status": "ok",
            "generatedAt": datetime.now(timezone.utc),
        },
    )


async def stream_display_snapshots(
    *,
    event_slug: str,
    request: Request,
    initial_snapshot: DisplaySnapshotResponse,
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    snapshot_interval = max(settings.display_snapshot_interval_seconds, 1)
    heartbeat_interval = max(settings.display_sse_heartbeat_seconds, 1)
    last_heartbeat_at = monotonic()

    yield snapshot_to_event(initial_snapshot)

    while True:
        if await request.is_disconnected():
            break

        await asyncio.sleep(snapshot_interval)
        if await request.is_disconnected():
            break

        db = SessionLocal(bind=get_engine())
        try:
            snapshot = build_display_snapshot(db, event_slug)
        finally:
            db.close()

        yield snapshot_to_event(snapshot)

        if monotonic() - last_heartbeat_at >= heartbeat_interval:
            yield heartbeat_event()
            last_heartbeat_at = monotonic()
