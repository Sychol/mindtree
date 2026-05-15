from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.keyword import Keyword, KeywordJob
from app.repositories.keyword_jobs import KeywordJobRepository
from app.services.keywords.job_runner import process_next_jobs
from tests.test_cards_api import _card, _session


@pytest.fixture(autouse=True)
def keyword_settings(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "false")
    monkeypatch.setenv("LLM_PROVIDER", "disabled")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_phase07_keyword_job_snapshot_does_not_store_sensitive_flow_values(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)

    response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "to_now_me", "content": "오늘은 조금 쉬어가도 괜찮다."},
    )

    assert response.status_code == 200
    job = db_session.execute(select(KeywordJob).where(KeywordJob.event_id == event.id)).scalar_one()
    snapshot = job.input_snapshot
    assert "session_id" not in snapshot
    assert "resumeToken" not in snapshot
    assert "completionCode" not in snapshot
    assert "content_raw" not in snapshot
    assert "content_preview" not in snapshot
    assert snapshot["content_length"] > 0


def test_personal_info_is_not_saved_as_keyword(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(
        db_session,
        event,
        session,
        content="연락은 010-1234-5678 이고 hello@example.com 입니다. 괜찮아요 쉬어가도 돼요.",
    )
    job = KeywordJobRepository(db_session).create_pending_job(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        input_snapshot={"source_type": "mind_card", "source_id": str(card.id), "content_length": len(card.content_raw)},
    )
    db_session.commit()

    process_next_jobs(db_session, limit=5)

    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    combined = " ".join(f"{keyword.keyword_text} {keyword.normalized_keyword}" for keyword in keywords)
    assert "010-1234-5678" not in combined
    assert "hello@example.com" not in combined
    assert {keyword.normalized_keyword for keyword in keywords} & {"괜찮아", "쉼"}


def test_crisis_expression_is_not_saved_as_keyword(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="자살이라는 말은 빼고 숨을 천천히 쉬어봐요")
    job = KeywordJobRepository(db_session).create_pending_job(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        input_snapshot={"source_type": "mind_card", "source_id": str(card.id), "content_length": len(card.content_raw)},
    )
    db_session.commit()

    process_next_jobs(db_session, limit=5)

    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert "자살" not in {keyword.normalized_keyword for keyword in keywords}


def test_error_message_does_not_include_raw_content(db_session: Session, event_factory) -> None:
    event = event_factory()
    raw_content = "이 원문은 error_message에 들어가면 안 됩니다"
    job = KeywordJobRepository(db_session).create_pending_job(
        event_id=event.id,
        source_type="summary",
        source_id=uuid4(),
        input_snapshot={"source_type": "summary", "source_id": str(uuid4()), "content_length": len(raw_content)},
    )
    db_session.commit()

    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    assert stored_job is not None
    assert stored_job.error_message == "unsupported source type"
    assert raw_content not in stored_job.error_message
