from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.core.config import get_settings


class JwtError(ValueError):
    pass


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _json_b64(value: dict[str, Any]) -> str:
    return _b64encode(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def _sign(message: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return _b64encode(digest)


def create_admin_access_token(
    admin_user_id: UUID | str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    if settings.jwt_algorithm != "HS256":
        raise JwtError("unsupported jwt algorithm")

    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.admin_jwt_expires_minutes)
    )
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {
        "sub": str(admin_user_id),
        "role": role,
        "typ": "admin_access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    signing_input = f"{_json_b64(header)}.{_json_b64(payload)}"
    return f"{signing_input}.{_sign(signing_input, settings.jwt_secret_key)}"


def decode_admin_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        header_raw, payload_raw, signature = token.split(".", 2)
        header = json.loads(_b64decode(header_raw))
        payload = json.loads(_b64decode(payload_raw))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise JwtError("invalid token") from exc

    if header.get("alg") != settings.jwt_algorithm or settings.jwt_algorithm != "HS256":
        raise JwtError("invalid token algorithm")

    signing_input = f"{header_raw}.{payload_raw}"
    expected_signature = _sign(signing_input, settings.jwt_secret_key)
    if not hmac.compare_digest(signature, expected_signature):
        raise JwtError("invalid token signature")

    if payload.get("typ") != "admin_access":
        raise JwtError("invalid token type")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at < int(datetime.now(timezone.utc).timestamp()):
        raise JwtError("expired token")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise JwtError("invalid token subject")

    return payload
