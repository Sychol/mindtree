from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.repositories.admin_queries import AdminQueryRepository
from app.repositories.events import EventRepository
from app.schemas.admin_events import (
    AdminDashboardEvent,
    AdminDashboardMetrics,
    AdminDashboardResponse,
)


def get_admin_dashboard(db: Session, event_slug: str) -> AdminDashboardResponse:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    metrics = AdminQueryRepository(db).dashboard_metrics(event.id)
    return AdminDashboardResponse(
        event=AdminDashboardEvent(slug=event.slug, status=event.status),
        metrics=AdminDashboardMetrics(**metrics),
    )
