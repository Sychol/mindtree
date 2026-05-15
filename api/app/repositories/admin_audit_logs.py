from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.repositories.base import BaseRepository


class AdminAuditLogRepository(BaseRepository[AdminAuditLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, AdminAuditLog)

    def create_log(
        self,
        *,
        event_id: UUID | None,
        admin_user_id: UUID | None,
        action: str,
        target_type: str,
        target_id: UUID | None,
        before_value: dict[str, Any] | None,
        after_value: dict[str, Any] | None,
        reason: str | None,
    ) -> AdminAuditLog:
        log = AdminAuditLog(
            event_id=event_id,
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before_value=before_value,
            after_value=after_value,
            reason=reason,
        )
        self.db.add(log)
        self.db.flush()
        return log

    def list_logs(
        self,
        *,
        event_id: UUID,
        limit: int,
        offset: int,
        action: str | None = None,
        target_type: str | None = None,
    ) -> list[AdminAuditLog]:
        statement = select(AdminAuditLog).where(AdminAuditLog.event_id == event_id)
        if action:
            statement = statement.where(AdminAuditLog.action == action)
        if target_type:
            statement = statement.where(AdminAuditLog.target_type == target_type)
        statement = statement.order_by(AdminAuditLog.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(statement).scalars())

    def count_logs(
        self,
        *,
        event_id: UUID,
        action: str | None = None,
        target_type: str | None = None,
    ) -> int:
        statement = select(func.count(AdminAuditLog.id)).where(AdminAuditLog.event_id == event_id)
        if action:
            statement = statement.where(AdminAuditLog.action == action)
        if target_type:
            statement = statement.where(AdminAuditLog.target_type == target_type)
        return int(self.db.execute(statement).scalar_one() or 0)
