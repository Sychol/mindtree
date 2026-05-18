from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.session import get_db
from app.models.admin import AdminUser
from app.schemas.admin_keywords import (
    AdminKeywordJobListResponse,
    AdminKeywordJobRetryRequest,
    AdminKeywordJobRetryResponse,
    AdminKeywordListResponse,
    AdminManualKeywordCreateRequest,
    AdminManualKeywordCreateResponse,
    AdminManualKeywordStatusRequest,
    AdminManualKeywordStatusResponse,
    AdminKeywordUpdateRequest,
    AdminKeywordUpdateResponse,
)
from app.services.admin_keywords import (
    create_manual_keyword,
    list_admin_keyword_jobs,
    list_admin_keywords,
    retry_admin_keyword_job,
    update_admin_keyword,
    update_manual_keyword_status,
)

router = APIRouter(prefix="/admin")


@router.get(
    "/events/{eventSlug}/keywords",
    response_model=AdminKeywordListResponse,
)
def read_admin_keywords(
    event_slug: str = Path(alias="eventSlug"),
    status_filter: str = Query(default="active", alias="status"),
    category: str | None = Query(default=None),
    origin_filter: str = Query(default="all", alias="origin"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminKeywordListResponse:
    return list_admin_keywords(
        db,
        event_slug=event_slug,
        status_filter=status_filter,
        category=category,
        origin_filter=origin_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/events/{eventSlug}/keywords/manual",
    response_model=AdminManualKeywordCreateResponse,
)
def post_manual_keyword(
    payload: AdminManualKeywordCreateRequest,
    event_slug: str = Path(alias="eventSlug"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminManualKeywordCreateResponse:
    return create_manual_keyword(
        db,
        event_slug=event_slug,
        payload=payload,
        admin=current_admin,
    )


@router.patch(
    "/keywords/{keywordId}",
    response_model=AdminKeywordUpdateResponse,
)
def patch_admin_keyword(
    payload: AdminKeywordUpdateRequest,
    keyword_id: UUID = Path(alias="keywordId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminKeywordUpdateResponse:
    return update_admin_keyword(db, keyword_id=keyword_id, payload=payload, admin=current_admin)


@router.patch(
    "/keywords/{keywordId}/manual-status",
    response_model=AdminManualKeywordStatusResponse,
)
def patch_manual_keyword_status(
    payload: AdminManualKeywordStatusRequest,
    keyword_id: UUID = Path(alias="keywordId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminManualKeywordStatusResponse:
    return update_manual_keyword_status(db, keyword_id=keyword_id, payload=payload, admin=current_admin)


@router.get(
    "/events/{eventSlug}/keyword-jobs",
    response_model=AdminKeywordJobListResponse,
    response_model_exclude_none=True,
)
def read_admin_keyword_jobs(
    event_slug: str = Path(alias="eventSlug"),
    status_filter: str = Query(default="failed", alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminKeywordJobListResponse:
    return list_admin_keyword_jobs(
        db,
        event_slug=event_slug,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/keyword-jobs/{jobId}/retry",
    response_model=AdminKeywordJobRetryResponse,
    response_model_exclude_none=True,
)
def post_admin_keyword_job_retry(
    payload: AdminKeywordJobRetryRequest,
    job_id: UUID = Path(alias="jobId"),
    db: Session = Depends(get_db),
    current_admin: AdminUser = Depends(get_current_admin),
) -> AdminKeywordJobRetryResponse:
    return retry_admin_keyword_job(db, job_id=job_id, payload=payload, admin=current_admin)
