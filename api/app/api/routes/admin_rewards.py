from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_rewards import (
    AdminCompletionCodeRedeemRequest,
    AdminCompletionCodeRedeemResponse,
    AdminCompletionCodeResponse,
)
from app.services.admin_rewards import lookup_completion_code, redeem_completion_code

router = APIRouter(prefix="/admin")


@router.get(
    "/events/{eventSlug}/completion-codes/{code}",
    response_model=AdminCompletionCodeResponse,
)
def read_admin_completion_code(
    event_slug: str = Path(alias="eventSlug"),
    code: str = Path(),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminCompletionCodeResponse:
    return lookup_completion_code(db, event_slug=event_slug, code_value=code)


@router.post(
    "/events/{eventSlug}/completion-codes/{code}/redeem",
    response_model=AdminCompletionCodeRedeemResponse,
)
def post_admin_completion_code_redeem(
    payload: AdminCompletionCodeRedeemRequest,
    event_slug: str = Path(alias="eventSlug"),
    code: str = Path(),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminCompletionCodeRedeemResponse:
    return redeem_completion_code(
        db,
        event_slug=event_slug,
        code_value=code,
        payload=payload,
        admin=current_admin,
    )
