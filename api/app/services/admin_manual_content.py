from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.admin import AdminUser
from app.models.card import MindCard
from app.models.enums import ContentOrigin, PublicStatus, ReplyType, SafetyStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.repositories.admin_manual_content import AdminManualContentRepository
from app.repositories.cards import MindCardRepository
from app.repositories.events import EventRepository
from app.repositories.keywords import KeywordRepository
from app.repositories.replies import ReplyRepository
from app.schemas.admin_manual_content import (
    AdminManualCardCreateRequest,
    AdminManualCardCreateResponse,
    AdminManualCardPayload,
    AdminManualCardStatusResponse,
    AdminManualContentStatusRequest,
    AdminManualReplyCreateRequest,
    AdminManualReplyCreateResponse,
    AdminManualReplyPayload,
    AdminManualReplyStatusResponse,
)
from app.schemas.cards import KeywordJobPayload
from app.services.audit_log import create_audit_log
from app.services.cards import _normalize_prompt_type
from app.services.keyword_job_factory import create_keyword_job_for_card, create_keyword_job_for_reply
from app.services.safety_filter import evaluate_safety

DEFAULT_MANUAL_ORIGIN_TAG = "운영자추가"
MANUAL_STATUS_ORIGINS = {
    ContentOrigin.ADMIN_MANUAL.value,
    ContentOrigin.SYSTEM_SEED.value,
}
ALLOWED_REPLY_TYPES = {
    ReplyType.COMFORT.value,
    ReplyType.EMPATHY.value,
    ReplyType.SMALL_COPING.value,
}


def _event_or_404(db: Session, event_slug: str):
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(ErrorCode.EVENT_NOT_FOUND, "이벤트를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    return event


def _validate_public_status(public_status: str) -> str:
    if public_status not in {item.value for item in PublicStatus}:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 공개 상태입니다.")
    return public_status


def _validate_reply_type(reply_type: str) -> str:
    if reply_type not in ALLOWED_REPLY_TYPES:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "지원하지 않는 응원문장 유형입니다.",
            details={"replyType": reply_type},
        )
    return reply_type


def _validate_status_payload(payload: AdminManualContentStatusRequest) -> tuple[str, str]:
    if payload.safety_status not in {item.value for item in SafetyStatus}:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 안전 상태입니다.")
    if payload.public_status not in {item.value for item in PublicStatus}:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 공개 상태입니다.")

    safety_status = payload.safety_status
    public_status = payload.public_status
    if safety_status == SafetyStatus.EXCLUDE.value:
        public_status = PublicStatus.EXCLUDED.value
    if public_status == PublicStatus.PUBLIC.value and safety_status != SafetyStatus.SAFE.value:
        raise AppError(ErrorCode.BAD_REQUEST, "공개 상태로 복구하려면 안전 상태가 safe여야 합니다.")
    return safety_status, public_status


def _public_status_from_safety(requested_status: str, safety_status: str, moderation_reason: str | None) -> str:
    if safety_status == SafetyStatus.EXCLUDE.value:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "안전 필터에서 제외된 콘텐츠는 수동 등록할 수 없습니다.",
            details={"reason": moderation_reason},
        )
    if safety_status == SafetyStatus.REVIEW.value:
        return PublicStatus.PENDING.value
    return requested_status


def _should_create_manual_keyword_job(*, create_keyword_job: bool, safety_status: str, public_status: str) -> bool:
    return (
        create_keyword_job
        and safety_status == SafetyStatus.SAFE.value
        and public_status == PublicStatus.PUBLIC.value
    )


def _keyword_job_payload(job: KeywordJob | None) -> KeywordJobPayload | None:
    if job is None:
        return None
    return KeywordJobPayload(id=job.id, status=job.status)


def _content_preview(content: str) -> str:
    return content[:40]


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


def _card_payload(card: MindCard, event_slug: str | None = None, *, include_content: bool = True) -> AdminManualCardPayload:
    return AdminManualCardPayload(
        id=card.id,
        eventSlug=event_slug,
        sessionId=card.session_id,
        promptType=card.prompt_type if include_content else None,
        contentRaw=card.content_raw if include_content else None,
        contentRedacted=card.content_redacted if include_content else None,
        safetyStatus=card.safety_status,
        publicStatus=card.public_status,
        origin=card.origin,
        originTag=card.origin_tag,
        createdByAdminId=card.created_by_admin_id,
        createdAt=card.created_at if include_content else None,
    )


def _reply_payload(reply: Reply, event_slug: str | None = None, *, include_content: bool = True) -> AdminManualReplyPayload:
    return AdminManualReplyPayload(
        id=reply.id,
        eventSlug=event_slug,
        sessionId=reply.session_id,
        targetCardId=reply.target_card_id,
        replyType=reply.reply_type if include_content else None,
        contentRaw=reply.content_raw if include_content else None,
        contentRedacted=reply.content_redacted if include_content else None,
        safetyStatus=reply.safety_status,
        publicStatus=reply.public_status,
        origin=reply.origin,
        originTag=reply.origin_tag,
        createdByAdminId=reply.created_by_admin_id,
        createdAt=reply.created_at if include_content else None,
    )


def create_manual_card(
    db: Session,
    *,
    event_slug: str,
    payload: AdminManualCardCreateRequest,
    admin: AdminUser,
) -> AdminManualCardCreateResponse:
    event = _event_or_404(db, event_slug)
    prompt_type = _normalize_prompt_type(payload.prompt_type)
    requested_public_status = _validate_public_status(payload.public_status)
    safety_result = evaluate_safety("mind_card", payload.content)
    public_status = _public_status_from_safety(
        requested_public_status,
        safety_result.safety_status,
        safety_result.moderation_reason,
    )
    origin_tag = payload.origin_tag or DEFAULT_MANUAL_ORIGIN_TAG
    now = datetime.now(UTC)

    card = MindCardRepository(db).create_card(
        event_id=event.id,
        session_id=None,
        prompt_type=prompt_type,
        content_raw=payload.content,
        content_redacted=safety_result.content_redacted,
        safety_status=safety_result.safety_status,
        public_status=public_status,
        moderation_reason=safety_result.moderation_reason,
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag=origin_tag,
        created_by_admin_id=admin.id,
        reviewed_by=admin.id,
        reviewed_at=now,
    )

    keyword_job = None
    if _should_create_manual_keyword_job(
        create_keyword_job=payload.create_keyword_job,
        safety_status=card.safety_status,
        public_status=card.public_status,
    ):
        keyword_job = create_keyword_job_for_card(db, card)

    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=event.id,
        action="manual_card.create",
        target_type="mind_card",
        target_id=card.id,
        after_value={
            "promptType": card.prompt_type,
            "contentPreview": _content_preview(card.content_raw),
            "contentLength": len(card.content_raw),
            "safetyStatus": card.safety_status,
            "publicStatus": card.public_status,
            "origin": card.origin,
            "originTag": card.origin_tag,
            "createKeywordJob": payload.create_keyword_job,
        },
        reason=payload.reason,
    )
    db.commit()
    db.refresh(card)
    if keyword_job is not None:
        db.refresh(keyword_job)

    return AdminManualCardCreateResponse(
        card=_card_payload(card, event.slug),
        keywordJob=_keyword_job_payload(keyword_job),
        auditLogCreated=True,
    )


def update_manual_card_status(
    db: Session,
    *,
    card_id: UUID,
    payload: AdminManualContentStatusRequest,
    admin: AdminUser,
) -> AdminManualCardStatusResponse:
    card = AdminManualContentRepository(db).get_card(card_id)
    if card is None:
        raise AppError(ErrorCode.CARD_NOT_FOUND, "마음카드를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    if card.origin not in MANUAL_STATUS_ORIGINS:
        raise AppError(ErrorCode.BAD_REQUEST, "참가자 마음카드는 기존 review API를 사용해 주세요.")

    safety_status, public_status = _validate_status_payload(payload)
    before = {
        "safetyStatus": card.safety_status,
        "publicStatus": card.public_status,
        "origin": card.origin,
        "originTag": card.origin_tag,
    }
    card.safety_status = safety_status
    card.public_status = public_status
    card.reviewed_by = admin.id
    card.reviewed_at = datetime.now(UTC)
    db.add(card)
    _sync_keyword_status_for_source(
        db,
        event_id=card.event_id,
        source_type="mind_card",
        source_id=card.id,
        safety_status=safety_status,
        public_status=public_status,
    )
    after = {
        "safetyStatus": card.safety_status,
        "publicStatus": card.public_status,
        "origin": card.origin,
        "originTag": card.origin_tag,
    }
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=card.event_id,
        action="manual_card.update_status",
        target_type="mind_card",
        target_id=card.id,
        before_value=before,
        after_value=after,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(card)
    return AdminManualCardStatusResponse(
        card=_card_payload(card, include_content=False),
        auditLogCreated=True,
    )


def _validate_target_card(db: Session, *, event_id: UUID, target_card_id: UUID | None) -> UUID | None:
    if target_card_id is None:
        return None
    card = MindCardRepository(db).get_by_id(target_card_id)
    if card is None:
        raise AppError(ErrorCode.CARD_NOT_FOUND, "대상 마음카드를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    if card.event_id != event_id:
        raise AppError(ErrorCode.BAD_REQUEST, "같은 이벤트의 마음카드만 대상이 될 수 있습니다.")
    if card.safety_status != SafetyStatus.SAFE.value or card.public_status != PublicStatus.PUBLIC.value:
        raise AppError(ErrorCode.BAD_REQUEST, "safe/public 마음카드만 대상이 될 수 있습니다.")
    return card.id


def create_manual_reply(
    db: Session,
    *,
    event_slug: str,
    payload: AdminManualReplyCreateRequest,
    admin: AdminUser,
) -> AdminManualReplyCreateResponse:
    event = _event_or_404(db, event_slug)
    reply_type = _validate_reply_type(payload.reply_type)
    target_card_id = _validate_target_card(db, event_id=event.id, target_card_id=payload.target_card_id)
    requested_public_status = _validate_public_status(payload.public_status)
    safety_result = evaluate_safety("reply", payload.content)
    public_status = _public_status_from_safety(
        requested_public_status,
        safety_result.safety_status,
        safety_result.moderation_reason,
    )
    origin_tag = payload.origin_tag or DEFAULT_MANUAL_ORIGIN_TAG
    now = datetime.now(UTC)

    reply = ReplyRepository(db).create_reply(
        event_id=event.id,
        session_id=None,
        target_card_id=target_card_id,
        reply_type=reply_type,
        content_raw=payload.content,
        content_redacted=safety_result.content_redacted,
        safety_status=safety_result.safety_status,
        public_status=public_status,
        moderation_reason=safety_result.moderation_reason,
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag=origin_tag,
        created_by_admin_id=admin.id,
        reviewed_by=admin.id,
        reviewed_at=now,
    )

    keyword_job = None
    if _should_create_manual_keyword_job(
        create_keyword_job=payload.create_keyword_job,
        safety_status=reply.safety_status,
        public_status=reply.public_status,
    ):
        keyword_job = create_keyword_job_for_reply(db, reply)

    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=event.id,
        action="manual_reply.create",
        target_type="reply",
        target_id=reply.id,
        after_value={
            "replyType": reply.reply_type,
            "contentPreview": _content_preview(reply.content_raw),
            "contentLength": len(reply.content_raw),
            "targetCardId": reply.target_card_id,
            "safetyStatus": reply.safety_status,
            "publicStatus": reply.public_status,
            "origin": reply.origin,
            "originTag": reply.origin_tag,
            "createKeywordJob": payload.create_keyword_job,
        },
        reason=payload.reason,
    )
    db.commit()
    db.refresh(reply)
    if keyword_job is not None:
        db.refresh(keyword_job)

    return AdminManualReplyCreateResponse(
        reply=_reply_payload(reply, event.slug),
        keywordJob=_keyword_job_payload(keyword_job),
        auditLogCreated=True,
    )


def update_manual_reply_status(
    db: Session,
    *,
    reply_id: UUID,
    payload: AdminManualContentStatusRequest,
    admin: AdminUser,
) -> AdminManualReplyStatusResponse:
    reply = AdminManualContentRepository(db).get_reply(reply_id)
    if reply is None:
        raise AppError(ErrorCode.REPLY_NOT_FOUND, "응원문장을 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    if reply.origin not in MANUAL_STATUS_ORIGINS:
        raise AppError(ErrorCode.BAD_REQUEST, "참가자 응원문장은 기존 review API를 사용해 주세요.")

    safety_status, public_status = _validate_status_payload(payload)
    before = {
        "safetyStatus": reply.safety_status,
        "publicStatus": reply.public_status,
        "origin": reply.origin,
        "originTag": reply.origin_tag,
    }
    reply.safety_status = safety_status
    reply.public_status = public_status
    reply.reviewed_by = admin.id
    reply.reviewed_at = datetime.now(UTC)
    db.add(reply)
    _sync_keyword_status_for_source(
        db,
        event_id=reply.event_id,
        source_type="reply",
        source_id=reply.id,
        safety_status=safety_status,
        public_status=public_status,
    )
    after = {
        "safetyStatus": reply.safety_status,
        "publicStatus": reply.public_status,
        "origin": reply.origin,
        "originTag": reply.origin_tag,
    }
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=reply.event_id,
        action="manual_reply.update_status",
        target_type="reply",
        target_id=reply.id,
        before_value=before,
        after_value=after,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(reply)
    return AdminManualReplyStatusResponse(
        reply=_reply_payload(reply, include_content=False),
        auditLogCreated=True,
    )
