from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_admin_responses import create_response_dataset


def _export_payload(**overrides):
    payload = {
        "format": "wide",
        "includeScores": True,
        "includeRiskFlags": False,
        "includeCompletionStatus": True,
        "status": "completed",
        "completedOnly": False,
        "createdFrom": None,
        "createdTo": None,
        "reason": "행사 종료 후 응답 데이터 확인",
    }
    payload.update(overrides)
    return payload


def test_admin_response_export_requires_auth(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    create_response_dataset(db_session, event)

    response = client.post(
        f"/api/admin/events/{event.slug}/responses/export.csv",
        json=_export_payload(),
    )

    assert response.status_code == 401


def test_admin_response_export_wide_csv_bom_headers_korean_and_sanitize(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    response = client.post(
        f"/api/admin/events/{event.slug}/responses/export.csv",
        json=_export_payload(),
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "filename=" in response.headers["content-disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    csv_text = response.content.decode("utf-8-sig")
    header = csv_text.splitlines()[0]
    assert "event_slug" in header
    assert "q001" in header
    assert "phq9_raw_score" in header
    assert "help_notice_required" not in header
    assert "귀하의 연령대" not in csv_text
    assert "30대" in csv_text
    assert "'=SUM(A1:A2)" in csv_text
    assert "TREE-SECRET" not in csv_text


def test_admin_response_export_long_csv(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    response = client.post(
        f"/api/admin/events/{event.slug}/responses/export.csv",
        json=_export_payload(format="long"),
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    csv_text = response.content.decode("utf-8-sig")
    header = csv_text.splitlines()[0]
    assert header.startswith("event_slug,session_short_id,session_status,question_no")
    assert "question_title" in header
    assert "answer_label" in header
    assert "phq9_raw_score" not in header
    assert "help_notice_required" not in header
    assert "귀하의 연령대는 어떻게 되십니까?" in csv_text
    assert "30대" in csv_text


def test_admin_response_export_risk_flags_are_opt_in(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    without_risk = client.post(
        f"/api/admin/events/{event.slug}/responses/export.csv",
        json=_export_payload(includeRiskFlags=False),
        headers=auth_headers(admin),
    )
    with_risk = client.post(
        f"/api/admin/events/{event.slug}/responses/export.csv",
        json=_export_payload(includeRiskFlags=True),
        headers=auth_headers(admin),
    )

    assert without_risk.status_code == 200
    assert "help_notice_required" not in without_risk.content.decode("utf-8-sig").splitlines()[0]
    assert with_risk.status_code == 200
    assert "help_notice_required" in with_risk.content.decode("utf-8-sig").splitlines()[0]


def test_admin_response_export_writes_audit_log_without_csv_body(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    response = client.post(
        f"/api/admin/events/{event.slug}/responses/export.csv",
        json=_export_payload(),
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    db_session.expire_all()
    audit = db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.event_id == event.id,
            AdminAuditLog.action == "responses.export",
        )
    ).scalar_one()
    assert audit.reason == "행사 종료 후 응답 데이터 확인"
    assert audit.after_value["format"] == "wide"
    assert audit.after_value["includeRiskFlags"] is False
    audit_text = str(audit.after_value)
    assert "30대" not in audit_text
    assert "=SUM(A1:A2)" not in audit_text
    assert "TREE-SECRET" not in audit_text
