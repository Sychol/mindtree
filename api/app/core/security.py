import hashlib
import hmac
import secrets

from app.core.config import get_settings


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
