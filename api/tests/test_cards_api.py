from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import CardSelection, MindCard
from app.models.consent import ConsentLog
from app.models.enums import KeywordStatus, SessionStatus
from app.models.event import Event
from app.models.keyword import Keyword, KeywordJob
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
    assert stored_session.last_step == "cards/new"


def test_session_can_create_up_to_three_cards_and_fourth_fails(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)

    for index in range(3):
        response = client.post(
            f"/api/sessions/{session.id}/cards",
            json={
                "promptType": "stress_memory",
                "content": f"마음에 남은 장면 {index + 1}을 짧게 적었습니다.",
            },
        )
        assert response.status_code == 200
        assert response.json()["sessionStatus"] == "card_created"

    fourth = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "네 번째 카드는 저장되지 않아야 합니다."},
    )

    assert fourth.status_code == 400
    assert fourth.json()["error"]["code"] == "BAD_REQUEST"
    assert fourth.json()["error"]["message"] == "마음카드는 최대 3개까지 작성할 수 있습니다."
    stored_cards = db_session.execute(
        select(MindCard).where(MindCard.session_id == session.id)
    ).scalars().all()
    assert len(stored_cards) == 3


def test_event_setting_limits_session_card_count(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory(settings={"maxMindCardsPerSession": 2})
    session = _session(db_session, event)

    first = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "첫 번째 카드입니다."},
    )
    second = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "두 번째 카드입니다."},
    )
    third = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "세 번째 카드는 제한됩니다."},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 400
    assert third.json()["error"]["message"] == "마음카드는 최대 2개까지 작성할 수 있습니다."


def test_event_setting_card_limit_is_capped_at_three(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory(settings={"maxMindCardsPerSession": 5})
    session = _session(db_session, event)

    for index in range(3):
        response = client.post(
            f"/api/sessions/{session.id}/cards",
            json={"promptType": "stress_memory", "content": f"{index + 1}번째 카드입니다."},
        )
        assert response.status_code == 200

    response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "네 번째 카드는 제한됩니다."},
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "마음카드는 최대 3개까지 작성할 수 있습니다."


def test_list_my_cards_returns_created_cards(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)

    client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "마음에 남은 상황을 적었습니다."},
    )
    client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "to_now_me", "content": "지금의 나에게 건네는 말입니다."},
    )

    response = client.get(f"/api/sessions/{session.id}/cards")

    assert response.status_code == 200
    data = response.json()
    assert len(data["cards"]) == 2
    assert {card["promptType"] for card in data["cards"]} == {"stress_memory", "to_now_me"}
    assert all(card["content"] for card in data["cards"])


def test_update_my_card_reapplies_safety_and_keeps_flow(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    create_response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "처음 적은 카드입니다."},
    )
    card_id = create_response.json()["card"]["id"]

    update_response = client.patch(
        f"/api/sessions/{session.id}/cards/{card_id}",
        json={"promptType": "to_now_me", "content": "지금은 잠시 숨을 고르고 싶습니다."},
    )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["card"]["promptType"] == "to_now_me"
    assert data["card"]["content"] == "지금은 잠시 숨을 고르고 싶습니다."
    assert data["card"]["safetyStatus"] == "safe"
    assert data["card"]["publicStatus"] == "public"
    assert data["sessionStatus"] == "card_created"

    list_response = client.get(f"/api/sessions/{session.id}/cards")
    assert list_response.json()["cards"][0]["content"] == "지금은 잠시 숨을 고르고 싶습니다."


def test_update_my_card_hides_existing_keywords_and_creates_new_job_when_needed(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    create_response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "처음 적은 카드입니다."},
    )
    card_id = create_response.json()["card"]["id"]
    first_job_id = create_response.json()["keywordJob"]["id"]
    first_job = db_session.get(KeywordJob, first_job_id)
    assert first_job is not None
    first_job.status = "succeeded"
    db_session.add(
        Keyword(
            event_id=event.id,
            source_type="mind_card",
            source_id=first_job.source_id,
            keyword_text="처음",
            normalized_keyword="처음",
            category="mind_signal",
            job_id=first_job.id,
        )
    )
    db_session.commit()

    update_response = client.patch(
        f"/api/sessions/{session.id}/cards/{card_id}",
        json={"promptType": "stress_memory", "content": "수정한 카드입니다."},
    )

    assert update_response.status_code == 200
    assert update_response.json()["keywordJob"]["id"] != first_job_id
    keywords = db_session.execute(select(Keyword).where(Keyword.source_id == first_job.source_id)).scalars().all()
    assert keywords[0].status == KeywordStatus.HIDDEN.value


def test_delete_my_card_removes_card_and_relocks_next_step(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    create_response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "삭제할 카드입니다."},
    )
    card_id = create_response.json()["card"]["id"]

    delete_response = client.delete(f"/api/sessions/{session.id}/cards/{card_id}")

    assert delete_response.status_code == 200
    assert delete_response.json()["deletedCardId"] == card_id
    assert delete_response.json()["sessionStatus"] == "summary_viewed"
    assert client.get(f"/api/sessions/{session.id}/cards").json()["cards"] == []

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session.id)
    assert stored_session is not None
    assert stored_session.status == "summary_viewed"
    assert stored_session.last_step == "cards/new"


def test_update_or_delete_card_after_selecting_peer_card_fails(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    own_response = client.post(
        f"/api/sessions/{session.id}/cards",
        json={"promptType": "stress_memory", "content": "내 카드입니다."},
    )
    peer_card = _card(db_session, event, peer_session, content="선택 가능한 카드입니다.")
    select_response = client.post(
        f"/api/sessions/{session.id}/selected-card",
        json={"selectedCardId": str(peer_card.id)},
    )
    assert select_response.status_code == 200

    card_id = own_response.json()["card"]["id"]
    update_response = client.patch(
        f"/api/sessions/{session.id}/cards/{card_id}",
        json={"promptType": "stress_memory", "content": "수정 시도입니다."},
    )
    delete_response = client.delete(f"/api/sessions/{session.id}/cards/{card_id}")

    assert update_response.status_code == 409
    assert delete_response.status_code == 409


def test_card_selected_by_another_session_cannot_be_deleted(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    owner_session = _session(db_session, event)
    selector_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    create_response = client.post(
        f"/api/sessions/{owner_session.id}/cards",
        json={"promptType": "stress_memory", "content": "다른 참여자가 볼 카드입니다."},
    )
    card_id = create_response.json()["card"]["id"]
    select_response = client.post(
        f"/api/sessions/{selector_session.id}/selected-card",
        json={"selectedCardId": card_id},
    )
    assert select_response.status_code == 200

    delete_response = client.delete(f"/api/sessions/{owner_session.id}/cards/{card_id}")

    assert delete_response.status_code == 400


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
