from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, SessionStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.models.session import Session as EventSession
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _card, _session


def test_admin_dashboard_counts_operational_metrics(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    completed_session = _session(db_session, event, status=SessionStatus.COMPLETED.value)
    active_session = _session(db_session, event)
    card = _card(db_session, event, completed_session)
    review_card = MindCard(
        event_id=event.id,
        session_id=active_session.id,
        prompt_type="to_now_me",
        content_raw="needs review",
        safety_status="review",
        public_status="pending",
    )
    db_session.add(review_card)
    db_session.add(
        Reply(
            event_id=event.id,
            session_id=active_session.id,
            target_card_id=card.id,
            content_raw="reply",
            safety_status="review",
            public_status="pending",
        )
    )
    db_session.flush()
    db_session.add(
        KeywordJob(
            event_id=event.id,
            source_type="mind_card",
            source_id=card.id,
            status="pending",
        )
    )
    db_session.add(
        KeywordJob(
            event_id=event.id,
            source_type="mind_card",
            source_id=review_card.id,
            status="failed",
        )
    )
    db_session.add(
        CompletionCode(
            event_id=event.id,
            session_id=completed_session.id,
            code="TREE-ADMIN1",
            status=CompletionCodeStatus.REDEEMED.value,
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/admin/events/{event.slug}/dashboard",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    metrics = response.json()["metrics"]
    assert metrics["sessionCount"] == 2
    assert metrics["completedCount"] == 1
    assert metrics["cardCount"] == 2
    assert metrics["replyCount"] == 1
    assert metrics["reviewCount"] == 2
    assert metrics["keywordPendingCount"] == 1
    assert metrics["keywordFailedCount"] == 1
    assert metrics["completionIssuedCount"] == 1
    assert metrics["redeemedCount"] == 1


def test_admin_dashboard_requires_auth_and_event(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    unauthorized = client.get(f"/api/admin/events/{event.slug}/dashboard")
    missing = client.get(
        "/api/admin/events/missing-event/dashboard",
        headers=auth_headers(admin),
    )

    assert unauthorized.status_code == 401
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "EVENT_NOT_FOUND"
