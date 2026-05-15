from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.models.card import MindCard
from app.models.keyword import Keyword
from app.models.reply import Reply
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _card, _session


def test_admin_card_review_list_and_publish_with_redaction(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event)
    card = _card(
        db_session,
        event,
        session,
        content="private card text",
        safety_status="review",
        public_status="pending",
    )

    listing = client.get(
        f"/api/admin/events/{event.slug}/cards",
        params={"status": "review"},
        headers=auth_headers(admin),
    )
    assert listing.status_code == 200
    assert listing.json()["items"][0]["contentRaw"] == "private card text"
    assert listing.json()["items"][0]["riskFlags"]["publicRestriction"] is False

    response = client.patch(
        f"/api/admin/cards/{card.id}/review",
        json={
            "safetyStatus": "safe",
            "publicStatus": "public",
            "contentRedacted": "public card text",
            "reason": "redacted",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["card"]["contentRedacted"] == "public card text"
    db_session.expire_all()
    stored = db_session.get(MindCard, card.id)
    assert stored.content_raw == "private card text"
    assert stored.content_redacted == "public card text"
    assert stored.reviewed_by == admin.id
    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == card.id)
    ).scalar_one()
    assert audit.action in {"card.publish", "card.edit"}


def test_admin_card_hidden_updates_source_keywords(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event)
    card = _card(db_session, event, session)
    keyword = Keyword(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        keyword_text="rest",
        normalized_keyword="rest",
        category="support",
        weight=1,
        status="active",
        extraction_method="fallback",
    )
    db_session.add(keyword)
    db_session.commit()

    response = client.patch(
        f"/api/admin/cards/{card.id}/review",
        json={
            "safetyStatus": "safe",
            "publicStatus": "hidden",
            "reason": "hide from display",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(Keyword, keyword.id).status == "hidden"


def test_admin_reply_review_list_and_hide(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    source_session = _session(db_session, event)
    reply_session = _session(db_session, event)
    card = _card(db_session, event, source_session)
    reply = Reply(
        event_id=event.id,
        session_id=reply_session.id,
        target_card_id=card.id,
        reply_type="comfort",
        content_raw="private reply",
        safety_status="review",
        public_status="pending",
    )
    db_session.add(reply)
    db_session.commit()
    db_session.refresh(reply)

    listing = client.get(
        f"/api/admin/events/{event.slug}/replies",
        params={"status": "review"},
        headers=auth_headers(admin),
    )
    assert listing.status_code == 200
    assert listing.json()["items"][0]["contentRaw"] == "private reply"

    response = client.patch(
        f"/api/admin/replies/{reply.id}/review",
        json={
            "safetyStatus": "safe",
            "publicStatus": "hidden",
            "reason": "hide reply",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    db_session.expire_all()
    stored = db_session.get(Reply, reply.id)
    assert stored.public_status == "hidden"
    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == reply.id)
    ).scalar_one()
    assert audit.action == "reply.hide"


def test_review_api_rejects_unauthenticated_requests(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session)

    listing = client.get(f"/api/admin/events/{event.slug}/cards")
    patch = client.patch(
        f"/api/admin/cards/{card.id}/review",
        json={"safetyStatus": "safe", "publicStatus": "public"},
    )

    assert listing.status_code == 401
    assert patch.status_code == 401
