from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.repositories.admin_audit_logs import AdminAuditLogRepository


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def create_audit_log(
    db: Session,
    *,
    admin_user_id: UUID | None,
    event_id: UUID | None,
    action: str,
    target_type: str,
    target_id: UUID | None,
    before_value: dict[str, Any] | None = None,
    after_value: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AdminAuditLog:
    return AdminAuditLogRepository(db).create_log(
        admin_user_id=admin_user_id,
        event_id=event_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_value=_json_safe(before_value),
        after_value=_json_safe(after_value),
        reason=reason,
    )
