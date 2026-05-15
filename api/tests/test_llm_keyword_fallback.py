import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.keyword import Keyword, KeywordJob
from app.repositories.keyword_jobs import KeywordJobRepository
from app.services.keywords.job_runner import process_next_jobs
from tests.test_cards_api import _card, _session


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _create_card_job(db_session: Session, event_factory, content: str = "괜찮아요 쉬어가도 돼요") -> KeywordJob:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content=content)
    job = KeywordJobRepository(db_session).create_pending_job(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        input_snapshot={
            "source_type": "mind_card",
            "source_id": str(card.id),
            "content_length": len(card.content_raw),
        },
    )
    db_session.commit()
    return job


def test_llm_disabled_uses_fallback(monkeypatch, db_session: Session, event_factory) -> None:
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    job = _create_card_job(db_session, event_factory)

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.fallback_used is True
    assert stored_job.provider == "disabled"
    assert {keyword.extraction_method for keyword in keywords} == {"fallback"}


def test_mock_llm_success_saves_llm_keywords(monkeypatch, db_session: Session, event_factory) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    job = _create_card_job(db_session, event_factory)

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.fallback_used is False
    assert stored_job.provider == "mock"
    assert {keyword.extraction_method for keyword in keywords} == {"llm"}


def test_mock_schema_failure_falls_back(monkeypatch, db_session: Session, event_factory) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock_invalid")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    job = _create_card_job(db_session, event_factory, content="잠이 안 와요")

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.fallback_used is True
    assert stored_job.output_snapshot["fallback_reason"] == "LLM schema parse failed"
    assert {keyword.extraction_method for keyword in keywords} == {"fallback"}


def test_mock_provider_failure_falls_back(monkeypatch, db_session: Session, event_factory) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock_failure")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    job = _create_card_job(db_session, event_factory, content="가슴이 답답해요")

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    assert stored_job is not None
    assert stored_job.fallback_used is True
    assert stored_job.output_snapshot["fallback_reason"] == "LLM keyword extraction failed"
