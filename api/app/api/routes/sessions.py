from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.sessions import (
    ConsentRequest,
    ConsentResponse,
    CreateOrResumeSessionRequest,
    CreateOrResumeSessionResponse,
    SessionResponse,
)
from app.services.consent import accept_consent
from app.services.sessions import create_or_resume_session, get_session_state

router = APIRouter()


@router.post(
    "/events/{eventSlug}/sessions",
    response_model=CreateOrResumeSessionResponse,
)
def create_or_resume_event_session(
    payload: CreateOrResumeSessionRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
) -> CreateOrResumeSessionResponse:
    return create_or_resume_session(db, event_slug, payload)


@router.get("/sessions/{sessionId}", response_model=SessionResponse)
def read_session_state(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return get_session_state(db, session_id)


@router.post("/sessions/{sessionId}/consent", response_model=ConsentResponse)
def create_session_consent(
    payload: ConsentRequest,
    request: Request,
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> ConsentResponse:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return accept_consent(db, session_id, payload, ip_address, user_agent)
