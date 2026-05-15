from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import CardSelection, MindCard
from app.models.consent import ConsentLog
from app.models.enums import SessionStatus
from app.models.event import Event
from app.models.keyword import KeywordJob
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.models.summary import Summary


def _session(
    db_session: Session,
    event: Event,
    *,
    status: str = SessionStatus.SUMMARY_VIEWED.value,
    with_completion_inputs: bool = True,
) -> EventSession:
    session = EventSession(
        event_id=event.id,
        anonymous_key_hash=f"anon-{uuid4()}",
        resume_token_hash=f"resume-{uuid4()}",
        status=status,
        last_step="cards/new",
        client_meta={},
    )
    db_session.add(session)
    db_session.flush()

    if with_completion_inputs:
        db_session.add(
            ConsentLog(
                event_id=event.id,
                session_id=session.id,
                consent_version="v1",
                accepted_items={"eventIsNotDiagnosis": True},
            )
        )
        for scale_code in ["phq9", "pcl5", "kmies", "kscs"]:
            db_session.add(
                ScaleScore(
                    event_id=event.id,
                    session_id=session.id,
                    scale_code=scale_code,
                    raw_score=Decimal("1"),
                    severity_level="low",
                    sub_scores={},
                    rule_version="test",
                )
            )
        db_session.add(
            RiskFlag(
                event_id=event.id,
                session_id=session.id,
                details={},
                rule_version="test",
            )
        )
        db_session.add(
            Summary(
                event_id=event.id,
                session_id=session.id,
                template_text="template",
                final_text="summary",
                generation_mode="template",
                viewed_at=datetime.now(timezone.utc),
            )
        )

    db_session.commit()
    db_session.refresh(session)
    return session


def _card(
    db_session: Session,
    event: Event,
    session: EventSession,
    *,
    content: str = "당신의 하루가 누군가에게 큰 힘이 됩니다.",
    safety_status: str = "safe",
    public_status: str = "public",
) -> MindCard:
    card = MindCard(
        event_id=event.id,
        session_id=session.id,
        prompt_type="to_colleague",
        content_raw=content,
        safety_status=safety_status,
        public_status=public_status,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


def test_summary_viewed_session_can_create_card(
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
    data = response.json()
    assert data["card"]["promptType"] == "to_now_me"
    assert data["card"]["safetyStatus"] == "safe"
    assert data["card"]["publicStatus"] == "public"
    assert data["keywordJob"]["status"] == "pending"
    assert data["sessionStatus"] == "card_created"

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session.id)
    assert stored_session is not None
    assert stored_session.status == "card_created"
    assert stored_session.last_step == "cards/select"


def test_questions_completed_session_cannot_create_card(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.QUESTIONS_COMPLETED.value)

    response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "to_now_me", "content": "오늘은 조금 쉬어가도 괜찮다."},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_SESSION_STATUS"


def test_create_card_validates_content_and_prompt_type(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)

    empty = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "to_now_me", "content": "   "},
    )
    too_long = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "to_now_me", "content": "a" * 301},
    )
    bad_type = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "unknown", "content": "오늘도 버텼다."},
    )

    assert empty.status_code == 400
    assert too_long.status_code == 400
    assert bad_type.status_code == 400


def test_create_card_creates_keyword_job_for_safe_or_review_only(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    safe_session = _session(db_session, event)
    review_session = _session(db_session, event)
    exclude_session = _session(db_session, event)

    safe = client.post(
        f"/api/sessions/{safe_session.id}/cards",
        json={"promptType": "to_now_me", "content": "오늘도 조용히 지나갔다."},
    )
    review = client.post(
        f"/api/sessions/{review_session.id}/cards",
        json={"promptType": "to_now_me", "content": "연락은 hello@example.com 으로 주세요."},
    )
    excluded = client.post(
        f"/api/sessions/{exclude_session.id}/cards",
        json={"promptType": "to_now_me", "content": "자살하고 싶다는 생각이 들었다."},
    )

    assert safe.status_code == 200
    assert safe.json()["keywordJob"]["status"] == "pending"
    assert review.status_code == 200
    assert review.json()["card"]["publicStatus"] == "pending"
    assert review.json()["keywordJob"]["status"] == "pending"
    assert excluded.status_code == 200
    assert excluded.json()["card"]["publicStatus"] == "excluded"
    assert excluded.json()["keywordJob"] is None

    jobs = db_session.execute(select(KeywordJob).where(KeywordJob.event_id == event.id)).scalars().all()
    assert len(jobs) == 2


def test_public_cards_exclude_self_and_only_return_safe_public_cards(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    my_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    review_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    _card(db_session, event, my_session, content="내 카드입니다.")
    peer_card = _card(db_session, event, peer_session, content="동료에게 보내는 안전한 문장.")
    _card(db_session, event, review_session, content="검수 대기 카드.", safety_status="review", public_status="pending")

    response = client.get(
        f"/api/events/{event.slug}/cards/public",
        params={"excludeSessionId": str(my_session.id), "limit": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["fallbackUsed"] is False
    assert [card["id"] for card in data["cards"]] == [str(peer_card.id)]


def test_public_cards_exclude_public_restricted_source(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    my_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    _card(db_session, event, peer_session)

    risk_flag = db_session.execute(
        select(RiskFlag).where(RiskFlag.session_id == peer_session.id)
    ).scalar_one()
    risk_flag.public_restriction = True
    db_session.add(risk_flag)
    db_session.commit()

    response = client.get(
        f"/api/events/{event.slug}/cards/public",
        params={"excludeSessionId": str(my_session.id), "limit": 10},
    )

    assert response.status_code == 200
    assert response.json()["cards"] == []
    assert response.json()["fallbackUsed"] is True


def test_public_cards_empty_state_uses_fallback_message(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)

    response = client.get(
        f"/api/events/{event.slug}/cards/public",
        params={"excludeSessionId": str(session.id), "limit": 10},
    )

    assert response.status_code == 200
    assert response.json()["fallbackUsed"] is True
    assert response.json()["message"]


def test_select_peer_card_success_and_upsert(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_card = _card(db_session, event, peer_session)

    response = client.post(
        f"/api/sessions/{session.id}/selected-card",
        json={"selectedCardId": str(peer_card.id)},
    )

    assert response.status_code == 200
    assert response.json()["selectedCardId"] == str(peer_card.id)
    selection = db_session.execute(
        select(CardSelection).where(CardSelection.session_id == session.id)
    ).scalar_one()
    assert selection.selected_card_id == peer_card.id


def test_select_self_or_non_public_card_fails(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    own_card = _card(db_session, event, session)
    pending_card = _card(
        db_session,
        event,
        peer_session,
        safety_status="review",
        public_status="pending",
    )

    self_response = client.post(
        f"/api/sessions/{session.id}/selected-card",
        json={"selectedCardId": str(own_card.id)},
    )
    pending_response = client.post(
        f"/api/sessions/{session.id}/selected-card",
        json={"selectedCardId": str(pending_card.id)},
    )

    assert self_response.status_code == 400
    assert pending_response.status_code == 400
