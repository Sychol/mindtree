import hashlib
import hmac
import secrets
from uuid import UUID

from fastapi import Depends, Header, status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.jwt import JwtError, decode_admin_access_token
from app.db.session import get_db
from app.models.admin import AdminUser
from app.repositories.admin_users import AdminUserRepository


def generate_resume_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    settings = get_settings()
    # TODO(phase11): split participant session hashing into SESSION_HASH_SECRET.
    secret = settings.jwt_secret_key.encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def hash_optional_value(value: str | None) -> str | None:
    if value is None:
        return None

    stripped_value = value.strip()
    if not stripped_value:
        return None

    return hash_token(stripped_value)


def _unauthorized() -> AppError:
    return AppError(
        ErrorCode.UNAUTHORIZED,
        "Admin authentication is required.",
        status.HTTP_401_UNAUTHORIZED,
    )


def get_current_admin(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: SQLAlchemySession = Depends(get_db),
) -> AdminUser:
    if not authorization:
        raise _unauthorized()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized()

    try:
        payload = decode_admin_access_token(token.strip())
        admin_id = UUID(str(payload["sub"]))
    except (JwtError, ValueError, KeyError):
        raise _unauthorized() from None

    admin = AdminUserRepository(db).get_by_id(admin_id)
    if admin is None or not admin.is_active:
        raise _unauthorized()

    return admin
