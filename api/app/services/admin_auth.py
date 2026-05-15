from __future__ import annotations

from datetime import timedelta

from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.jwt import create_admin_access_token
from app.core.passwords import verify_password
from app.models.admin import AdminUser
from app.repositories.admin_users import AdminUserRepository
from app.schemas.admin_auth import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminMeResponse,
    AdminPayload,
)
from app.services.audit_log import create_audit_log


def build_admin_payload(admin: AdminUser) -> AdminPayload:
    return AdminPayload(
        id=admin.id,
        email=admin.email,
        displayName=admin.display_name,
        role=admin.role,
    )


def _raise_login_failed(db: Session, admin: AdminUser | None, email: str) -> None:
    create_audit_log(
        db,
        admin_user_id=admin.id if admin else None,
        event_id=None,
        action="admin.login_failed",
        target_type="admin",
        target_id=admin.id if admin else None,
        before_value=None,
        after_value={"email": email},
        reason="login_failed",
    )
    db.commit()
    raise AppError(
        ErrorCode.UNAUTHORIZED,
        "이메일 또는 비밀번호를 확인해 주세요.",
        status.HTTP_401_UNAUTHORIZED,
    )


def login_admin(db: Session, payload: AdminLoginRequest) -> AdminLoginResponse:
    email = payload.email.strip().lower()
    if not email or not payload.password:
        _raise_login_failed(db, None, email)

    admin = AdminUserRepository(db).get_by_email(email)
    if admin is None or not admin.is_active:
        _raise_login_failed(db, admin, email)

    if not verify_password(payload.password, admin.password_hash):
        _raise_login_failed(db, admin, email)

    settings = get_settings()
    token = create_admin_access_token(
        admin_user_id=admin.id,
        role=admin.role,
        expires_delta=timedelta(minutes=settings.admin_jwt_expires_minutes),
    )
    return AdminLoginResponse(accessToken=token, admin=build_admin_payload(admin))


def get_admin_me(admin: AdminUser) -> AdminMeResponse:
    return AdminMeResponse(admin=build_admin_payload(admin))
