from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.replies import CreateReplyRequest, CreateReplyResponse
from app.services.replies import create_reply

router = APIRouter()


@router.post("/sessions/{sessionId}/replies", response_model=CreateReplyResponse)
def create_session_reply(
    payload: CreateReplyRequest,
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> CreateReplyResponse:
    return create_reply(db, session_id, payload)
