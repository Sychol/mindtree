from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.models.enums import PublicStatus, ReplyType, SafetyStatus, SessionStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.repositories.card_selections import CardSelectionRepository
from app.repositories.cards import MindCardRepository
from app.repositories.replies import ReplyRepository
from app.repositories.risk_flags import RiskFlagRepository
from app.repositories.sessions import SessionRepository
from app.schemas.cards import KeywordJobPayload
from app.schemas.replies import (
    CompletionPayload,
    CreateReplyRequest,
    CreateReplyResponse,
    ReplyPayload,
)
from app.services.completion import ensure_completion_if_eligible
from app.services.keyword_job_factory import create_keyword_job_for_reply
from app.services.safety_filter import evaluate_safety
from app.services.sessions import status_at_least

ALLOWED_REPLY_TYPES = {
    ReplyType.COMFORT.value,
    ReplyType.EMPATHY.value,
    ReplyType.SMALL_COPING.value,
}
MAX_CONTENT_LENGTH = 300


def _ensure_min_status(current_status: str, required_status: str) -> None:
    if not status_at_least(current_status, required_status):
        raise AppError(
            ErrorCode.INVALID_SESSION_STATUS,
            "현재 세션 상태에서는 이 단계를 진행할 수 없습니다.",
            status.HTTP_409_CONFLICT,
            details={"status": current_status, "requiredStatus": required_status},
        )


def _validate_content(content: str) -> str:
    normalized = content.strip()
    if not normalized:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "내용을 입력해 주세요.",
            status.HTTP_400_BAD_REQUEST,
        )
    if len(normalized) > MAX_CONTENT_LENGTH:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "내용은 300자 이내로 입력해 주세요.",
            status.HTTP_400_BAD_REQUEST,
            details={"maxLength": MAX_CONTENT_LENGTH},
        )
    return normalized


def _validate_reply_type(reply_type: str) -> str:
    if reply_type not in ALLOWED_REPLY_TYPES:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "허용되지 않는 응원 문장 유형입니다.",
            status.HTTP_400_BAD_REQUEST,
            details={"replyType": reply_type},
        )
    return reply_type


def _reply_payload(reply: Reply) -> ReplyPayload:
    return ReplyPayload(
        id=reply.id,
        reply_type=reply.reply_type,
        safety_status=reply.safety_status,
        public_status=reply.public_status,
    )


def _keyword_job_payload(job: KeywordJob | None) -> KeywordJobPayload | None:
    if job is None:
        return None
    return KeywordJobPayload(id=job.id, status=job.status)


def create_reply(
    db: SQLAlchemySession,
    session_id: UUID,
    payload: CreateReplyRequest,
) -> CreateReplyResponse:
    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    session, event = row
    _ensure_min_status(session.status, SessionStatus.CARD_CREATED.value)

    selection = CardSelectionRepository(db).get_by_session_id(session.id)
    if selection is None:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "먼저 공개 가능한 타인 카드를 선택해 주세요.",
            status.HTTP_400_BAD_REQUEST,
        )
    if selection.selected_card_id != payload.target_card_id:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "선택한 카드에만 응원 문장을 남길 수 있습니다.",
            status.HTTP_400_BAD_REQUEST,
        )

    target_card = MindCardRepository(db).get_by_id(payload.target_card_id)
    if target_card is None:
        raise AppError(
            ErrorCode.CARD_NOT_FOUND,
            "응원할 카드를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    if (
        target_card.event_id != event.id
        or target_card.safety_status != SafetyStatus.SAFE.value
        or target_card.public_status != PublicStatus.PUBLIC.value
    ):
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "공개 가능한 카드에만 응원 문장을 남길 수 있습니다.",
            status.HTTP_400_BAD_REQUEST,
        )

    reply_type = _validate_reply_type(payload.reply_type)
    content = _validate_content(payload.content)
    safety_result = evaluate_safety("reply", content)

    reply = ReplyRepository(db).create_reply(
        event_id=event.id,
        session_id=session.id,
        target_card_id=target_card.id,
        reply_type=reply_type,
        content_raw=content,
        content_redacted=safety_result.content_redacted,
        safety_status=safety_result.safety_status,
        public_status=safety_result.public_status,
        moderation_reason=safety_result.moderation_reason,
    )

    if safety_result.crisis_expression_detected:
        RiskFlagRepository(db).mark_crisis_expression_detected(
            event_id=event.id,
            session_id=session.id,
            reason=safety_result.moderation_reason or "crisis_expression",
        )

    keyword_job = create_keyword_job_for_reply(db, reply)

    if session.status == SessionStatus.CARD_CREATED.value:
        SessionRepository(db).set_status_and_step(
            session,
            SessionStatus.REPLY_CREATED.value,
            "complete",
        )

    eligible, completion_code = ensure_completion_if_eligible(
        db,
        event=event,
        session=session,
    )

    db.commit()
    db.refresh(reply)
    if keyword_job is not None:
        db.refresh(keyword_job)
    db.refresh(session)
    if completion_code is not None:
        db.refresh(completion_code)

    return CreateReplyResponse(
        reply=_reply_payload(reply),
        keyword_job=_keyword_job_payload(keyword_job),
        completion=CompletionPayload(
            eligible=eligible,
            code=completion_code.code if completion_code is not None else None,
        ),
        session_status=session.status,
    )
