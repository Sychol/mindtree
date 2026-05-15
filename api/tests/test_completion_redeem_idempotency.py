from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, SessionStatus
from app.models.risk import RiskFlag
from tests.admin_test_utils import auth_headers, create_admin
from tests.test_cards_api import _session


def test_completion_redeem_is_idempotent_and_does_not_block_risk_flagged_session(
    client,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    session = _session(db_session, event, status=SessionStatus.COMPLETED.value)
    risk = db_session.execute(select(RiskFlag).where(RiskFlag.session_id == session.id)).scalar_one()
    risk.phq9_item9_positive = True
    risk.public_restriction = True
    db_session.add(risk)
    completion_code = CompletionCode(
        event_id=event.id,
        session_id=session.id,
        code="TREE-IDEMP1",
        status=CompletionCodeStatus.ISSUED.value,
    )
    db_session.add(completion_code)
    db_session.commit()

    first = client.post(
        f"/api/admin/events/{event.slug}/completion-codes/{completion_code.code}/redeem",
        json={"notes": "field reward"},
        headers=auth_headers(admin),
    )
    second = client.post(
        f"/api/admin/events/{event.slug}/completion-codes/{completion_code.code}/redeem",
        json={"notes": "duplicate attempt"},
        headers=auth_headers(admin),
    )

    assert first.status_code == 200
    assert first.json()["completionCode"]["status"] == "redeemed"
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "COMPLETION_CODE_ALREADY_REDEEMED"

    db_session.expire_all()
    stored = db_session.get(CompletionCode, completion_code.id)
    assert stored is not None
    assert stored.status == CompletionCodeStatus.REDEEMED.value
    assert stored.redeemed_at is not None
    assert stored.redeemed_by == admin.id
    assert stored.notes == "field reward"

    audits = db_session.execute(
        select(AdminAuditLog).where(
            AdminAuditLog.target_id == completion_code.id,
            AdminAuditLog.action == "completion_code.redeem",
        )
    ).scalars().all()
    assert len(audits) == 1
