from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_audit_logs import AdminAuditLogListResponse
from app.services.admin_audit_logs import list_admin_audit_logs

router = APIRouter(prefix="/admin")


@router.get(
    "/events/{eventSlug}/audit-logs",
    response_model=AdminAuditLogListResponse,
    response_model_exclude_none=True,
)
def read_admin_audit_logs(
    event_slug: str = Path(alias="eventSlug"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None),
    target_type: str | None = Query(default=None, alias="targetType"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminAuditLogListResponse:
    return list_admin_audit_logs(
        db,
        event_slug=event_slug,
        limit=limit,
        offset=offset,
        action=action,
        target_type=target_type,
    )
