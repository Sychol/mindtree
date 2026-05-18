from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_survey import (
    AdminSurveyMutationResponse,
    AdminSurveyResponse,
    SurveyConsentUpdateRequest,
    SurveyIntroUpdateRequest,
    SurveyQuestionPresentationUpdateRequest,
    SurveyResetRequest,
    SurveySectionUpdateRequest,
    SurveyThanksUpdateRequest,
)
from app.services.survey_config import (
    get_admin_survey_config,
    reset_survey_config,
    update_consent,
    update_intro,
    update_question_presentation,
    update_section,
    update_thanks,
)

router = APIRouter(prefix="/admin")


@router.get("/events/{eventSlug}/survey", response_model=AdminSurveyResponse)
def read_admin_survey(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyResponse:
    return get_admin_survey_config(db, event_slug)


@router.patch(
    "/events/{eventSlug}/survey/intro",
    response_model=AdminSurveyMutationResponse,
)
def patch_admin_survey_intro(
    payload: SurveyIntroUpdateRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyMutationResponse:
    return update_intro(db, event_slug, payload, current_admin)


@router.patch(
    "/events/{eventSlug}/survey/consent",
    response_model=AdminSurveyMutationResponse,
)
def patch_admin_survey_consent(
    payload: SurveyConsentUpdateRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyMutationResponse:
    return update_consent(db, event_slug, payload, current_admin)


@router.patch(
    "/events/{eventSlug}/survey/sections/{sectionId}",
    response_model=AdminSurveyMutationResponse,
)
def patch_admin_survey_section(
    payload: SurveySectionUpdateRequest,
    event_slug: str = Path(alias="eventSlug"),
    section_id: str = Path(alias="sectionId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyMutationResponse:
    return update_section(db, event_slug, section_id, payload, current_admin)


@router.patch(
    "/events/{eventSlug}/survey/questions/{questionNo}/presentation",
    response_model=AdminSurveyMutationResponse,
)
def patch_admin_survey_question_presentation(
    payload: SurveyQuestionPresentationUpdateRequest,
    event_slug: str = Path(alias="eventSlug"),
    question_no: int = Path(alias="questionNo"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyMutationResponse:
    return update_question_presentation(db, event_slug, question_no, payload, current_admin)


@router.patch(
    "/events/{eventSlug}/survey/thanks",
    response_model=AdminSurveyMutationResponse,
)
def patch_admin_survey_thanks(
    payload: SurveyThanksUpdateRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyMutationResponse:
    return update_thanks(db, event_slug, payload, current_admin)


@router.post(
    "/events/{eventSlug}/survey/reset",
    response_model=AdminSurveyMutationResponse,
)
def post_admin_survey_reset(
    payload: SurveyResetRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminSurveyMutationResponse:
    return reset_survey_config(db, event_slug, current_admin, payload)
