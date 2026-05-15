from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import CardSelection
from app.models.enums import KeywordJobStatus, SessionStatus
from app.models.keyword import Keyword, KeywordJob
from tests.test_cards_api import _card, _session


def test_mind_card_save_creates_pending_keyword_job(
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
    job = db_session.execute(
        select(KeywordJob).where(KeywordJob.event_id == event.id)
    ).scalar_one()
    assert job.source_type == "mind_card"
    assert job.status == KeywordJobStatus.PENDING.value
    assert "session_id" not in job.input_snapshot
    assert job.input_snapshot["prompt_type"] == "to_now_me"


def test_reply_save_creates_pending_keyword_job_without_keywords(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    _card(db_session, event, session, content="내 카드")
    peer_card = _card(db_session, event, peer_session)
    db_session.add(
        CardSelection(
            event_id=event.id,
            session_id=session.id,
            selected_card_id=peer_card.id,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session.id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "comfort",
            "content": "그 시간을 버틴 것만으로도 충분합니다.",
        },
    )

    assert response.status_code == 200
    jobs = db_session.execute(select(KeywordJob).where(KeywordJob.event_id == event.id)).scalars().all()
    assert len(jobs) == 1
    assert jobs[0].source_type == "reply"
    assert jobs[0].status == KeywordJobStatus.PENDING.value
    assert "session_id" not in jobs[0].input_snapshot
    keywords = db_session.execute(select(Keyword).where(Keyword.event_id == event.id)).scalars().all()
    assert keywords == []


def test_excluded_source_does_not_create_keyword_job(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)

    response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "to_now_me", "content": "자살하고 싶다는 생각이 들었다."},
    )

    assert response.status_code == 200
    assert response.json()["keywordJob"] is None
    jobs = db_session.execute(select(KeywordJob).where(KeywordJob.event_id == event.id)).scalars().all()
    assert jobs == []
