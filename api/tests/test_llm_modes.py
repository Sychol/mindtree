import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.keyword import Keyword, KeywordJob
from app.services.keywords.job_runner import process_next_jobs
from app.services.llm.base import LlmSummaryRequest
from app.services.llm.provider import get_summary_llm_provider
from tests.test_cards_api import _card, _session
from tests.test_llm_keyword_fallback import _create_card_job as _create_fallback_card_job


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _set_llm_mode(monkeypatch, *, enabled: bool, provider: str, fallback: bool = True) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true" if fallback else "false")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()


def _create_keyword_job(
    db_session: Session,
    event_factory,
    content: str = "\uad1c\ucc2e\uc544\uc694 \uc26c\uc5b4\uac00\ub3c4 \ub3fc\uc694",
) -> KeywordJob:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content=content)
    job = KeywordJob(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        status="pending",
        input_snapshot={
            "source_type": "mind_card",
            "source_id": str(card.id),
            "content_length": len(card.content_raw),
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_llm_disabled_summary_provider_returns_template(monkeypatch) -> None:
    _set_llm_mode(monkeypatch, enabled=False, provider="mock")
    provider = get_summary_llm_provider(get_settings())
    request = LlmSummaryRequest(
        template_text="Template summary",
        signals=["steady breath"],
        recommended_action="Take one small step.",
    )

    result = provider.polish_summary(request)

    assert provider.provider_name == "disabled"
    assert result.used is False
    assert result.text == "Template summary"


def test_llm_disabled_keyword_flow_uses_fallback(monkeypatch, db_session: Session, event_factory) -> None:
    _set_llm_mode(monkeypatch, enabled=False, provider="disabled", fallback=True)
    job = _create_fallback_card_job(db_session, event_factory)

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert stored_job.provider == "disabled"
    assert stored_job.fallback_used is True
    assert keywords
    assert {keyword.extraction_method for keyword in keywords} == {"fallback"}


def test_mock_keyword_provider_is_deterministic(monkeypatch, db_session: Session, event_factory) -> None:
    _set_llm_mode(monkeypatch, enabled=True, provider="mock", fallback=True)
    first_job = _create_keyword_job(db_session, event_factory, content="support and recovery")
    second_job = _create_keyword_job(db_session, event_factory, content="support and recovery")

    process_next_jobs(db_session, limit=5)

    first = [
        keyword.normalized_keyword
        for keyword in db_session.execute(
            select(Keyword).where(Keyword.job_id == first_job.id).order_by(Keyword.normalized_keyword)
        ).scalars()
    ]
    second = [
        keyword.normalized_keyword
        for keyword in db_session.execute(
            select(Keyword).where(Keyword.job_id == second_job.id).order_by(Keyword.normalized_keyword)
        ).scalars()
    ]
    assert first
    assert first == second


def test_llm_schema_failure_falls_back_without_external_api(monkeypatch, db_session: Session, event_factory) -> None:
    _set_llm_mode(monkeypatch, enabled=True, provider="mock_invalid", fallback=True)
    job = _create_keyword_job(db_session, event_factory, content="steady small step")

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert stored_job.fallback_used is True
    assert stored_job.output_snapshot["fallback_reason"] == "LLM schema parse failed"
