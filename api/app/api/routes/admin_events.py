from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_events import AdminDashboardResponse
from app.services.admin_dashboard import get_admin_dashboard

router = APIRouter(prefix="/admin")


@router.get(
    "/events/{eventSlug}/dashboard",
    response_model=AdminDashboardResponse,
)
def read_admin_dashboard(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminDashboardResponse:
    return get_admin_dashboard(db, event_slug)
