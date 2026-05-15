from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from tests.admin_test_utils import auth_headers, create_admin


def test_admin_audit_log_list_and_filters(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    db_session.add(
        AdminAuditLog(
            event_id=event.id,
            admin_user_id=admin.id,
            action="keyword.edit",
            target_type="keyword",
            reason="merge",
        )
    )
    db_session.add(
        AdminAuditLog(
            event_id=event.id,
            admin_user_id=admin.id,
            action="completion_code.redeem",
            target_type="completion_code",
            reason="reward",
        )
    )
    db_session.commit()

    all_logs = client.get(
        f"/api/admin/events/{event.slug}/audit-logs",
        headers=auth_headers(admin),
    )
    filtered = client.get(
        f"/api/admin/events/{event.slug}/audit-logs",
        params={"action": "keyword.edit", "targetType": "keyword"},
        headers=auth_headers(admin),
    )
    unauthenticated = client.get(f"/api/admin/events/{event.slug}/audit-logs")

    assert all_logs.status_code == 200
    assert all_logs.json()["total"] == 2
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["action"] == "keyword.edit"
    assert unauthenticated.status_code == 401
