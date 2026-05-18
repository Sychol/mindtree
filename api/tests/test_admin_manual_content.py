from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.audit import AdminAuditLog
from app.models.card import MindCard
from app.models.enums import ContentOrigin, PublicStatus, SafetyStatus
from app.models.keyword import Keyword, KeywordJob
from app.models.reply import Reply
from app.services.safety_filter import SafetyFilterResult
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _card, _session


def test_manual_card_create_requires_admin(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.post(
        f"/api/admin/events/{event.slug}/manual-cards",
        json={"promptType": "to_colleague", "content": "manual card"},
    )

    assert response.status_code == 401


def test_admin_can_create_manual_card_with_keyword_job_and_audit(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    response = client.post(
        f"/api/admin/events/{event.slug}/manual-cards",
        json={
            "promptType": "to_colleague",
            "content": "manual safe card",
            "originTag": "ops",
            "createKeywordJob": True,
            "reason": "seed",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["card"]["sessionId"] is None
    assert payload["card"]["origin"] == ContentOrigin.ADMIN_MANUAL.value
    assert payload["card"]["originTag"] == "ops"
    assert payload["card"]["createdByAdminId"] == str(admin.id)
    assert payload["keywordJob"]["status"] == "pending"

    stored = db_session.get(MindCard, payload["card"]["id"])
    assert stored.session_id is None
    assert stored.origin == ContentOrigin.ADMIN_MANUAL.value
    assert stored.created_by_admin_id == admin.id
    assert stored.reviewed_by == admin.id

    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == stored.id)
    ).scalar_one()
    assert audit.action == "manual_card.create"
    assert audit.target_type == "mind_card"
    assert audit.after_value["contentPreview"] == "manual safe card"


def test_manual_card_excluded_by_safety_filter_is_rejected(
    client: TestClient,
    db_session: Session,
    event_factory,
    monkeypatch,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    monkeypatch.setattr(
        "app.services.admin_manual_content.evaluate_safety",
        lambda _source_type, _content: SafetyFilterResult(
            safety_status=SafetyStatus.EXCLUDE.value,
            public_status=PublicStatus.EXCLUDED.value,
            moderation_reason="test_exclude",
            content_redacted=None,
            crisis_expression_detected=False,
            personal_info_detected=False,
        ),
    )

    response = client.post(
        f"/api/admin/events/{event.slug}/manual-cards",
        json={"promptType": "to_colleague", "content": "blocked"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 400


def test_manual_card_status_endpoint_rejects_participant_card_and_updates_manual_keywords(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    participant_session = _session(db_session, event)
    participant_card = _card(db_session, event, participant_session)

    rejected = client.patch(
        f"/api/admin/manual-cards/{participant_card.id}/status",
        json={"safetyStatus": "safe", "publicStatus": "hidden"},
        headers=auth_headers(admin),
    )
    assert rejected.status_code == 400

    created = client.post(
        f"/api/admin/events/{event.slug}/manual-cards",
        json={"promptType": "to_colleague", "content": "manual card", "createKeywordJob": False},
        headers=auth_headers(admin),
    )
    card_id = UUID(created.json()["card"]["id"])
    keyword = Keyword(
        event_id=event.id,
        source_type="mind_card",
        source_id=card_id,
        keyword_text="rest",
        normalized_keyword="rest",
        category="support",
        weight=1,
        status="active",
        extraction_method="fallback",
        origin=ContentOrigin.ADMIN_MANUAL.value,
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)

    hidden = client.patch(
        f"/api/admin/manual-cards/{card_id}/status",
        json={"safetyStatus": "safe", "publicStatus": "hidden", "reason": "hide"},
        headers=auth_headers(admin),
    )
    assert hidden.status_code == 200
    db_session.expire_all()
    assert db_session.get(Keyword, keyword.id).status == "hidden"

    restored = client.patch(
        f"/api/admin/manual-cards/{card_id}/status",
        json={"safetyStatus": "safe", "publicStatus": "public", "reason": "restore"},
        headers=auth_headers(admin),
    )
    assert restored.status_code == 200
    db_session.expire_all()
    assert db_session.get(Keyword, keyword.id).status == "active"

    excluded = client.patch(
        f"/api/admin/manual-cards/{card_id}/status",
        json={"safetyStatus": "exclude", "publicStatus": "excluded", "reason": "exclude"},
        headers=auth_headers(admin),
    )
    assert excluded.status_code == 200
    db_session.expire_all()
    assert db_session.get(Keyword, keyword.id).status == "excluded"
    actions = [
        row.action
        for row in db_session.execute(
            select(AdminAuditLog).where(AdminAuditLog.target_id == card_id).order_by(AdminAuditLog.created_at)
        ).scalars()
    ]
    assert "manual_card.update_status" in actions


def test_manual_reply_create_requires_admin(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.post(
        f"/api/admin/events/{event.slug}/manual-replies",
        json={"replyType": "comfort", "content": "manual reply"},
    )

    assert response.status_code == 401


def test_admin_can_create_manual_reply_without_target_with_keyword_job_and_audit(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    response = client.post(
        f"/api/admin/events/{event.slug}/manual-replies",
        json={
            "replyType": "comfort",
            "content": "manual safe reply",
            "targetCardId": None,
            "originTag": "ops",
            "createKeywordJob": True,
            "reason": "seed",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"]["sessionId"] is None
    assert payload["reply"]["targetCardId"] is None
    assert payload["reply"]["origin"] == ContentOrigin.ADMIN_MANUAL.value
    assert payload["reply"]["createdByAdminId"] == str(admin.id)
    assert payload["keywordJob"]["status"] == "pending"

    stored = db_session.get(Reply, payload["reply"]["id"])
    assert stored.session_id is None
    assert stored.target_card_id is None
    assert stored.created_by_admin_id == admin.id
    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == stored.id)
    ).scalar_one()
    assert audit.action == "manual_reply.create"


def test_manual_reply_target_card_must_be_safe_public(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event)
    pending_card = _card(
        db_session,
        event,
        session,
        safety_status="review",
        public_status="pending",
    )

    response = client.post(
        f"/api/admin/events/{event.slug}/manual-replies",
        json={
            "replyType": "comfort",
            "content": "manual reply",
            "targetCardId": str(pending_card.id),
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 400


def test_manual_reply_status_endpoint_rejects_participant_reply_and_updates_keywords(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    card_session = _session(db_session, event)
    reply_session = _session(db_session, event)
    card = _card(db_session, event, card_session)
    participant_reply = Reply(
        event_id=event.id,
        session_id=reply_session.id,
        target_card_id=card.id,
        reply_type="comfort",
        content_raw="participant reply",
        safety_status="safe",
        public_status="public",
    )
    db_session.add(participant_reply)
    db_session.commit()
    db_session.refresh(participant_reply)

    rejected = client.patch(
        f"/api/admin/manual-replies/{participant_reply.id}/status",
        json={"safetyStatus": "safe", "publicStatus": "hidden"},
        headers=auth_headers(admin),
    )
    assert rejected.status_code == 400

    created = client.post(
        f"/api/admin/events/{event.slug}/manual-replies",
        json={"replyType": "comfort", "content": "manual reply", "createKeywordJob": False},
        headers=auth_headers(admin),
    )
    reply_id = UUID(created.json()["reply"]["id"])
    keyword = Keyword(
        event_id=event.id,
        source_type="reply",
        source_id=reply_id,
        keyword_text="support",
        normalized_keyword="support",
        category="support",
        weight=1,
        status="active",
        extraction_method="fallback",
        origin=ContentOrigin.ADMIN_MANUAL.value,
    )
    db_session.add(keyword)
    db_session.commit()

    hidden = client.patch(
        f"/api/admin/manual-replies/{reply_id}/status",
        json={"safetyStatus": "safe", "publicStatus": "hidden", "reason": "hide"},
        headers=auth_headers(admin),
    )
    assert hidden.status_code == 200
    db_session.expire_all()
    assert db_session.get(Keyword, keyword.id).status == "hidden"

    excluded = client.patch(
        f"/api/admin/manual-replies/{reply_id}/status",
        json={"safetyStatus": "exclude", "publicStatus": "excluded", "reason": "exclude"},
        headers=auth_headers(admin),
    )
    assert excluded.status_code == 200
    db_session.expire_all()
    assert db_session.get(Keyword, keyword.id).status == "excluded"
    audits = db_session.execute(
        select(AdminAuditLog)
        .where(AdminAuditLog.target_id == reply_id, AdminAuditLog.action == "manual_reply.update_status")
    ).scalars().all()
    assert len(audits) == 2
    assert {audit.target_type for audit in audits} == {"reply"}
