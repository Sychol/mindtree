from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.repositories.admin_audit_logs import AdminAuditLogRepository
from app.repositories.events import EventRepository
from app.schemas.admin_audit_logs import AdminAuditLogItem, AdminAuditLogListResponse


def list_admin_audit_logs(
    db: Session,
    *,
    event_slug: str,
    limit: int,
    offset: int,
    action: str | None,
    target_type: str | None,
) -> AdminAuditLogListResponse:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    repo = AdminAuditLogRepository(db)
    items = repo.list_logs(
        event_id=event.id,
        limit=limit,
        offset=offset,
        action=action,
        target_type=target_type,
    )
    total = repo.count_logs(event_id=event.id, action=action, target_type=target_type)
    return AdminAuditLogListResponse(
        items=[
            AdminAuditLogItem(
                id=item.id,
                adminUserId=item.admin_user_id,
                action=item.action,
                targetType=item.target_type,
                targetId=item.target_id,
                reason=item.reason,
                createdAt=item.created_at,
            )
            for item in items
        ],
        total=total,
    )
