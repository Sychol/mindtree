from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.card import MindCard
from app.models.enums import KeywordJobStatus, SessionStatus
from app.models.keyword import Keyword, KeywordJob
from app.models.reply import Reply
from app.models.risk import RiskFlag
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


def _job(db_session: Session, source: MindCard | Reply, source_type: str) -> KeywordJob:
    return KeywordJobRepository(db_session).create_pending_job(
        event_id=source.event_id,
        source_type=source_type,
        source_id=source.id,
        input_snapshot={
            "source_type": source_type,
            "source_id": str(source.id),
            "content_length": len(source.content_raw),
        },
    )


def test_process_pending_mind_card_job_succeeds_with_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="가슴이 답답해요")
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    assert summary.claimed_count == 1
    assert summary.succeeded_count == 1
    assert summary.created_keyword_count >= 1
    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.status == KeywordJobStatus.SUCCEEDED.value
    assert stored_job.fallback_used is True
    assert {keyword.normalized_keyword for keyword in keywords} & {"답답함", "긴장"}


def test_process_pending_reply_job_succeeds_with_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_card = _card(db_session, event, peer_session)
    reply = Reply(
        event_id=event.id,
        session_id=session.id,
        target_card_id=peer_card.id,
        reply_type="comfort",
        content_raw="괜찮아요 쉬어가도 돼요",
        safety_status="safe",
        public_status="public",
    )
    db_session.add(reply)
    db_session.flush()
    job = _job(db_session, reply, "reply")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    assert summary.claimed_count == 1
    assert summary.succeeded_count == 1
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert {keyword.normalized_keyword for keyword in keywords} & {"괜찮아", "쉼"}


def test_review_or_pending_source_is_succeeded_without_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(
        db_session,
        event,
        session,
        content="검수 대기 문장",
        safety_status="review",
        public_status="pending",
    )
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    assert summary.excluded_count == 1
    assert stored_job is not None
    assert stored_job.status == KeywordJobStatus.SUCCEEDED.value
    assert stored_job.output_snapshot["excluded"] is True
    assert stored_job.output_snapshot["excluded_reason"] == "source_not_public"
    assert db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all() == []


def test_excluded_source_is_succeeded_without_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(
        db_session,
        event,
        session,
        content="제외 문장",
        safety_status="exclude",
        public_status="excluded",
    )
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    stored_job = db_session.get(KeywordJob, job.id)
    assert summary.excluded_count == 1
    assert stored_job is not None
    assert stored_job.output_snapshot["excluded_reason"] == "source_excluded"
    assert db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all() == []


def test_public_restricted_source_is_succeeded_without_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="숨을 천천히 쉬어봐요")
    risk_flag = db_session.execute(select(RiskFlag).where(RiskFlag.session_id == session.id)).scalar_one()
    risk_flag.public_restriction = True
    db_session.add(risk_flag)
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    stored_job = db_session.get(KeywordJob, job.id)
    assert summary.excluded_count == 1
    assert stored_job is not None
    assert stored_job.output_snapshot["excluded_reason"] == "source_public_restricted"
    assert db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all() == []


def test_same_job_reprocessing_replaces_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="잠이 안 와요")
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    process_next_jobs(db_session, limit=5)
    stored_job = db_session.get(KeywordJob, job.id)
    assert stored_job is not None
    stored_job.status = KeywordJobStatus.PENDING.value
    stored_job.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.add(stored_job)
    db_session.commit()

    process_next_jobs(db_session, limit=5)

    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    normalized = [keyword.normalized_keyword for keyword in keywords]
    assert len(normalized) == len(set(normalized))


def test_fallback_failure_moves_to_retry_wait_then_failed(monkeypatch, db_session: Session, event_factory) -> None:
    def failing_fallback(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.services.keywords.job_runner.extract_fallback_keywords", failing_fallback)
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="잠이 안 와요")
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    process_next_jobs(db_session, limit=5)
    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    assert stored_job is not None
    assert stored_job.status == KeywordJobStatus.RETRY_WAIT.value

    stored_job.next_run_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.add(stored_job)
    db_session.commit()
    process_next_jobs(db_session, limit=5)

    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    assert stored_job is not None
    assert stored_job.status == KeywordJobStatus.FAILED.value
    assert stored_job.error_message == "fallback keyword extraction failed"
