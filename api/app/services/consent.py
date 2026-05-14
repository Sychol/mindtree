from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.core.security import hash_optional_value
from app.models.enums import SessionStatus
from app.repositories.consent import ConsentRepository
from app.repositories.sessions import SessionRepository
from app.schemas.sessions import ConsentRequest, ConsentResponse

REQUIRED_ACCEPTED_ITEMS = {
    "eventIsNotDiagnosis",
    "anonymousKeywordDisplay",
    "cardMayBeShownAnonymously",
    "noIdentifyingInfo",
    "adminModeration",
}


def _validate_required_items(accepted_items: dict[str, bool]) -> None:
    missing_or_false = [
        item
        for item in sorted(REQUIRED_ACCEPTED_ITEMS)
        if accepted_items.get(item) is not True
    ]
    if missing_or_false:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "필수 동의 항목을 모두 확인해야 합니다.",
            status.HTTP_400_BAD_REQUEST,
            details={"items": missing_or_false},
        )


def accept_consent(
    db: SQLAlchemySession,
    session_id: UUID,
    request: ConsentRequest,
    ip_address: str | None,
    user_agent: str | None,
) -> ConsentResponse:
    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    session, event = row
    _validate_required_items(request.accepted_items)

    if request.consent_version != event.consent_version:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "동의 버전이 현재 이벤트 버전과 일치하지 않습니다.",
            status.HTTP_400_BAD_REQUEST,
            details={
                "expectedConsentVersion": event.consent_version,
                "receivedConsentVersion": request.consent_version,
            },
        )

    session_repository = SessionRepository(db)
    consent_repository = ConsentRepository(db)
    consent_log = consent_repository.get_by_session_and_version(
        session.id,
        request.consent_version,
    )

    if consent_log is None:
        consent_log = consent_repository.create_consent_log(
            event_id=event.id,
            session_id=session.id,
            consent_version=request.consent_version,
            accepted_items=request.accepted_items,
            ip_hash=hash_optional_value(ip_address),
            user_agent_hash=hash_optional_value(user_agent),
        )

    if session.status == SessionStatus.CREATED.value:
        session_repository.set_status_and_step(
            session,
            SessionStatus.CONSENTED.value,
            "questions",
        )

    db.commit()
    db.refresh(session)
    db.refresh(consent_log)

    return ConsentResponse(
        session_status=session.status,
        accepted_at=consent_log.accepted_at,
    )
