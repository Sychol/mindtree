from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import KeywordJobStatus
from app.models.keyword import KeywordJob
from app.repositories.base import BaseRepository


class KeywordJobRepository(BaseRepository[KeywordJob]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, KeywordJob)

    def create_pending_job(
        self,
        *,
        event_id: UUID,
        source_type: str,
        source_id: UUID,
        input_snapshot: dict[str, Any],
    ) -> KeywordJob:
        job = KeywordJob(
            event_id=event_id,
            source_type=source_type,
            source_id=source_id,
            status="pending",
            input_snapshot=input_snapshot,
        )
        self.db.add(job)
        self.db.flush()
        return job

    def get_job_by_id(self, job_id: UUID) -> KeywordJob | None:
        return self.db.get(KeywordJob, job_id)

    def list_by_source(self, source_type: str, source_id: UUID) -> list[KeywordJob]:
        statement = select(KeywordJob).where(
            KeywordJob.source_type == source_type,
            KeywordJob.source_id == source_id,
        )
        return list(self.db.execute(statement).scalars())

    def claim_next_jobs(self, *, limit: int, now) -> list[KeywordJob]:
        safe_limit = max(1, min(limit, 100))
        statement = (
            select(KeywordJob)
            .where(
                KeywordJob.status.in_(
                    [
                        KeywordJobStatus.PENDING.value,
                        KeywordJobStatus.RETRY_WAIT.value,
                    ]
                ),
                or_(
                    KeywordJob.next_run_at.is_(None),
                    KeywordJob.next_run_at <= now,
                ),
            )
            .order_by(KeywordJob.created_at.asc())
            .limit(safe_limit)
            .with_for_update(skip_locked=True)
        )
        jobs = list(self.db.execute(statement).scalars())
        for job in jobs:
            job.status = KeywordJobStatus.PROCESSING.value
            job.locked_at = now
            job.next_run_at = None
            job.attempts = (job.attempts or 0) + 1
            self.db.add(job)
        self.db.flush()
        return jobs

    def claim_job_by_id(self, *, job_id: UUID, now) -> KeywordJob | None:
        statement = (
            select(KeywordJob)
            .where(
                KeywordJob.id == job_id,
                KeywordJob.status.in_(
                    [
                        KeywordJobStatus.PENDING.value,
                        KeywordJobStatus.RETRY_WAIT.value,
                    ]
                ),
                or_(
                    KeywordJob.next_run_at.is_(None),
                    KeywordJob.next_run_at <= now,
                ),
            )
            .with_for_update(skip_locked=True)
        )
        job = self.db.execute(statement).scalar_one_or_none()
        if job is None:
            return None

        job.status = KeywordJobStatus.PROCESSING.value
        job.locked_at = now
        job.next_run_at = None
        job.attempts = (job.attempts or 0) + 1
        self.db.add(job)
        self.db.flush()
        return job

    def mark_job_succeeded(
        self,
        *,
        job_id: UUID,
        output_snapshot: dict[str, Any],
        provider: str,
        fallback_used: bool,
    ) -> KeywordJob | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None

        job.status = KeywordJobStatus.SUCCEEDED.value
        job.provider = provider
        job.fallback_used = fallback_used
        job.output_snapshot = output_snapshot
        job.error_message = None
        job.locked_at = None
        job.next_run_at = None
        self.db.add(job)
        self.db.flush()
        return job

    def mark_job_retry_wait(
        self,
        *,
        job_id: UUID,
        error_message: str,
        next_run_at,
        output_snapshot: dict[str, Any] | None = None,
        provider: str | None = None,
        fallback_used: bool | None = None,
    ) -> KeywordJob | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None

        job.status = KeywordJobStatus.RETRY_WAIT.value
        job.error_message = error_message
        job.next_run_at = next_run_at
        job.locked_at = None
        if output_snapshot is not None:
            job.output_snapshot = output_snapshot
        if provider is not None:
            job.provider = provider
        if fallback_used is not None:
            job.fallback_used = fallback_used
        self.db.add(job)
        self.db.flush()
        return job

    def mark_job_failed(
        self,
        *,
        job_id: UUID,
        error_message: str,
        output_snapshot: dict[str, Any] | None = None,
        provider: str | None = None,
        fallback_used: bool | None = None,
    ) -> KeywordJob | None:
        job = self.get_job_by_id(job_id)
        if job is None:
            return None

        job.status = KeywordJobStatus.FAILED.value
        job.error_message = error_message
        job.next_run_at = None
        job.locked_at = None
        if output_snapshot is not None:
            job.output_snapshot = output_snapshot
        if provider is not None:
            job.provider = provider
        if fallback_used is not None:
            job.fallback_used = fallback_used
        self.db.add(job)
        self.db.flush()
        return job

    def list_admin_jobs(
        self,
        *,
        event_id: UUID,
        status_filter: str,
        limit: int,
        offset: int,
    ) -> list[KeywordJob]:
        statement = select(KeywordJob).where(KeywordJob.event_id == event_id)
        if status_filter != "all":
            statement = statement.where(KeywordJob.status == status_filter)
        statement = statement.order_by(KeywordJob.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(statement).scalars())

    def count_admin_jobs(self, *, event_id: UUID, status_filter: str) -> int:
        statement = select(func.count(KeywordJob.id)).where(KeywordJob.event_id == event_id)
        if status_filter != "all":
            statement = statement.where(KeywordJob.status == status_filter)
        return int(self.db.execute(statement).scalar_one() or 0)

    def reset_job_for_retry(self, job: KeywordJob) -> KeywordJob:
        job.status = KeywordJobStatus.PENDING.value
        job.attempts = 0
        job.locked_at = None
        job.next_run_at = None
        job.error_message = None
        self.db.add(job)
        self.db.flush()
        return job
