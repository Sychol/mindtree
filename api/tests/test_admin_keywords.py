from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.models.keyword import Keyword, KeywordJob
from app.services.display_aggregate import build_display_snapshot
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _card, _session


def test_admin_keyword_list_update_and_tv_hidden_exclusion(
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
        weight=Decimal("3"),
        status="active",
        extraction_method="fallback",
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)

    listing = client.get(
        f"/api/admin/events/{event.slug}/keywords",
        params={"status": "active"},
        headers=auth_headers(admin),
    )
    assert listing.status_code == 200
    assert listing.json()["items"][0]["normalizedKeyword"] == "rest"

    response = client.patch(
        f"/api/admin/keywords/{keyword.id}",
        json={
            "normalizedKeyword": "recovery",
            "category": "recovery",
            "status": "hidden",
            "reason": "merge",
        },
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    db_session.expire_all()
    stored = db_session.get(Keyword, keyword.id)
    assert stored.normalized_keyword == "recovery"
    assert stored.category == "recovery"
    assert stored.status == "hidden"
    assert build_display_snapshot(db_session, event.slug).cloudKeywords == []
    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == keyword.id)
    ).scalar_one()
    assert audit.action == "keyword.hide"


def test_admin_keyword_job_list_and_retry(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event)
    card = _card(db_session, event, session)
    job = KeywordJob(
        event_id=event.id,
        source_type="mind_card",
        source_id=card.id,
        status="failed",
        attempts=2,
        max_attempts=2,
        provider="mock",
        fallback_used=True,
        error_message="timeout",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    listing = client.get(
        f"/api/admin/events/{event.slug}/keyword-jobs",
        params={"status": "failed"},
        headers=auth_headers(admin),
    )
    assert listing.status_code == 200
    assert listing.json()["items"][0]["status"] == "failed"

    response = client.post(
        f"/api/admin/keyword-jobs/{job.id}/retry",
        json={"reason": "retry"},
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == "pending"
    assert response.json()["job"]["attempts"] == 0
    db_session.expire_all()
    stored = db_session.get(KeywordJob, job.id)
    assert stored.status == "pending"
    assert stored.attempts == 0
    assert stored.error_message is None
    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == job.id)
    ).scalar_one()
    assert audit.action == "keyword_job.retry"
