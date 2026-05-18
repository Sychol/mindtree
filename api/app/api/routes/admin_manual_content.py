from uuid import UUID

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_manual_content import (
    AdminManualCardCreateRequest,
    AdminManualCardCreateResponse,
    AdminManualCardStatusResponse,
    AdminManualContentStatusRequest,
    AdminManualReplyCreateRequest,
    AdminManualReplyCreateResponse,
    AdminManualReplyStatusResponse,
)
from app.services.admin_manual_content import (
    create_manual_card,
    create_manual_reply,
    update_manual_card_status,
    update_manual_reply_status,
)

router = APIRouter(prefix="/admin")


@router.post(
    "/events/{eventSlug}/manual-cards",
    response_model=AdminManualCardCreateResponse,
)
def post_manual_card(
    payload: AdminManualCardCreateRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminManualCardCreateResponse:
    return create_manual_card(
        db,
        event_slug=event_slug,
        payload=payload,
        admin=current_admin,
    )


@router.patch(
    "/manual-cards/{cardId}/status",
    response_model=AdminManualCardStatusResponse,
    response_model_exclude_none=True,
)
def patch_manual_card_status(
    payload: AdminManualContentStatusRequest,
    card_id: UUID = Path(alias="cardId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminManualCardStatusResponse:
    return update_manual_card_status(
        db,
        card_id=card_id,
        payload=payload,
        admin=current_admin,
    )


@router.post(
    "/events/{eventSlug}/manual-replies",
    response_model=AdminManualReplyCreateResponse,
)
def post_manual_reply(
    payload: AdminManualReplyCreateRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminManualReplyCreateResponse:
    return create_manual_reply(
        db,
        event_slug=event_slug,
        payload=payload,
        admin=current_admin,
    )


@router.patch(
    "/manual-replies/{replyId}/status",
    response_model=AdminManualReplyStatusResponse,
    response_model_exclude_none=True,
)
def patch_manual_reply_status(
    payload: AdminManualContentStatusRequest,
    reply_id: UUID = Path(alias="replyId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminManualReplyStatusResponse:
    return update_manual_reply_status(
        db,
        reply_id=reply_id,
        payload=payload,
        admin=current_admin,
    )
