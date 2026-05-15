from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.jwt import create_admin_access_token
from app.core.passwords import hash_password
from app.models.admin import AdminUser


def create_admin(
    db_session: Session,
    *,
    email: str | None = None,
    password: str = "admin-pass",
    is_active: bool = True,
    role: str = "operator",
) -> AdminUser:
    admin = AdminUser(
        email=email or f"admin-{uuid4().hex}@example.com",
        password_hash=hash_password(password),
        display_name="Operator",
        role=role,
        is_active=is_active,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


def auth_headers(admin: AdminUser) -> dict[str, str]:
    token = create_admin_access_token(admin_user_id=admin.id, role=admin.role)
    return {"Authorization": f"Bearer {token}"}
