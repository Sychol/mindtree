from __future__ import annotations

import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.models.completion import CompletionCode
from app.models.enums import SessionStatus
from app.models.event import Event
from app.models.session import Session as EventSession
from app.repositories.card_selections import CardSelectionRepository
from app.repositories.cards import MindCardRepository
from app.repositories.completion_codes import CompletionCodeRepository
from app.repositories.consent import ConsentRepository
from app.repositories.replies import ReplyRepository
from app.repositories.risk_flags import RiskFlagRepository
from app.repositories.scale_scores import ScaleScoreRepository
from app.repositories.sessions import SessionRepository
from app.repositories.summaries import SummaryRepository
from app.schemas.completion import CompletionCodePayload, CompletionCodeResponse
from app.services.sessions import status_at_least

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _completion_prefix(event: Event) -> str:
    raw_prefix = (event.settings or {}).get("completionCodePrefix")
    if isinstance(raw_prefix, str) and raw_prefix.strip():
        return raw_prefix.strip().upper()[:12]
    return "TREE"


def _generate_code(prefix: str) -> str:
    suffix = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
    return f"{prefix}-{suffix}"


def _issue_code(
    db: SQLAlchemySession,
    *,
    event: Event,
    session: EventSession,
) -> CompletionCode:
    repository = CompletionCodeRepository(db)
    existing = repository.get_by_session_id(session.id)
    if existing is not None:
        return existing

    prefix = _completion_prefix(event)
    for _ in range(20):
        code = _generate_code(prefix)
        if repository.get_by_code(code) is None:
            return repository.create_code(
                event_id=event.id,
                session_id=session.id,
                code=code,
            )

    raise AppError(
        ErrorCode.INTERNAL_ERROR,
        "완료 코드를 생성하지 못했습니다.",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def is_completion_eligible(db: SQLAlchemySession, session: EventSession) -> bool:
    summary = SummaryRepository(db).get_by_session_id(session.id)
    has_summary_viewed = (
        summary is not None
        and summary.viewed_at is not None
        or status_at_least(session.status, SessionStatus.SUMMARY_VIEWED.value)
    )

    return all(
        [
            status_at_least(session.status, SessionStatus.SUMMARY_VIEWED.value),
            ConsentRepository(db).exists_for_session(session.id),
            bool(ScaleScoreRepository(db).list_by_session_id(session.id)),
            RiskFlagRepository(db).get_by_session_id(session.id) is not None,
            has_summary_viewed,
            MindCardRepository(db).count_by_session_id(session.id) >= 1,
            CardSelectionRepository(db).get_by_session_id(session.id) is not None,
            ReplyRepository(db).count_by_session_id(session.id) >= 1,
        ]
    )


def ensure_completion_if_eligible(
    db: SQLAlchemySession,
    *,
    event: Event,
    session: EventSession,
) -> tuple[bool, CompletionCode | None]:
    existing = CompletionCodeRepository(db).get_by_session_id(session.id)
    eligible = is_completion_eligible(db, session)
    if not eligible:
        return False, existing

    completion_code = existing or _issue_code(db, event=event, session=session)
    session.status = SessionStatus.COMPLETED.value
    session.last_step = "complete"
    session.completed_at = session.completed_at or datetime.now(timezone.utc)
    db.add(session)
    db.flush()
    return True, completion_code


def get_completion_code(
    db: SQLAlchemySession,
    session_id: UUID,
) -> CompletionCodeResponse:
    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    completion_code = CompletionCodeRepository(db).get_by_session_id(session_id)
    if completion_code is None:
        raise AppError(
            ErrorCode.COMPLETION_CODE_NOT_FOUND,
            "아직 발급된 완료 코드가 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    return CompletionCodeResponse(
        completion_code=CompletionCodePayload(
            code=completion_code.code,
            status=completion_code.status,
            issued_at=completion_code.issued_at,
        )
    )
