from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.events import PublicEventResponse
from app.schemas.survey_content import PublicSurveyContentResponse
from app.services.events import get_public_event
from app.services.survey_config import get_public_survey_content

router = APIRouter()


@router.get("/events/{eventSlug}/public", response_model=PublicEventResponse)
def read_public_event(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> PublicEventResponse:
    return get_public_event(db, event_slug)


@router.get("/events/{eventSlug}/survey-content", response_model=PublicSurveyContentResponse)
def read_public_survey_content(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> PublicSurveyContentResponse:
    return get_public_survey_content(db, event_slug)
