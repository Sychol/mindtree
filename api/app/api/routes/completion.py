from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.completion import CompletionCodeResponse
from app.services.completion import get_completion_code

router = APIRouter()


@router.get(
    "/sessions/{sessionId}/completion-code",
    response_model=CompletionCodeResponse,
)
def read_completion_code(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> CompletionCodeResponse:
    return get_completion_code(db, session_id)
