from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SessionStatus
from app.models.event import Event
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.models.summary import Summary


def _create_session_with_results(
    db_session: Session,
    event: Event,
    *,
    status: str = SessionStatus.QUESTIONS_COMPLETED.value,
    with_scores: bool = True,
    with_risk: bool = True,
) -> EventSession:
    session = EventSession(
        event_id=event.id,
        anonymous_key_hash=f"anon-{uuid4()}",
        resume_token_hash=f"resume-{uuid4()}",
        status=status,
        last_step="summary",
        client_meta={},
    )
    db_session.add(session)
    db_session.flush()

    if with_scores:
        for scale_code, raw_score, severity_level in [
            ("phq9", Decimal("7"), "mild_depressive_symptoms"),
            ("pcl5", Decimal("32"), "threshold"),
            ("kmies", Decimal("22"), "moderate"),
            ("kscs", Decimal("2.2"), "low"),
        ]:
            db_session.add(
                ScaleScore(
                    event_id=event.id,
                    session_id=session.id,
                    scale_code=scale_code,
                    raw_score=raw_score,
                    severity_level=severity_level,
                    sub_scores={},
                    rule_version="v2-2026-05-13-scale-cutoffs",
                )
            )

    if with_risk:
        db_session.add(
            RiskFlag(
                event_id=event.id,
                session_id=session.id,
                phq9_item9_positive=False,
                crisis_expression_detected=False,
                trauma_high_signal=False,
                moral_injury_high_signal=False,
                public_restriction=False,
                help_notice_required=False,
                details={"kscs_level": "low"},
                rule_version="v2-2026-05-13-scale-cutoffs",
            )
        )

    db_session.commit()
    db_session.refresh(session)
    return session


def test_get_summary_creates_summary_for_questions_completed_session(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _create_session_with_results(db_session, event)

    response = client.get(f"/api/sessions/{session.id}/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["id"]
    assert data["summary"]["finalText"]
    assert data["summary"]["generationMode"] == "template"
    assert data["summary"]["helpNoticeRequired"] is False
    assert data["summary"]["isDiagnosis"] is False
    assert data["riskNotice"]["showHelpNotice"] is False

    db_session.expire_all()
    stored_summary = db_session.execute(
        select(Summary).where(Summary.session_id == session.id)
    ).scalar_one()
    assert stored_summary.final_text == data["summary"]["finalText"]


def test_get_summary_reuses_existing_summary(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _create_session_with_results(db_session, event)

    first = client.get(f"/api/sessions/{session.id}/summary")
    second = client.get(f"/api/sessions/{session.id}/summary")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["summary"]["id"] == second.json()["summary"]["id"]
    summaries = db_session.execute(
        select(Summary).where(Summary.session_id == session.id)
    ).scalars().all()
    assert len(summaries) == 1


def test_get_summary_rejects_created_or_consented_session(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    created_session = _create_session_with_results(
        db_session,
        event,
        status=SessionStatus.CREATED.value,
        with_scores=False,
        with_risk=False,
    )

    response = client.get(f"/api/sessions/{created_session.id}/summary")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "QUESTIONS_NOT_COMPLETED"


def test_get_summary_requires_scale_scores_and_risk_flags(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _create_session_with_results(
        db_session,
        event,
        with_scores=False,
        with_risk=False,
    )

    response = client.get(f"/api/sessions/{session.id}/summary")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "QUESTIONS_NOT_COMPLETED"


def test_mark_summary_viewed_transitions_session(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _create_session_with_results(db_session, event)

    response = client.post(f"/api/sessions/{session.id}/summary/viewed")

    assert response.status_code == 200
    data = response.json()
    assert data["sessionStatus"] == "summary_viewed"
    assert data["viewedAt"]

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session.id)
    stored_summary = db_session.execute(
        select(Summary).where(Summary.session_id == session.id)
    ).scalar_one()
    assert stored_session is not None
    assert stored_session.status == "summary_viewed"
    assert stored_session.last_step == "cards/new"
    assert stored_summary.viewed_at is not None


def test_mark_summary_viewed_is_idempotent_after_later_status(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _create_session_with_results(
        db_session,
        event,
        status=SessionStatus.CARD_CREATED.value,
    )
    viewed_at = datetime(2026, 5, 13, 9, 0, tzinfo=timezone.utc)
    summary = Summary(
        event_id=event.id,
        session_id=session.id,
        template_text="기존 템플릿",
        final_text="기존 요약",
        generation_mode="template",
        viewed_at=viewed_at,
    )
    db_session.add(summary)
    db_session.commit()

    response = client.post(f"/api/sessions/{session.id}/summary/viewed")

    assert response.status_code == 200
    assert response.json()["sessionStatus"] == "card_created"

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session.id)
    stored_summary = db_session.get(Summary, summary.id)
    assert stored_session is not None
    assert stored_session.status == "card_created"
    assert stored_summary is not None
    assert stored_summary.viewed_at == viewed_at
