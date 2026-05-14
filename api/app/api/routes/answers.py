from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.answers import BulkAnswerRequest, BulkAnswerResponse
from app.services.answers import save_bulk_answers

router = APIRouter()


@router.put("/sessions/{sessionId}/answers/bulk", response_model=BulkAnswerResponse)
def save_session_answers(
    payload: BulkAnswerRequest,
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> BulkAnswerResponse:
    return save_bulk_answers(db, session_id, payload)
