from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_responses import (
    AdminResponsesColumnsResponse,
    AdminResponsesExportRequest,
    AdminResponsesListResponse,
)
from app.services.admin_responses import (
    AdminResponsesQuery,
    export_admin_responses_csv,
    get_admin_response_columns,
    list_admin_responses,
)

router = APIRouter(prefix="/admin")


@router.get(
    "/events/{eventSlug}/responses",
    response_model=AdminResponsesListResponse,
    response_model_exclude_none=True,
)
def read_admin_responses(
    event_slug: str = Path(alias="eventSlug"),
    view: str = Query(default="summary"),
    status_filter: str = Query(default="all", alias="status"),
    completed_only: bool = Query(default=False, alias="completedOnly"),
    include_scores: bool = Query(default=True, alias="includeScores"),
    include_risk_flags: bool = Query(default=False, alias="includeRiskFlags"),
    include_completion_status: bool = Query(default=True, alias="includeCompletionStatus"),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminResponsesListResponse:
    return list_admin_responses(
        db,
        event_slug=event_slug,
        query=AdminResponsesQuery(
            view=view,
            status=status_filter,
            completed_only=completed_only,
            include_scores=include_scores,
            include_risk_flags=include_risk_flags,
            include_completion_status=include_completion_status,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        ),
    )


@router.get(
    "/events/{eventSlug}/responses/columns",
    response_model=AdminResponsesColumnsResponse,
    response_model_exclude_none=True,
)
def read_admin_response_columns(
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminResponsesColumnsResponse:
    return get_admin_response_columns(db, event_slug=event_slug)


@router.post("/events/{eventSlug}/responses/export.csv")
def post_admin_responses_export_csv(
    payload: AdminResponsesExportRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> Response:
    csv_file = export_admin_responses_csv(
        db,
        event_slug=event_slug,
        payload=payload,
        admin=current_admin,
    )
    return Response(
        content=csv_file.content,
        media_type=csv_file.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{csv_file.filename}"',
        },
    )
