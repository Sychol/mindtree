from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.display import DisplaySnapshotResponse
from app.services.display import stream_display_snapshots
from app.services.display_aggregate import build_display_snapshot

router = APIRouter()


@router.get(
    "/events/{eventSlug}/display/snapshot",
    response_model=DisplaySnapshotResponse,
    response_model_exclude_none=True,
)
def read_display_snapshot(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> DisplaySnapshotResponse:
    return build_display_snapshot(db, event_slug)


@router.get("/events/{eventSlug}/stream")
def stream_display(
    request: Request,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    initial_snapshot = build_display_snapshot(db, event_slug)
    return StreamingResponse(
        stream_display_snapshots(
            event_slug=event_slug,
            request=request,
            initial_snapshot=initial_snapshot,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
