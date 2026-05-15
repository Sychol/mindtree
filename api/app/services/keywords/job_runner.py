from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import get_settings
from app.models.card import MindCard
from app.models.enums import KeywordJobStatus, KeywordSourceType, PublicStatus, SafetyStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.repositories.cards import MindCardRepository
from app.repositories.keyword_jobs import KeywordJobRepository
from app.repositories.keywords import KeywordRepository
from app.repositories.replies import ReplyRepository
from app.repositories.risk_flags import RiskFlagRepository
from app.services.keywords.fallback_extractor import extract_fallback_keywords
from app.services.keywords.llm_keyword_extractor import (
    KeywordLlmFailed,
    KeywordLlmUnavailable,
    extract_keywords_with_llm,
)
from app.services.keywords.types import KeywordCandidate

RETRY_WAIT_SECONDS = 15


@dataclass(frozen=True)
class KeywordJobRunResult:
    job_id: UUID | None
    status: str
    excluded: bool = False
    fallback_used: bool = False
    created_keyword_count: int = 0
    error_message: str | None = None


@dataclass(frozen=True)
class KeywordJobRunSummary:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retry_wait_count: int
    excluded_count: int
    fallback_used_count: int
    created_keyword_count: int


@dataclass(frozen=True)
class _SourceContext:
    source: MindCard | Reply
    source_hint: str
    input_text: str


class KeywordJobProcessingError(RuntimeError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_error_message(message: str) -> str:
    allowed_messages = {
        "LLM timeout",
        "LLM schema parse failed",
        "LLM keyword extraction failed",
        "LLM disabled",
        "fallback disabled",
        "fallback keyword extraction failed",
        "source not found",
        "source excluded",
        "source not public",
        "source public restricted",
        "unsupported source type",
    }
    return message if message in allowed_messages else "keyword job processing failed"


def _keyword_snapshot(candidates: list[KeywordCandidate]) -> list[dict[str, object]]:
    return [
        {
            "text": candidate.text,
            "normalized": candidate.normalized,
            "category": candidate.category,
            "weight": candidate.weight,
        }
        for candidate in candidates
    ]


def _load_source_context(db: SQLAlchemySession, job: KeywordJob) -> _SourceContext | None:
    if job.source_type == KeywordSourceType.MIND_CARD.value:
        card = MindCardRepository(db).get_by_id(job.source_id)
        if card is None:
            return None
        return _SourceContext(
            source=card,
            source_hint=card.prompt_type,
            input_text=card.content_redacted or card.content_raw,
        )

    if job.source_type == KeywordSourceType.REPLY.value:
        reply = ReplyRepository(db).get_by_id(job.source_id)
        if reply is None:
            return None
        return _SourceContext(
            source=reply,
            source_hint=reply.reply_type,
            input_text=reply.content_redacted or reply.content_raw,
        )

    raise KeywordJobProcessingError("unsupported source type")


def _source_exclusion_reason(db: SQLAlchemySession, source: MindCard | Reply) -> str | None:
    if source.safety_status == SafetyStatus.EXCLUDE.value or source.public_status == PublicStatus.EXCLUDED.value:
        return "source_excluded"
    if source.safety_status != SafetyStatus.SAFE.value or source.public_status != PublicStatus.PUBLIC.value:
        return "source_not_public"

    risk_flag = RiskFlagRepository(db).get_by_session_id(source.session_id)
    if risk_flag and (risk_flag.public_restriction or risk_flag.crisis_expression_detected):
        return "source_public_restricted"

    return None


def _mark_succeeded(
    db: SQLAlchemySession,
    *,
    job: KeywordJob,
    output_snapshot: dict[str, object],
    provider: str,
    fallback_used: bool,
    excluded: bool = False,
    created_keyword_count: int = 0,
) -> KeywordJobRunResult:
    KeywordJobRepository(db).mark_job_succeeded(
        job_id=job.id,
        output_snapshot=output_snapshot,
        provider=provider,
        fallback_used=fallback_used,
    )
    db.commit()
    return KeywordJobRunResult(
        job_id=job.id,
        status=KeywordJobStatus.SUCCEEDED.value,
        excluded=excluded,
        fallback_used=fallback_used,
        created_keyword_count=created_keyword_count,
    )


def _mark_failure(
    db: SQLAlchemySession,
    *,
    job: KeywordJob,
    error_message: str,
    provider: str = "disabled",
    fallback_used: bool = False,
) -> KeywordJobRunResult:
    safe_message = _safe_error_message(error_message)
    output_snapshot = {
        "error": safe_message,
        "provider": provider,
        "fallback_used": fallback_used,
    }
    repository = KeywordJobRepository(db)
    if (job.attempts or 0) < (job.max_attempts or 1):
        repository.mark_job_retry_wait(
            job_id=job.id,
            error_message=safe_message,
            next_run_at=_now() + timedelta(seconds=RETRY_WAIT_SECONDS),
            output_snapshot=output_snapshot,
            provider=provider,
            fallback_used=fallback_used,
        )
        db.commit()
        return KeywordJobRunResult(
            job_id=job.id,
            status=KeywordJobStatus.RETRY_WAIT.value,
            fallback_used=fallback_used,
            error_message=safe_message,
        )

    repository.mark_job_failed(
        job_id=job.id,
        error_message=safe_message,
        output_snapshot=output_snapshot,
        provider=provider,
        fallback_used=fallback_used,
    )
    db.commit()
    return KeywordJobRunResult(
        job_id=job.id,
        status=KeywordJobStatus.FAILED.value,
        fallback_used=fallback_used,
        error_message=safe_message,
    )


def _extract_candidates(
    *,
    text: str,
    source_type: str,
    source_hint: str,
) -> tuple[list[KeywordCandidate], str, bool, str | None]:
    settings = get_settings()
    provider = "disabled"
    fallback_reason: str | None = None

    if settings.llm_enabled:
        try:
            llm_result = extract_keywords_with_llm(
                settings=settings,
                text=text,
                source_type=source_type,
                source_hint=source_hint,
            )
            return llm_result.candidates, llm_result.provider, False, None
        except KeywordLlmUnavailable as exc:
            fallback_reason = str(exc)
        except KeywordLlmFailed as exc:
            fallback_reason = str(exc)
            provider = settings.llm_provider.strip().lower() or "unknown"
    else:
        fallback_reason = "LLM disabled"

    if not settings.keyword_fallback_enabled:
        raise KeywordJobProcessingError("fallback disabled")

    try:
        candidates = extract_fallback_keywords(
            text,
            source_type=source_type,
            source_hint=source_hint,
        )
    except Exception as exc:
        raise KeywordJobProcessingError("fallback keyword extraction failed") from exc

    return candidates, provider, True, fallback_reason


def _process_claimed_job(db: SQLAlchemySession, job_id: UUID) -> KeywordJobRunResult:
    repository = KeywordJobRepository(db)
    job = repository.get_job_by_id(job_id)
    if job is None:
        return KeywordJobRunResult(job_id=None, status=KeywordJobStatus.FAILED.value, error_message="source not found")
    if job.status != KeywordJobStatus.PROCESSING.value:
        return KeywordJobRunResult(job_id=job.id, status="not_claimed")

    try:
        context = _load_source_context(db, job)
    except KeywordJobProcessingError as exc:
        return _mark_failure(db, job=job, error_message=str(exc))

    if context is None:
        return _mark_failure(db, job=job, error_message="source not found")

    exclusion_reason = _source_exclusion_reason(db, context.source)
    if exclusion_reason is not None:
        KeywordRepository(db).delete_keywords_by_job_id(job.id)
        output_snapshot = {
            "keywords": [],
            "excluded": True,
            "excluded_reason": exclusion_reason,
            "provider": "policy",
            "fallback_used": False,
        }
        return _mark_succeeded(
            db,
            job=job,
            output_snapshot=output_snapshot,
            provider="policy",
            fallback_used=False,
            excluded=True,
        )

    try:
        candidates, provider, fallback_used, fallback_reason = _extract_candidates(
            text=context.input_text,
            source_type=job.source_type,
            source_hint=context.source_hint,
        )
    except KeywordJobProcessingError as exc:
        return _mark_failure(db, job=job, error_message=str(exc), fallback_used=True)

    keyword_repository = KeywordRepository(db)
    keyword_repository.delete_keywords_by_job_id(job.id)
    keywords = keyword_repository.create_keywords(
        event_id=job.event_id,
        source_type=job.source_type,
        source_id=job.source_id,
        job_id=job.id,
        candidates=candidates,
    )
    output_snapshot = {
        "keywords": _keyword_snapshot(candidates),
        "keyword_count": len(keywords),
        "extraction_method": "fallback" if fallback_used else "llm",
        "fallback_used": fallback_used,
        "fallback_reason": _safe_error_message(fallback_reason) if fallback_reason else None,
        "excluded": False,
        "provider": provider,
    }
    return _mark_succeeded(
        db,
        job=job,
        output_snapshot=output_snapshot,
        provider=provider,
        fallback_used=fallback_used,
        created_keyword_count=len(keywords),
    )


def process_job(db: SQLAlchemySession, job_id: UUID) -> KeywordJobRunResult:
    repository = KeywordJobRepository(db)
    job = repository.get_job_by_id(job_id)
    if job is None:
        return KeywordJobRunResult(job_id=None, status=KeywordJobStatus.FAILED.value, error_message="source not found")
    if job.status != KeywordJobStatus.PROCESSING.value:
        claimed = repository.claim_job_by_id(job_id=job_id, now=_now())
        if claimed is None:
            db.rollback()
            return KeywordJobRunResult(job_id=job_id, status="not_claimed")
        db.commit()

    return _process_claimed_job(db, job_id)


def process_next_jobs(db: SQLAlchemySession, *, limit: int | None = None) -> KeywordJobRunSummary:
    settings = get_settings()
    safe_limit = limit or settings.keyword_worker_batch_size
    repository = KeywordJobRepository(db)
    jobs = repository.claim_next_jobs(limit=safe_limit, now=_now())
    job_ids = [job.id for job in jobs]
    db.commit()

    results = [_process_claimed_job(db, job_id) for job_id in job_ids]
    return KeywordJobRunSummary(
        claimed_count=len(job_ids),
        succeeded_count=sum(1 for result in results if result.status == KeywordJobStatus.SUCCEEDED.value),
        failed_count=sum(1 for result in results if result.status == KeywordJobStatus.FAILED.value),
        retry_wait_count=sum(1 for result in results if result.status == KeywordJobStatus.RETRY_WAIT.value),
        excluded_count=sum(1 for result in results if result.excluded),
        fallback_used_count=sum(1 for result in results if result.fallback_used),
        created_keyword_count=sum(result.created_keyword_count for result in results),
    )
