from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.admin import AdminUser
from app.models.card import MindCard
from app.models.enums import PublicStatus, SafetyStatus
from app.models.reply import Reply
from app.models.risk import RiskFlag
from app.repositories.cards import MindCardRepository
from app.repositories.events import EventRepository
from app.repositories.keywords import KeywordRepository
from app.repositories.replies import ReplyRepository
from app.repositories.risk_flags import RiskFlagRepository
from app.schemas.admin_review import (
    AdminCardReviewItem,
    AdminCardReviewListResponse,
    AdminCardReviewPayload,
    AdminCardReviewResponse,
    AdminReplyReviewItem,
    AdminReplyReviewListResponse,
    AdminReplyReviewPayload,
    AdminReplyReviewResponse,
    AdminReviewRequest,
    AdminRiskFlagsPayload,
)
from app.services.audit_log import create_audit_log

ALLOWED_FILTERS = {
    "review",
    "safe",
    "exclude",
    "public",
    "hidden",
    "excluded",
    "pending",
    "all",
}


def _event_id_or_404(db: Session, event_slug: str) -> UUID:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return event.id


def _risk_payload(risk: RiskFlag | None) -> AdminRiskFlagsPayload:
    if risk is None:
        return AdminRiskFlagsPayload()
    return AdminRiskFlagsPayload(
        phq9Item9Positive=risk.phq9_item9_positive,
        crisisExpressionDetected=risk.crisis_expression_detected,
        traumaHighSignal=risk.trauma_high_signal,
        moralInjuryHighSignal=risk.moral_injury_high_signal,
        publicRestriction=risk.public_restriction,
        helpNoticeRequired=risk.help_notice_required,
    )


def _card_item(db: Session, card: MindCard) -> AdminCardReviewItem:
    risk = RiskFlagRepository(db).get_by_session_id(card.session_id)
    return AdminCardReviewItem(
        id=card.id,
        contentRaw=card.content_raw,
        contentRedacted=card.content_redacted,
        promptType=card.prompt_type,
        safetyStatus=card.safety_status,
        publicStatus=card.public_status,
        moderationReason=card.moderation_reason,
        riskFlags=_risk_payload(risk),
        createdAt=card.created_at,
    )


def _reply_item(db: Session, reply: Reply) -> AdminReplyReviewItem:
    risk = RiskFlagRepository(db).get_by_session_id(reply.session_id)
    return AdminReplyReviewItem(
        id=reply.id,
        contentRaw=reply.content_raw,
        contentRedacted=reply.content_redacted,
        replyType=reply.reply_type,
        targetCardId=reply.target_card_id,
        safetyStatus=reply.safety_status,
        publicStatus=reply.public_status,
        moderationReason=reply.moderation_reason,
        riskFlags=_risk_payload(risk),
        createdAt=reply.created_at,
    )


def _validate_filter(status_filter: str) -> None:
    if status_filter not in ALLOWED_FILTERS:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 상태 필터입니다.")


def list_admin_cards(
    db: Session,
    *,
    event_slug: str,
    status_filter: str,
    limit: int,
    offset: int,
) -> AdminCardReviewListResponse:
    _validate_filter(status_filter)
    event_id = _event_id_or_404(db, event_slug)
    repo = MindCardRepository(db)
    items = repo.list_admin_cards(
        event_id=event_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    total = repo.count_admin_cards(event_id=event_id, status_filter=status_filter)
    return AdminCardReviewListResponse(
        items=[_card_item(db, item) for item in items],
        total=total,
    )


def list_admin_replies(
    db: Session,
    *,
    event_slug: str,
    status_filter: str,
    limit: int,
    offset: int,
) -> AdminReplyReviewListResponse:
    _validate_filter(status_filter)
    event_id = _event_id_or_404(db, event_slug)
    repo = ReplyRepository(db)
    items = repo.list_admin_replies(
        event_id=event_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    total = repo.count_admin_replies(event_id=event_id, status_filter=status_filter)
    return AdminReplyReviewListResponse(
        items=[_reply_item(db, item) for item in items],
        total=total,
    )


def _validate_review_payload(payload: AdminReviewRequest) -> tuple[str, str]:
    safety_status = payload.safety_status
    public_status = payload.public_status
    allowed_safety = {item.value for item in SafetyStatus}
    allowed_public = {item.value for item in PublicStatus}
    if safety_status not in allowed_safety:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 안전 상태입니다.")
    if public_status not in allowed_public:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 공개 상태입니다.")

    if safety_status == SafetyStatus.EXCLUDE.value:
        public_status = PublicStatus.EXCLUDED.value
    if public_status == PublicStatus.PUBLIC.value and safety_status != SafetyStatus.SAFE.value:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "공개 상태로 변경하려면 안전 상태가 safe여야 합니다.",
        )
    return safety_status, public_status


def _content_redacted(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _review_before(source: MindCard | Reply) -> dict[str, object | None]:
    return {
        "safetyStatus": source.safety_status,
        "publicStatus": source.public_status,
        "contentRedacted": source.content_redacted,
        "moderationReason": source.moderation_reason,
    }


def _review_after(source: MindCard | Reply) -> dict[str, object | None]:
    return {
        "safetyStatus": source.safety_status,
        "publicStatus": source.public_status,
        "contentRedacted": source.content_redacted,
        "moderationReason": source.moderation_reason,
        "reviewedAt": source.reviewed_at,
        "reviewedBy": source.reviewed_by,
    }


def _review_action(target_prefix: str, before: dict[str, object | None], public_status: str) -> str:
    if public_status == PublicStatus.PUBLIC.value:
        if before.get("contentRedacted") is not None:
            return f"{target_prefix}.edit"
        return f"{target_prefix}.publish"
    if public_status == PublicStatus.HIDDEN.value:
        return f"{target_prefix}.hide"
    if public_status == PublicStatus.EXCLUDED.value:
        return f"{target_prefix}.delete"
    return f"{target_prefix}.edit"


def _sync_keyword_status_for_source(
    db: Session,
    *,
    event_id: UUID,
    source_type: str,
    source_id: UUID,
    safety_status: str,
    public_status: str,
) -> None:
    keyword_status: str | None = None
    if safety_status == SafetyStatus.EXCLUDE.value or public_status == PublicStatus.EXCLUDED.value:
        keyword_status = "excluded"
    elif public_status == PublicStatus.HIDDEN.value:
        keyword_status = "hidden"
    elif public_status == PublicStatus.PUBLIC.value and safety_status == SafetyStatus.SAFE.value:
        keyword_status = "active"

    if keyword_status is not None:
        KeywordRepository(db).update_status_by_source(
            event_id=event_id,
            source_type=source_type,
            source_id=source_id,
            status=keyword_status,
        )


def review_admin_card(
    db: Session,
    *,
    card_id: UUID,
    payload: AdminReviewRequest,
    admin: AdminUser,
) -> AdminCardReviewResponse:
    card = MindCardRepository(db).get_by_id(card_id)
    if card is None:
        raise AppError(ErrorCode.CARD_NOT_FOUND, "마음카드를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)

    safety_status, public_status = _validate_review_payload(payload)
    before = _review_before(card)
    card.safety_status = safety_status
    card.public_status = public_status
    card.content_redacted = _content_redacted(payload.content_redacted)
    card.moderation_reason = payload.reason
    card.reviewed_at = datetime.now(UTC)
    card.reviewed_by = admin.id
    db.add(card)
    _sync_keyword_status_for_source(
        db,
        event_id=card.event_id,
        source_type="mind_card",
        source_id=card.id,
        safety_status=safety_status,
        public_status=public_status,
    )
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=card.event_id,
        action=_review_action("card", before, public_status),
        target_type="card",
        target_id=card.id,
        before_value=before,
        after_value=_review_after(card),
        reason=payload.reason,
    )
    db.commit()
    db.refresh(card)
    return AdminCardReviewResponse(
        card=AdminCardReviewPayload(
            id=card.id,
            safetyStatus=card.safety_status,
            publicStatus=card.public_status,
            contentRedacted=card.content_redacted,
        ),
        auditLogCreated=True,
    )


def review_admin_reply(
    db: Session,
    *,
    reply_id: UUID,
    payload: AdminReviewRequest,
    admin: AdminUser,
) -> AdminReplyReviewResponse:
    reply = ReplyRepository(db).get_by_id(reply_id)
    if reply is None:
        raise AppError(ErrorCode.REPLY_NOT_FOUND, "응원 문장을 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)

    safety_status, public_status = _validate_review_payload(payload)
    before = _review_before(reply)
    reply.safety_status = safety_status
    reply.public_status = public_status
    reply.content_redacted = _content_redacted(payload.content_redacted)
    reply.moderation_reason = payload.reason
    reply.reviewed_at = datetime.now(UTC)
    reply.reviewed_by = admin.id
    db.add(reply)
    _sync_keyword_status_for_source(
        db,
        event_id=reply.event_id,
        source_type="reply",
        source_id=reply.id,
        safety_status=safety_status,
        public_status=public_status,
    )
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=reply.event_id,
        action=_review_action("reply", before, public_status),
        target_type="reply",
        target_id=reply.id,
        before_value=before,
        after_value=_review_after(reply),
        reason=payload.reason,
    )
    db.commit()
    db.refresh(reply)
    return AdminReplyReviewResponse(
        reply=AdminReplyReviewPayload(
            id=reply.id,
            safetyStatus=reply.safety_status,
            publicStatus=reply.public_status,
            contentRedacted=reply.content_redacted,
        ),
        auditLogCreated=True,
    )
