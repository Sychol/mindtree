from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.card import MindCard
from app.models.enums import ContentOrigin, KeywordJobStatus, SessionStatus
from app.models.keyword import Keyword, KeywordJob
from app.models.reply import Reply
from app.models.risk import RiskFlag
from app.repositories.keyword_jobs import KeywordJobRepository
from app.services.keywords.job_runner import process_next_jobs
from app.services.keywords.types import KeywordCandidate
from tests.admin_test_utils import create_admin
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


def _set_openai_keyword_env(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_KEYWORD_MODEL", "gpt-4.1-nano-test")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()


class _FakeOpenAICompletions:
    def __init__(self, *, content: str | None = None, error: Exception | None = None) -> None:
        self.call_count = 0
        self._content = content or (
            '{"keywords":[{"text":"rest","normalized":"rest",'
            '"category":"recovery","weight":1.0}]}'
        )
        self._error = error

    def create(self, **kwargs):
        del kwargs
        self.call_count += 1
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._content),
                )
            ]
        )


class _FakeOpenAIClient:
    def __init__(self, completions: _FakeOpenAICompletions) -> None:
        self.chat = SimpleNamespace(completions=completions)


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


def test_openai_success_saves_llm_keywords_and_provider(monkeypatch, db_session: Session, event_factory) -> None:
    _set_openai_keyword_env(monkeypatch)
    completions = _FakeOpenAICompletions()
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="participant card")
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    assert summary.succeeded_count == 1
    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.provider == "openai:gpt-4.1-nano-test"
    assert stored_job.fallback_used is False
    assert stored_job.output_snapshot["extraction_method"] == "llm"
    assert {keyword.extraction_method for keyword in keywords} == {"llm"}
    assert {keyword.origin for keyword in keywords} == {ContentOrigin.PARTICIPANT.value}


def test_openai_success_keeps_admin_manual_origin(monkeypatch, db_session: Session, event_factory) -> None:
    _set_openai_keyword_env(monkeypatch)
    completions = _FakeOpenAICompletions()
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    event = event_factory()
    admin = create_admin(db_session)
    card = MindCard(
        event_id=event.id,
        session_id=None,
        prompt_type="to_colleague",
        content_raw="admin card",
        safety_status="safe",
        public_status="public",
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag="ops",
        created_by_admin_id=admin.id,
    )
    db_session.add(card)
    db_session.flush()
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    assert summary.succeeded_count == 1
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert keywords
    assert {keyword.origin for keyword in keywords} == {ContentOrigin.ADMIN_MANUAL.value}
    assert {keyword.origin_tag for keyword in keywords} == {"ops"}
    assert {keyword.created_by_admin_id for keyword in keywords} == {admin.id}


def test_openai_failure_saves_fallback_keywords(monkeypatch, db_session: Session, event_factory) -> None:
    _set_openai_keyword_env(monkeypatch)
    completions = _FakeOpenAICompletions(error=RuntimeError("api error"))
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    monkeypatch.setattr(
        "app.services.keywords.job_runner.extract_fallback_keywords",
        lambda *args, **kwargs: [
            KeywordCandidate(
                text="fallback",
                normalized="fallback",
                category="recovery",
                weight=1.0,
                extraction_method="fallback",
            )
        ],
    )
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="媛?댁씠 ?듬떟?댁슂")
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    assert summary.succeeded_count == 1
    assert summary.fallback_used_count == 1
    db_session.expire_all()
    stored_job = db_session.get(KeywordJob, job.id)
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert stored_job is not None
    assert stored_job.provider == "openai:gpt-4.1-nano-test"
    assert stored_job.fallback_used is True
    assert stored_job.output_snapshot["fallback_reason"] == "LLM keyword extraction failed"
    assert {keyword.extraction_method for keyword in keywords} == {"fallback"}


def test_excluded_source_does_not_call_openai(monkeypatch, db_session: Session, event_factory) -> None:
    _set_openai_keyword_env(monkeypatch)
    completions = _FakeOpenAICompletions()
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeOpenAIClient(completions),
    )
    event = event_factory()
    session = _session(db_session, event)
    card = _card(
        db_session,
        event,
        session,
        content="excluded card",
        safety_status="exclude",
        public_status="excluded",
    )
    job = _job(db_session, card, "mind_card")
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    stored_job = db_session.get(KeywordJob, job.id)
    assert summary.excluded_count == 1
    assert completions.call_count == 0
    assert stored_job is not None
    assert stored_job.provider == "policy"
    assert stored_job.output_snapshot["excluded"] is True


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
