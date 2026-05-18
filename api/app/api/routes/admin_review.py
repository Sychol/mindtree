from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_review import (
    AdminCardReviewListResponse,
    AdminCardReviewResponse,
    AdminReplyReviewListResponse,
    AdminReplyReviewResponse,
    AdminReviewRequest,
)
from app.services.admin_review import (
    list_admin_cards,
    list_admin_replies,
    review_admin_card,
    review_admin_reply,
)

router = APIRouter(prefix="/admin")


@router.get(
    "/events/{eventSlug}/cards",
    response_model=AdminCardReviewListResponse,
    response_model_exclude_none=True,
)
def read_admin_cards(
    event_slug: str = Path(alias="eventSlug"),
    status_filter: str = Query(default="review", alias="status"),
    origin_filter: str = Query(default="all", alias="origin"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminCardReviewListResponse:
    return list_admin_cards(
        db,
        event_slug=event_slug,
        status_filter=status_filter,
        origin_filter=origin_filter,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/cards/{cardId}/review",
    response_model=AdminCardReviewResponse,
    response_model_exclude_none=True,
)
def patch_admin_card_review(
    payload: AdminReviewRequest,
    card_id: UUID = Path(alias="cardId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminCardReviewResponse:
    return review_admin_card(db, card_id=card_id, payload=payload, admin=current_admin)


@router.get(
    "/events/{eventSlug}/replies",
    response_model=AdminReplyReviewListResponse,
    response_model_exclude_none=True,
)
def read_admin_replies(
    event_slug: str = Path(alias="eventSlug"),
    status_filter: str = Query(default="review", alias="status"),
    origin_filter: str = Query(default="all", alias="origin"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminReplyReviewListResponse:
    return list_admin_replies(
        db,
        event_slug=event_slug,
        status_filter=status_filter,
        origin_filter=origin_filter,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/replies/{replyId}/review",
    response_model=AdminReplyReviewResponse,
    response_model_exclude_none=True,
)
def patch_admin_reply_review(
    payload: AdminReviewRequest,
    reply_id: UUID = Path(alias="replyId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminReplyReviewResponse:
    return review_admin_reply(db, reply_id=reply_id, payload=payload, admin=current_admin)
