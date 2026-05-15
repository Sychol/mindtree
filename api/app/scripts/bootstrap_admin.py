from __future__ import annotations

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.db.session import SessionLocal, get_engine
from app.repositories.admin_users import AdminUserRepository


def main() -> None:
    settings = get_settings()
    email = settings.admin_bootstrap_email.strip().lower()
    password = settings.admin_bootstrap_password
    display_name = settings.admin_bootstrap_display_name.strip() or "\uc6b4\uc601\uc790"
    if not email or not password:
        print("ADMIN_BOOTSTRAP_EMAIL and ADMIN_BOOTSTRAP_PASSWORD are empty. Nothing to do.")
        return

    db = SessionLocal(bind=get_engine())
    try:
        repo = AdminUserRepository(db)
        existing = repo.get_by_email(email)
        if existing is not None:
            print(f"Admin already exists: email={existing.email}, role={existing.role}")
            return

        admin = repo.create_admin_user(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            role="operator",
            is_active=True,
        )
        db.commit()
        print(f"Admin created: email={admin.email}, role={admin.role}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
