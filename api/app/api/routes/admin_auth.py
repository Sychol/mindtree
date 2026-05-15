from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_auth import AdminLoginRequest, AdminLoginResponse, AdminMeResponse
from app.services.admin_auth import get_admin_me, login_admin

router = APIRouter(prefix="/admin/auth")


@router.post("/login", response_model=AdminLoginResponse)
def login(
    payload: AdminLoginRequest,
    db: Session = Depends(get_db),
) -> AdminLoginResponse:
    return login_admin(db, payload)


@router.get("/me", response_model=AdminMeResponse)
def read_me(
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminMeResponse:
    return get_admin_me(current_admin)
