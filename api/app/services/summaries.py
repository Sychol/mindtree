from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.models.enums import SessionStatus
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.models.summary import Summary
from app.repositories.risk_flags import RiskFlagRepository
from app.repositories.scale_scores import ScaleScoreRepository
from app.repositories.sessions import SessionRepository
from app.repositories.summaries import SummaryRepository
from app.schemas.summaries import (
    RiskNoticePayload,
    SummaryPayload,
    SummaryResponse,
    SummaryViewedResponse,
)
from app.services.llm.base import LlmSummaryRequest, LlmSummaryResult
from app.services.llm.provider import get_summary_llm_provider
from app.services.sessions import status_at_least
from app.services.summary_templates import TemplateSummary, build_template_summary

REQUIRED_SCALE_CODES = {"phq9", "pcl5", "kmies", "kscs"}
SUMMARY_ALLOWED_STATUSES = {
    SessionStatus.QUESTIONS_COMPLETED.value,
    SessionStatus.SUMMARY_VIEWED.value,
    SessionStatus.CARD_CREATED.value,
    SessionStatus.REPLY_CREATED.value,
    SessionStatus.COMPLETED.value,
}


@dataclass(frozen=True)
class _SummaryInputs:
    session: EventSession
    event_id: UUID
    scale_scores: list[ScaleScore]
    risk_flag: RiskFlag
    template: TemplateSummary


def _ensure_summary_status(session: EventSession) -> None:
    if session.status not in SUMMARY_ALLOWED_STATUSES:
        raise AppError(
            ErrorCode.QUESTIONS_NOT_COMPLETED,
            "문항 응답 완료 후 요약을 확인할 수 있습니다.",
            status.HTTP_403_FORBIDDEN,
            details={"status": session.status},
        )


def _load_inputs(db: SQLAlchemySession, session_id: UUID) -> _SummaryInputs:
    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    session, event = row
    _ensure_summary_status(session)

    scale_scores = ScaleScoreRepository(db).list_by_session_id(session.id)
    found_codes = {scale_score.scale_code for scale_score in scale_scores}
    missing_codes = sorted(REQUIRED_SCALE_CODES - found_codes)
    risk_flag = RiskFlagRepository(db).get_by_session_id(session.id)

    if missing_codes or risk_flag is None:
        raise AppError(
            ErrorCode.QUESTIONS_NOT_COMPLETED,
            "요약 생성에 필요한 문항 결과가 아직 준비되지 않았습니다.",
            status.HTTP_409_CONFLICT,
            details={
                "missingScaleScores": missing_codes,
                "riskFlagsReady": risk_flag is not None,
            },
        )

    return _SummaryInputs(
        session=session,
        event_id=event.id,
        scale_scores=scale_scores,
        risk_flag=risk_flag,
        template=build_template_summary(scale_scores, risk_flag),
    )


def _polish_with_timeout(
    request: LlmSummaryRequest,
) -> tuple[LlmSummaryResult | None, bool]:
    settings = get_settings()
    provider = get_summary_llm_provider(settings)
    if provider.provider_name == "disabled":
        result = provider.polish_summary(request)
        return result, False

    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(provider.polish_summary, request)
    try:
        result = future.result(timeout=max(settings.llm_timeout_seconds, 1))
        return result, False
    except TimeoutError:
        future.cancel()
        return None, True
    except Exception:
        return None, True
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _create_summary(
    db: SQLAlchemySession,
    inputs: _SummaryInputs,
) -> Summary:
    request = LlmSummaryRequest(
        template_text=inputs.template.template_text,
        signals=inputs.template.signals,
        recommended_action=inputs.template.recommended_action,
    )
    result, failed = _polish_with_timeout(request)

    llm_text: str | None = None
    final_text = inputs.template.template_text
    generation_mode = "template"
    if result and result.used:
        llm_text = result.text
        final_text = result.text
        generation_mode = "mock" if result.provider == "mock" else "llm"
    elif failed:
        generation_mode = "fallback"

    return SummaryRepository(db).create_summary(
        event_id=inputs.event_id,
        session_id=inputs.session.id,
        template_text=inputs.template.template_text,
        llm_text=llm_text,
        final_text=final_text,
        generation_mode=generation_mode,
    )


def _response_from_summary(
    summary: Summary,
    template: TemplateSummary,
) -> SummaryResponse:
    return SummaryResponse(
        summary=SummaryPayload(
            id=summary.id,
            final_text=summary.final_text,
            generation_mode=summary.generation_mode,
            help_notice_required=template.help_notice_required,
            signals=template.signals,
            recommended_action=template.recommended_action,
            is_diagnosis=False,
        ),
        risk_notice=RiskNoticePayload(
            show_help_notice=template.help_notice_required,
            text=template.risk_notice_text,
        ),
    )


def get_or_create_summary(
    db: SQLAlchemySession,
    session_id: UUID,
) -> SummaryResponse:
    inputs = _load_inputs(db, session_id)
    repository = SummaryRepository(db)
    summary = repository.get_by_session_id(session_id)
    if summary is None:
        summary = _create_summary(db, inputs)
        db.commit()
        db.refresh(summary)

    return _response_from_summary(summary, inputs.template)


def mark_summary_viewed(
    db: SQLAlchemySession,
    session_id: UUID,
) -> SummaryViewedResponse:
    inputs = _load_inputs(db, session_id)
    repository = SummaryRepository(db)
    summary = repository.get_by_session_id(session_id)
    if summary is None:
        summary = _create_summary(db, inputs)

    viewed_at = summary.viewed_at or datetime.now(timezone.utc)
    if summary.viewed_at is None:
        repository.update_viewed_at(summary, viewed_at)

    if inputs.session.status == SessionStatus.QUESTIONS_COMPLETED.value:
        SessionRepository(db).set_status_and_step(
            inputs.session,
            SessionStatus.SUMMARY_VIEWED.value,
            "cards/new",
        )
    elif status_at_least(inputs.session.status, SessionStatus.SUMMARY_VIEWED.value):
        inputs.session.last_step = inputs.session.last_step or "cards/new"

    db.commit()
    db.refresh(inputs.session)
    db.refresh(summary)

    return SummaryViewedResponse(
        session_status=inputs.session.status,
        viewed_at=summary.viewed_at or viewed_at,
    )
