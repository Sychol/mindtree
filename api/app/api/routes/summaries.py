from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.summaries import SummaryResponse, SummaryViewedResponse
from app.services.summaries import get_or_create_summary, mark_summary_viewed

router = APIRouter()


@router.get("/sessions/{sessionId}/summary", response_model=SummaryResponse)
def read_session_summary(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> SummaryResponse:
    return get_or_create_summary(db, session_id)


@router.post(
    "/sessions/{sessionId}/summary/viewed",
    response_model=SummaryViewedResponse,
)
def mark_session_summary_viewed(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> SummaryViewedResponse:
    return mark_summary_viewed(db, session_id)
