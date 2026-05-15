from __future__ import annotations

from datetime import UTC, datetime

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.admin import AdminUser
from app.models.enums import CompletionCodeStatus
from app.repositories.completion_codes import CompletionCodeRepository
from app.repositories.events import EventRepository
from app.schemas.admin_rewards import (
    AdminCompletionCodePayload,
    AdminCompletionCodeRedeemRequest,
    AdminCompletionCodeRedeemResponse,
    AdminCompletionCodeResponse,
)
from app.services.audit_log import create_audit_log


def _completion_payload(code) -> AdminCompletionCodePayload:
    return AdminCompletionCodePayload(
        code=code.code,
        status=code.status,
        issuedAt=code.issued_at,
        redeemedAt=code.redeemed_at,
    )


def _event_or_404(db: Session, event_slug: str):
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return event


def lookup_completion_code(
    db: Session,
    *,
    event_slug: str,
    code_value: str,
) -> AdminCompletionCodeResponse:
    event = _event_or_404(db, event_slug)
    completion_code = CompletionCodeRepository(db).get_by_event_and_code(
        event_id=event.id,
        code=code_value.strip(),
    )
    if completion_code is None:
        raise AppError(
            ErrorCode.COMPLETION_CODE_NOT_FOUND,
            "완료 코드를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return AdminCompletionCodeResponse(completionCode=_completion_payload(completion_code))


def redeem_completion_code(
    db: Session,
    *,
    event_slug: str,
    code_value: str,
    payload: AdminCompletionCodeRedeemRequest,
    admin: AdminUser,
) -> AdminCompletionCodeRedeemResponse:
    event = _event_or_404(db, event_slug)
    completion_code = CompletionCodeRepository(db).get_by_event_and_code(
        event_id=event.id,
        code=code_value.strip(),
    )
    if completion_code is None:
        raise AppError(
            ErrorCode.COMPLETION_CODE_NOT_FOUND,
            "완료 코드를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    if completion_code.status == CompletionCodeStatus.REDEEMED.value:
        raise AppError(
            ErrorCode.COMPLETION_CODE_ALREADY_REDEEMED,
            "이미 지급 처리된 완료 코드입니다.",
            status.HTTP_409_CONFLICT,
            details={
                "redeemedAt": completion_code.redeemed_at.isoformat()
                if completion_code.redeemed_at
                else None
            },
        )
    if completion_code.status != CompletionCodeStatus.ISSUED.value:
        raise AppError(ErrorCode.BAD_REQUEST, "지급 처리할 수 없는 완료 코드입니다.")

    before = {
        "status": completion_code.status,
        "redeemedAt": completion_code.redeemed_at,
        "redeemedBy": completion_code.redeemed_by,
    }
    completion_code.status = CompletionCodeStatus.REDEEMED.value
    completion_code.redeemed_at = datetime.now(UTC)
    completion_code.redeemed_by = admin.id
    completion_code.notes = payload.notes.strip() if payload.notes else None
    db.add(completion_code)
    after = {
        "status": completion_code.status,
        "redeemedAt": completion_code.redeemed_at,
        "redeemedBy": completion_code.redeemed_by,
        "notesPresent": bool(completion_code.notes),
    }
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=event.id,
        action="completion_code.redeem",
        target_type="completion_code",
        target_id=completion_code.id,
        before_value=before,
        after_value=after,
        reason=payload.notes,
    )
    db.commit()
    db.refresh(completion_code)
    return AdminCompletionCodeRedeemResponse(
        completionCode=_completion_payload(completion_code),
        auditLogCreated=True,
    )
