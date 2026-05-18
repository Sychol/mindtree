from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.config import get_settings
from app.models.enums import ContentOrigin, KeywordSourceType
from app.models.keyword import Keyword, KeywordJob
from app.repositories.keyword_jobs import KeywordJobRepository
from app.services.keywords.job_runner import process_next_jobs
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _card, _session


def test_manual_card_and_reply_create_keyword_jobs(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    card_response = client.post(
        f"/api/admin/events/{event.slug}/manual-cards",
        json={"promptType": "to_colleague", "content": "manual card", "createKeywordJob": True},
        headers=auth_headers(admin),
    )
    reply_response = client.post(
        f"/api/admin/events/{event.slug}/manual-replies",
        json={"replyType": "comfort", "content": "manual reply", "createKeywordJob": True},
        headers=auth_headers(admin),
    )

    assert card_response.status_code == 200
    assert reply_response.status_code == 200
    jobs = db_session.execute(
        select(KeywordJob).where(KeywordJob.event_id == event.id).order_by(KeywordJob.created_at)
    ).scalars().all()
    assert [job.source_type for job in jobs] == [
        KeywordSourceType.MIND_CARD.value,
        KeywordSourceType.REPLY.value,
    ]


def test_keyword_worker_propagates_manual_source_origin_and_handles_null_session(
    client: TestClient,
    db_session: Session,
    event_factory,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    event = event_factory()
    admin = create_admin(db_session)

    created = client.post(
        f"/api/admin/events/{event.slug}/manual-cards",
        json={
            "promptType": "to_colleague",
            "content": "manual card for keyword",
            "originTag": "ops",
            "createKeywordJob": True,
        },
        headers=auth_headers(admin),
    )
    assert created.status_code == 200
    job_id = UUID(created.json()["keywordJob"]["id"])

    summary = process_next_jobs(db_session, limit=5)

    assert summary.succeeded_count == 1
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job_id)).scalars().all()
    assert keywords
    assert {keyword.origin for keyword in keywords} == {ContentOrigin.ADMIN_MANUAL.value}
    assert {keyword.origin_tag for keyword in keywords} == {"ops"}
    assert {keyword.created_by_admin_id for keyword in keywords} == {admin.id}

    get_settings.cache_clear()


def test_keyword_worker_keeps_participant_source_origin(
    db_session: Session,
    event_factory,
    monkeypatch,
) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("KEYWORD_FALLBACK_ENABLED", "true")
    get_settings.cache_clear()
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="participant card")
    job = KeywordJobRepository(db_session).create_pending_job(
        event_id=event.id,
        source_type=KeywordSourceType.MIND_CARD.value,
        source_id=card.id,
        input_snapshot={"source_type": "mind_card", "source_id": str(card.id)},
    )
    db_session.commit()

    summary = process_next_jobs(db_session, limit=5)

    assert summary.succeeded_count == 1
    keywords = db_session.execute(select(Keyword).where(Keyword.job_id == job.id)).scalars().all()
    assert keywords
    assert {keyword.origin for keyword in keywords} == {ContentOrigin.PARTICIPANT.value}
    assert {keyword.origin_tag for keyword in keywords} == {None}
    assert {keyword.created_by_admin_id for keyword in keywords} == {None}

    get_settings.cache_clear()
