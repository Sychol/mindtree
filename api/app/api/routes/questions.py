from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.questions import QuestionsResponse
from app.services.questions import get_event_questions

router = APIRouter()


@router.get("/events/{eventSlug}/questions", response_model=QuestionsResponse)
def read_event_questions(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> QuestionsResponse:
    return get_event_questions(db, event_slug)
