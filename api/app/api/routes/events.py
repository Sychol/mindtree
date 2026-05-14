from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.events import PublicEventResponse
from app.services.events import get_public_event

router = APIRouter()


@router.get("/events/{eventSlug}/public", response_model=PublicEventResponse)
def read_public_event(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> PublicEventResponse:
    return get_public_event(db, event_slug)
