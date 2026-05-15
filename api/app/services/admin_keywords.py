from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.admin import AdminUser
from app.models.enums import KeywordCategory, KeywordJobStatus, KeywordStatus
from app.models.keyword import Keyword, KeywordJob
from app.repositories.events import EventRepository
from app.repositories.keyword_jobs import KeywordJobRepository
from app.repositories.keywords import KeywordRepository
from app.schemas.admin_keywords import (
    AdminKeywordItem,
    AdminKeywordJobItem,
    AdminKeywordJobListResponse,
    AdminKeywordJobRetryRequest,
    AdminKeywordJobRetryResponse,
    AdminKeywordListResponse,
    AdminKeywordUpdateRequest,
    AdminKeywordUpdateResponse,
)
from app.services.audit_log import create_audit_log


def _event_id_or_404(db: Session, event_slug: str) -> UUID:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return event.id


def _keyword_item(keyword: Keyword) -> AdminKeywordItem:
    return AdminKeywordItem(
        id=keyword.id,
        keywordText=keyword.keyword_text,
        normalizedKeyword=keyword.normalized_keyword,
        category=keyword.category,
        weight=float(keyword.weight),
        status=keyword.status,
        extractionMethod=keyword.extraction_method,
        sourceType=keyword.source_type,
        sourceId=keyword.source_id,
        createdAt=keyword.created_at,
    )


def _job_item(job: KeywordJob) -> AdminKeywordJobItem:
    error_message = job.error_message
    if error_message and len(error_message) > 240:
        error_message = f"{error_message[:237]}..."
    return AdminKeywordJobItem(
        id=job.id,
        sourceType=job.source_type,
        sourceId=job.source_id,
        status=job.status,
        attempts=job.attempts,
        maxAttempts=job.max_attempts,
        fallbackUsed=job.fallback_used,
        provider=job.provider,
        errorMessage=error_message,
        createdAt=job.created_at,
        updatedAt=job.updated_at,
    )


def _validate_keyword_filters(status_filter: str, category: str | None) -> None:
    if status_filter != "all" and status_filter not in {item.value for item in KeywordStatus}:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 키워드 상태입니다.")
    if category and category not in {item.value for item in KeywordCategory}:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 키워드 카테고리입니다.")


def list_admin_keywords(
    db: Session,
    *,
    event_slug: str,
    status_filter: str,
    category: str | None,
    limit: int,
    offset: int,
) -> AdminKeywordListResponse:
    _validate_keyword_filters(status_filter, category)
    event_id = _event_id_or_404(db, event_slug)
    repo = KeywordRepository(db)
    items = repo.list_admin_keywords(
        event_id=event_id,
        status_filter=status_filter,
        category=category,
        limit=limit,
        offset=offset,
    )
    total = repo.count_admin_keywords(
        event_id=event_id,
        status_filter=status_filter,
        category=category,
    )
    return AdminKeywordListResponse(items=[_keyword_item(item) for item in items], total=total)


def update_admin_keyword(
    db: Session,
    *,
    keyword_id: UUID,
    payload: AdminKeywordUpdateRequest,
    admin: AdminUser,
) -> AdminKeywordUpdateResponse:
    keyword = KeywordRepository(db).get_by_id(keyword_id)
    if keyword is None:
        raise AppError(ErrorCode.BAD_REQUEST, "키워드를 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)

    before = {
        "normalizedKeyword": keyword.normalized_keyword,
        "category": keyword.category,
        "status": keyword.status,
    }
    changed = False

    if payload.normalized_keyword is not None:
        normalized = payload.normalized_keyword.strip()
        if not 1 <= len(normalized) <= 40:
            raise AppError(ErrorCode.BAD_REQUEST, "정규화 키워드는 1~40자여야 합니다.")
        keyword.normalized_keyword = normalized
        keyword.extraction_method = "admin"
        changed = True

    if payload.category is not None:
        if payload.category not in {item.value for item in KeywordCategory}:
            raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 키워드 카테고리입니다.")
        keyword.category = payload.category
        changed = True

    if payload.status is not None:
        if payload.status not in {item.value for item in KeywordStatus}:
            raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 키워드 상태입니다.")
        keyword.status = payload.status
        changed = True

    if not changed:
        raise AppError(ErrorCode.BAD_REQUEST, "변경할 값이 없습니다.")

    db.add(keyword)
    after = {
        "normalizedKeyword": keyword.normalized_keyword,
        "category": keyword.category,
        "status": keyword.status,
    }
    action = "keyword.hide" if keyword.status in {"hidden", "excluded"} else "keyword.edit"
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=keyword.event_id,
        action=action,
        target_type="keyword",
        target_id=keyword.id,
        before_value=before,
        after_value=after,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(keyword)
    return AdminKeywordUpdateResponse(keyword=_keyword_item(keyword), auditLogCreated=True)


def _validate_job_filter(status_filter: str) -> None:
    if status_filter != "all" and status_filter not in {item.value for item in KeywordJobStatus}:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 keyword job 상태입니다.")


def list_admin_keyword_jobs(
    db: Session,
    *,
    event_slug: str,
    status_filter: str,
    limit: int,
    offset: int,
) -> AdminKeywordJobListResponse:
    _validate_job_filter(status_filter)
    event_id = _event_id_or_404(db, event_slug)
    repo = KeywordJobRepository(db)
    items = repo.list_admin_jobs(
        event_id=event_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    total = repo.count_admin_jobs(event_id=event_id, status_filter=status_filter)
    return AdminKeywordJobListResponse(items=[_job_item(item) for item in items], total=total)


def retry_admin_keyword_job(
    db: Session,
    *,
    job_id: UUID,
    payload: AdminKeywordJobRetryRequest,
    admin: AdminUser,
) -> AdminKeywordJobRetryResponse:
    repo = KeywordJobRepository(db)
    job = repo.get_job_by_id(job_id)
    if job is None:
        raise AppError(ErrorCode.BAD_REQUEST, "keyword job을 찾을 수 없습니다.", status.HTTP_404_NOT_FOUND)
    if job.status not in {KeywordJobStatus.FAILED.value, KeywordJobStatus.RETRY_WAIT.value}:
        raise AppError(ErrorCode.BAD_REQUEST, "failed 또는 retry_wait 상태만 재시도할 수 있습니다.")

    before = {
        "status": job.status,
        "attempts": job.attempts,
        "errorMessage": job.error_message,
        "lockedAt": job.locked_at,
        "nextRunAt": job.next_run_at,
    }
    repo.reset_job_for_retry(job)
    after = {
        "status": job.status,
        "attempts": job.attempts,
        "lockedAt": job.locked_at,
        "nextRunAt": job.next_run_at,
    }
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=job.event_id,
        action="keyword_job.retry",
        target_type="keyword_job",
        target_id=job.id,
        before_value=before,
        after_value=after,
        reason=payload.reason,
    )
    db.commit()
    db.refresh(job)
    return AdminKeywordJobRetryResponse(job=_job_item(job), auditLogCreated=True)
