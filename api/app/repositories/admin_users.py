from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.admin import AdminUser
from app.repositories.base import BaseRepository


class AdminUserRepository(BaseRepository[AdminUser]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AdminUser)

    def get_by_email(self, email: str) -> AdminUser | None:
        statement = select(AdminUser).where(AdminUser.email == email.strip().lower())
        return self.db.execute(statement).scalar_one_or_none()

    def create_admin_user(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
        role: str = "operator",
        is_active: bool = True,
    ) -> AdminUser:
        admin = AdminUser(
            email=email.strip().lower(),
            password_hash=password_hash,
            display_name=display_name,
            role=role,
            is_active=is_active,
        )
        self.db.add(admin)
        self.db.flush()
        return admin
