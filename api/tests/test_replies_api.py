from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import CardSelection
from app.models.completion import CompletionCode
from app.models.enums import SessionStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.models.session import Session as EventSession
from tests.test_cards_api import _card, _session


def _select_card(
    db_session: Session,
    session: EventSession,
    selected_card_id,
) -> CardSelection:
    selection = CardSelection(
        event_id=session.event_id,
        session_id=session.id,
        selected_card_id=selected_card_id,
    )
    db_session.add(selection)
    db_session.commit()
    db_session.refresh(selection)
    return selection


def test_card_created_session_can_create_reply_and_complete(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    _card(db_session, event, session, content="내 카드")
    peer_card = _card(db_session, event, peer_session)
    _select_card(db_session, session, peer_card.id)

    response = client.post(
        f"/api/sessions/{session.id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "comfort",
            "content": "그 시간을 버틴 것만으로도 충분히 애쓰셨습니다.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reply"]["replyType"] == "comfort"
    assert data["reply"]["safetyStatus"] == "safe"
    assert data["keywordJob"]["status"] == "pending"
    assert data["completion"]["eligible"] is True
    assert data["completion"]["code"].startswith("TREE-")
    assert data["sessionStatus"] == "completed"

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session.id)
    assert stored_session is not None
    assert stored_session.status == "completed"
    assert stored_session.completed_at is not None


def test_reply_requires_selected_card(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_card = _card(db_session, event, peer_session)

    response = client.post(
        f"/api/sessions/{session.id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "comfort",
            "content": "괜찮습니다.",
        },
    )

    assert response.status_code == 400


def test_reply_target_must_match_selected_card(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    selected_card = _card(db_session, event, peer_session)
    other_card = _card(db_session, event, peer_session, content="다른 카드")
    _select_card(db_session, session, selected_card.id)

    response = client.post(
        f"/api/sessions/{session.id}/replies",
        json={
            "targetCardId": str(other_card.id),
            "replyType": "comfort",
            "content": "괜찮습니다.",
        },
    )

    assert response.status_code == 400


def test_reply_validates_type_and_content(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_card = _card(db_session, event, peer_session)
    _select_card(db_session, session, peer_card.id)

    bad_type = client.post(
        f"/api/sessions/{session.id}/replies",
        json={"targetCardId": str(peer_card.id), "replyType": "bad", "content": "괜찮습니다."},
    )
    empty = client.post(
        f"/api/sessions/{session.id}/replies",
        json={"targetCardId": str(peer_card.id), "replyType": "comfort", "content": "  "},
    )
    too_long = client.post(
        f"/api/sessions/{session.id}/replies",
        json={"targetCardId": str(peer_card.id), "replyType": "comfort", "content": "a" * 301},
    )

    assert bad_type.status_code == 400
    assert empty.status_code == 400
    assert too_long.status_code == 400


def test_reply_safety_status_controls_keyword_job(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    review_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    exclude_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_card = _card(db_session, event, peer_session)
    _card(db_session, event, review_session, content="내 카드 1")
    _card(db_session, event, exclude_session, content="내 카드 2")
    _select_card(db_session, review_session, peer_card.id)
    _select_card(db_session, exclude_session, peer_card.id)

    review = client.post(
        f"/api/sessions/{review_session.id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "empathy",
            "content": "연락은 hello@example.com 으로 하면 좋겠습니다.",
        },
    )
    excluded = client.post(
        f"/api/sessions/{exclude_session.id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "comfort",
            "content": "자살하고 싶다는 말을 들어도 혼자가 아닙니다.",
        },
    )

    assert review.status_code == 200
    assert review.json()["reply"]["publicStatus"] == "pending"
    assert review.json()["keywordJob"]["status"] == "pending"
    assert excluded.status_code == 200
    assert excluded.json()["reply"]["publicStatus"] == "excluded"
    assert excluded.json()["keywordJob"] is None

    replies = db_session.execute(select(Reply).where(Reply.event_id == event.id)).scalars().all()
    assert len(replies) == 2
    jobs = db_session.execute(select(KeywordJob).where(KeywordJob.event_id == event.id)).scalars().all()
    assert len(jobs) == 1


def test_completion_code_is_created_once_on_duplicate_reply_calls(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    _card(db_session, event, session, content="내 카드")
    peer_card = _card(db_session, event, peer_session)
    _select_card(db_session, session, peer_card.id)

    payload = {
        "targetCardId": str(peer_card.id),
        "replyType": "small_coping",
        "content": "잠깐 물을 마시고 숨을 고르는 것도 도움이 됩니다.",
    }
    first = client.post(f"/api/sessions/{session.id}/replies", json=payload)
    second = client.post(f"/api/sessions/{session.id}/replies", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["completion"]["code"] == second.json()["completion"]["code"]
    codes = db_session.execute(
        select(CompletionCode).where(CompletionCode.session_id == session.id)
    ).scalars().all()
    assert len(codes) == 1
