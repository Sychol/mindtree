from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import SessionStatus
from app.models.event import Event
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.services.llm.base import LlmSummaryRequest
from app.services.llm.provider import get_summary_llm_provider


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_session_with_results(
    db_session: Session,
    event: Event,
) -> EventSession:
    session = EventSession(
        event_id=event.id,
        anonymous_key_hash=f"anon-{uuid4()}",
        resume_token_hash=f"resume-{uuid4()}",
        status=SessionStatus.QUESTIONS_COMPLETED.value,
        last_step="summary",
        client_meta={},
    )
    db_session.add(session)
    db_session.flush()
    for scale_code, raw_score, severity_level in [
        ("phq9", Decimal("21"), "severe_depression_score_range"),
        ("pcl5", Decimal("35"), "high_risk"),
        ("kmies", Decimal("40"), "high"),
        ("kscs", Decimal("2.0"), "low"),
    ]:
        db_session.add(
            ScaleScore(
                event_id=event.id,
                session_id=session.id,
                scale_code=scale_code,
                raw_score=raw_score,
                severity_level=severity_level,
                sub_scores={},
                rule_version="v2-2026-05-13-scale-cutoffs",
            )
        )
    db_session.add(
        RiskFlag(
            event_id=event.id,
            session_id=session.id,
            phq9_item9_positive=True,
            crisis_expression_detected=False,
            trauma_high_signal=True,
            moral_injury_high_signal=True,
            public_restriction=True,
            help_notice_required=True,
            details={"kscs_level": "low"},
            rule_version="v2-2026-05-13-scale-cutoffs",
        )
    )
    db_session.commit()
    db_session.refresh(session)
    return session


def _set_llm_env(monkeypatch, *, enabled: bool, provider: str) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()


def test_llm_disabled_selects_disabled_provider(monkeypatch) -> None:
    _set_llm_env(monkeypatch, enabled=False, provider="mock")

    provider = get_summary_llm_provider(get_settings())

    assert provider.provider_name == "disabled"


def test_mock_provider_is_deterministic_and_avoids_forbidden_language(monkeypatch) -> None:
    _set_llm_env(monkeypatch, enabled=True, provider="mock")
    provider = get_summary_llm_provider(get_settings())
    request = LlmSummaryRequest(
        template_text="최근 마음에 긴장 신호가 나타납니다.",
        signals=["일상 에너지가 낮아진 느낌이 있을 수 있습니다."],
        recommended_action="잠시 숨을 고르는 것이 도움이 될 수 있습니다.",
    )

    first = provider.polish_summary(request)
    second = provider.polish_summary(request)

    assert provider.provider_name == "mock"
    assert first == second
    assert "우울증입니다" not in first.text
    assert "PTSD입니다" not in first.text
    assert "자살위험입니다" not in first.text


def test_summary_api_uses_mock_generation_mode(
    monkeypatch,
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    _set_llm_env(monkeypatch, enabled=True, provider="mock")
    event = event_factory()
    session = _create_session_with_results(db_session, event)

    response = client.get(f"/api/sessions/{session.id}/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["generationMode"] == "mock"
    assert data["riskNotice"]["showHelpNotice"] is True


def test_llm_provider_failure_falls_back_to_template(
    monkeypatch,
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    _set_llm_env(monkeypatch, enabled=True, provider="mock")

    class FailingProvider:
        provider_name = "failing"

        def polish_summary(self, request: LlmSummaryRequest):
            raise RuntimeError("provider failed")

    monkeypatch.setattr(
        "app.services.summaries.get_summary_llm_provider",
        lambda settings: FailingProvider(),
    )
    event = event_factory()
    session = _create_session_with_results(db_session, event)

    response = client.get(f"/api/sessions/{session.id}/summary")

    assert response.status_code == 200
    assert response.json()["summary"]["generationMode"] == "fallback"
