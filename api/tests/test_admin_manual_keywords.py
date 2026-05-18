from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.models.enums import ContentOrigin, KeywordExtractionMethod, KeywordSourceType
from app.models.keyword import Keyword
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _card, _session


def test_manual_keyword_create_requires_admin(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "쉼", "category": "recovery"},
    )

    assert response.status_code == 401


def test_admin_can_create_manual_keyword_with_defaults_and_audit(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    response = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "쉼", "category": "recovery", "reason": "seed"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    payload = response.json()
    keyword_payload = payload["keyword"]
    assert payload["auditLogCreated"] is True
    assert keyword_payload["keywordText"] == "쉼"
    assert keyword_payload["normalizedKeyword"] == "쉼"
    assert keyword_payload["category"] == "recovery"
    assert keyword_payload["weight"] == 3.0
    assert keyword_payload["status"] == "active"
    assert keyword_payload["extractionMethod"] == KeywordExtractionMethod.ADMIN.value
    assert keyword_payload["sourceType"] == KeywordSourceType.ADMIN_MANUAL.value
    assert keyword_payload["sourceId"] is None
    assert keyword_payload["origin"] == ContentOrigin.ADMIN_MANUAL.value
    assert keyword_payload["originTag"] == "운영자추가"
    assert keyword_payload["createdByAdminId"] == str(admin.id)

    db_session.expire_all()
    stored = db_session.get(Keyword, keyword_payload["id"])
    assert stored is not None
    assert stored.origin == ContentOrigin.ADMIN_MANUAL.value
    assert stored.source_id is None
    assert stored.created_by_admin_id == admin.id

    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == stored.id)
    ).scalar_one()
    assert audit.action == "manual_keyword.create"
    assert audit.target_type == "keyword"
    assert audit.reason == "seed"
    assert audit.after_value["origin"] == ContentOrigin.ADMIN_MANUAL.value


def test_manual_keyword_create_accepts_explicit_fields(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    response = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={
            "keywordText": "쉬어가기",
            "normalizedKeyword": "쉼",
            "category": "recovery",
            "weight": 5,
            "status": "hidden",
            "originTag": "운영자추가",
            "reason": "초기 운영 seed",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    keyword_payload = response.json()["keyword"]
    assert keyword_payload["normalizedKeyword"] == "쉼"
    assert keyword_payload["weight"] == 5.0
    assert keyword_payload["status"] == "hidden"
    assert keyword_payload["originTag"] == "운영자추가"


def test_manual_keyword_create_validation_errors(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    headers = auth_headers(admin)

    invalid_category = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "쉼", "category": "unknown"},
        headers=headers,
    )
    invalid_weight = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "쉼", "category": "recovery", "weight": 99},
        headers=headers,
    )
    personal_info = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "010-1234-5678", "category": "neutral"},
        headers=headers,
    )

    assert invalid_category.status_code == 400
    assert invalid_weight.status_code == 400
    assert personal_info.status_code == 400


def test_manual_keyword_status_transitions_and_audit(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    headers = auth_headers(admin)
    created = client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "쉼", "category": "recovery"},
        headers=headers,
    )
    keyword_id = created.json()["keyword"]["id"]

    for next_status in ["hidden", "excluded", "active"]:
        response = client.patch(
            f"/api/admin/keywords/{keyword_id}/manual-status",
            json={"status": next_status, "reason": f"set {next_status}"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["keyword"]["status"] == next_status
        assert response.json()["keyword"]["origin"] == ContentOrigin.ADMIN_MANUAL.value

    db_session.expire_all()
    stored = db_session.get(Keyword, keyword_id)
    assert stored is not None
    assert stored.status == "active"
    audits = db_session.execute(
        select(AdminAuditLog)
        .where(AdminAuditLog.target_id == stored.id)
        .where(AdminAuditLog.action == "manual_keyword.update_status")
        .order_by(AdminAuditLog.created_at.asc())
    ).scalars().all()
    assert len(audits) == 3
    assert audits[-1].before_value["status"] == "excluded"
    assert audits[-1].after_value["status"] == "active"


def test_participant_keyword_cannot_use_manual_status_endpoint(
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
        keyword_text="쉼",
        normalized_keyword="쉼",
        category="recovery",
        weight=Decimal("2"),
        status="active",
        extraction_method="fallback",
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)

    response = client.patch(
        f"/api/admin/keywords/{keyword.id}/manual-status",
        json={"status": "hidden", "reason": "not manual"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 400


def test_keyword_list_origin_filters(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event)
    card = _card(db_session, event, session)
    participant_keyword = Keyword(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        keyword_text="긴장",
        normalized_keyword="긴장",
        category="mind_signal",
        weight=Decimal("4"),
        status="active",
        extraction_method="fallback",
    )
    db_session.add(participant_keyword)
    db_session.commit()

    client.post(
        f"/api/admin/events/{event.slug}/keywords/manual",
        json={"keywordText": "쉼", "category": "recovery"},
        headers=auth_headers(admin),
    )

    manual_listing = client.get(
        f"/api/admin/events/{event.slug}/keywords",
        params={"status": "all", "origin": "admin_manual"},
        headers=auth_headers(admin),
    )
    participant_listing = client.get(
        f"/api/admin/events/{event.slug}/keywords",
        params={"status": "all", "origin": "participant"},
        headers=auth_headers(admin),
    )

    assert manual_listing.status_code == 200
    assert participant_listing.status_code == 200
    assert [item["origin"] for item in manual_listing.json()["items"]] == ["admin_manual"]
    assert [item["origin"] for item in participant_listing.json()["items"]] == ["participant"]
