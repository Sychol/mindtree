from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.core.security import generate_resume_token, hash_token
from app.models.enums import EventStatus, SessionStatus
from app.models.event import Event
from app.models.session import Session
from app.repositories.card_selections import CardSelectionRepository
from app.repositories.cards import MindCardRepository
from app.repositories.completion_codes import CompletionCodeRepository
from app.repositories.consent import ConsentRepository
from app.repositories.events import EventRepository
from app.repositories.replies import ReplyRepository
from app.repositories.sessions import SessionRepository
from app.schemas.sessions import (
    CreateOrResumeSessionRequest,
    CreateOrResumeSessionResponse,
    SessionInfo,
    SessionProgress,
    SessionResponse,
)

CLIENT_META_ALLOWLIST = {"device", "timezone"}
STATUS_ORDER = [
    SessionStatus.CREATED.value,
    SessionStatus.CONSENTED.value,
    SessionStatus.QUESTIONS_COMPLETED.value,
    SessionStatus.SUMMARY_VIEWED.value,
    SessionStatus.CARD_CREATED.value,
    SessionStatus.REPLY_CREATED.value,
    SessionStatus.COMPLETED.value,
]


def status_at_least(current_status: str, target_status: str) -> bool:
    try:
        return STATUS_ORDER.index(current_status) >= STATUS_ORDER.index(target_status)
    except ValueError:
        return False


def build_session_info(session: Session, event: Event) -> SessionInfo:
    return SessionInfo(
        id=session.id,
        event_slug=event.slug,
        status=session.status,
        last_step=session.last_step or "landing",
        completed_at=session.completed_at,
    )


def _filter_client_meta(client_meta: dict) -> dict[str, str]:
    filtered_meta: dict[str, str] = {}
    for key in CLIENT_META_ALLOWLIST:
        value = client_meta.get(key)
        if isinstance(value, str) and value.strip():
            filtered_meta[key] = value.strip()[:64]
    return filtered_meta


def _get_event_or_raise(db: SQLAlchemySession, event_slug: str) -> Event:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return event


def create_or_resume_session(
    db: SQLAlchemySession,
    event_slug: str,
    request: CreateOrResumeSessionRequest,
) -> CreateOrResumeSessionResponse:
    event = _get_event_or_raise(db, event_slug)
    session_repository = SessionRepository(db)

    resume_token = request.resume_token or generate_resume_token()
    resume_token_hash = hash_token(resume_token)
    existing_session = session_repository.get_by_resume_token_hash(event.id, resume_token_hash)
    if existing_session is not None:
        return CreateOrResumeSessionResponse(
            session=build_session_info(existing_session, event),
            resume_token=resume_token,
        )

    # TODO(phase04+): finalize closed-event behavior for existing unfinished sessions.
    if event.status != EventStatus.OPEN.value:
        raise AppError(
            ErrorCode.EVENT_NOT_OPEN,
            "세션을 생성할 수 있는 이벤트 상태가 아닙니다.",
            status.HTTP_403_FORBIDDEN,
            details={"status": event.status},
        )

    client_meta = _filter_client_meta(request.client_meta)
    try:
        session = session_repository.create_session(
            event_id=event.id,
            anonymous_key_hash=resume_token_hash,
            resume_token_hash=resume_token_hash,
            client_meta=client_meta,
        )
        db.commit()
        db.refresh(session)
    except IntegrityError:
        db.rollback()
        session = session_repository.get_by_anonymous_key_hash(event.id, resume_token_hash)
        if session is None:
            raise

    return CreateOrResumeSessionResponse(
        session=build_session_info(session, event),
        resume_token=resume_token,
    )


def get_session_state(db: SQLAlchemySession, session_id: UUID) -> SessionResponse:
    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    session, event = row
    consent_accepted = ConsentRepository(db).exists_for_session(session.id) or status_at_least(
        session.status,
        SessionStatus.CONSENTED.value,
    )
    mind_card_count = MindCardRepository(db).count_by_session_id(session.id)
    selected_card = CardSelectionRepository(db).get_by_session_id(session.id) is not None
    reply_created = (
        ReplyRepository(db).count_by_session_id(session.id) > 0
        or status_at_least(session.status, SessionStatus.REPLY_CREATED.value)
    )
    completion_code_issued = CompletionCodeRepository(db).get_by_session_id(session.id) is not None

    return SessionResponse(
        session=build_session_info(session, event),
        progress=SessionProgress(
            consent_accepted=consent_accepted,
            questions_completed=status_at_least(
                session.status,
                SessionStatus.QUESTIONS_COMPLETED.value,
            ),
            summary_viewed=status_at_least(
                session.status,
                SessionStatus.SUMMARY_VIEWED.value,
            ),
            mind_card_count=mind_card_count,
            selected_card=selected_card,
            reply_created=reply_created,
            completion_code_issued=completion_code_issued,
        ),
    )
