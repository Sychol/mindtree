from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, SessionStatus
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _session


def test_admin_completion_code_lookup_and_redeem(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event, status=SessionStatus.COMPLETED.value)
    completion_code = CompletionCode(
        event_id=event.id,
        session_id=session.id,
        code="TREE-REWARD1",
        status=CompletionCodeStatus.ISSUED.value,
    )
    db_session.add(completion_code)
    db_session.commit()
    db_session.refresh(completion_code)

    lookup = client.get(
        f"/api/admin/events/{event.slug}/completion-codes/{completion_code.code}",
        headers=auth_headers(admin),
    )
    assert lookup.status_code == 200
    assert lookup.json()["completionCode"]["status"] == "issued"
    assert "riskFlags" not in lookup.text

    redeem = client.post(
        f"/api/admin/events/{event.slug}/completion-codes/{completion_code.code}/redeem",
        json={"notes": "field reward"},
        headers=auth_headers(admin),
    )
    assert redeem.status_code == 200
    assert redeem.json()["completionCode"]["status"] == "redeemed"

    db_session.expire_all()
    stored = db_session.get(CompletionCode, completion_code.id)
    assert stored.status == "redeemed"
    assert stored.redeemed_at is not None
    assert stored.redeemed_by == admin.id
    assert stored.notes == "field reward"
    audit = db_session.execute(
        select(AdminAuditLog).where(AdminAuditLog.target_id == completion_code.id)
    ).scalar_one()
    assert audit.action == "completion_code.redeem"


def test_admin_completion_code_rejects_missing_duplicate_and_unauthenticated(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event, status=SessionStatus.COMPLETED.value)
    completion_code = CompletionCode(
        event_id=event.id,
        session_id=session.id,
        code="TREE-REWARD2",
        status=CompletionCodeStatus.REDEEMED.value,
    )
    db_session.add(completion_code)
    db_session.commit()

    missing = client.get(
        f"/api/admin/events/{event.slug}/completion-codes/MISSING",
        headers=auth_headers(admin),
    )
    duplicate = client.post(
        f"/api/admin/events/{event.slug}/completion-codes/{completion_code.code}/redeem",
        json={"notes": "again"},
        headers=auth_headers(admin),
    )
    unauthenticated = client.get(
        f"/api/admin/events/{event.slug}/completion-codes/{completion_code.code}"
    )

    assert missing.status_code == 404
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "COMPLETION_CODE_ALREADY_REDEEMED"
    assert unauthenticated.status_code == 401
