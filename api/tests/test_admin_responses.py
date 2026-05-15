from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.completion import CompletionCode
from app.models.event import Event
from app.models.question import Question
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from tests.admin_test_utils import auth_headers, create_admin


def create_response_dataset(db_session: Session, event: Event) -> EventSession:
    questions: list[Question] = []
    for question_no in range(1, 62):
        question = Question(
            event_id=event.id,
            question_no=question_no,
            scale_code="profile" if question_no <= 5 else "phq9",
            question_key=f"test_q{question_no:03d}",
            title="귀하의 연령대는 어떻게 되십니까?" if question_no == 1 else f"테스트 문항 {question_no}",
            description=None,
            question_type="single_select",
            options=[
                {"label": "20대", "value": "q01_opt01"},
                {"label": "30대", "value": "q01_opt02"},
            ]
            if question_no == 1
            else [],
            score_map={},
            required=True,
            display_order=question_no,
        )
        db_session.add(question)
        questions.append(question)
    db_session.flush()

    session = EventSession(
        event_id=event.id,
        anonymous_key_hash="anonymous-secret-hash",
        resume_token_hash="resume-secret-hash",
        status="completed",
        last_step="complete",
        client_meta={"ipHash": "ip-secret-hash", "userAgentHash": "ua-secret-hash"},
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.flush()

    db_session.add(
        Answer(
            event_id=event.id,
            session_id=session.id,
            question_id=questions[0].id,
            answer_value="q01_opt02",
            score_value=Decimal("0"),
        )
    )
    db_session.add(
        Answer(
            event_id=event.id,
            session_id=session.id,
            question_id=questions[1].id,
            answer_value="=SUM(A1:A2)",
            score_value=Decimal("1"),
        )
    )
    for scale_code in ["phq9", "pcl5", "kmies", "kscs"]:
        db_session.add(
            ScaleScore(
                event_id=event.id,
                session_id=session.id,
                scale_code=scale_code,
                raw_score=Decimal("3"),
                severity_level="mild_depressive_symptoms" if scale_code == "phq9" else "low",
                sub_scores={},
                rule_version="test",
            )
        )
    db_session.add(
        RiskFlag(
            event_id=event.id,
            session_id=session.id,
            phq9_item9_positive=True,
            crisis_expression_detected=False,
            trauma_high_signal=True,
            moral_injury_high_signal=False,
            public_restriction=True,
            help_notice_required=True,
            details={"private": "do not export"},
            rule_version="test",
        )
    )
    db_session.add(
        CompletionCode(
            event_id=event.id,
            session_id=session.id,
            code=f"TREE-SECRET-{uuid4().hex[:6]}",
            status="issued",
        )
    )
    db_session.commit()
    db_session.refresh(session)
    return session


def test_admin_responses_requires_auth(client: TestClient, db_session: Session, event_factory) -> None:
    event = event_factory()
    create_response_dataset(db_session, event)

    response = client.get(f"/api/admin/events/{event.slug}/responses")

    assert response.status_code == 401


def test_admin_responses_columns_api_returns_61_question_columns(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    response = client.get(
        f"/api/admin/events/{event.slug}/responses/columns",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["questionColumns"]) == 61
    assert data["questionColumns"][0]["key"] == "q001"
    assert data["questionColumns"][-1]["key"] == "q061"
    assert "귀하의 연령대" in data["questionColumns"][0]["label"]


def test_admin_responses_summary_view_returns_session_rows_and_labels(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    response = client.get(
        f"/api/admin/events/{event.slug}/responses",
        headers=auth_headers(admin),
    )

    assert response.status_code == 200
    data = response.json()
    keys = {column["key"] for column in data["columns"]}
    assert data["total"] == 1
    assert len(data["rows"]) == 1
    assert data["rows"][0]["q001"] == "30대"
    assert data["rows"][0]["phq9Severity"] == "mild_depressive_symptoms"
    assert "helpNoticeRequired" not in keys
    response_text = response.text
    assert "resume-secret-hash" not in response_text
    assert "anonymous-secret-hash" not in response_text
    assert "ip-secret-hash" not in response_text
    assert "ua-secret-hash" not in response_text
    assert "TREE-SECRET" not in response_text


def test_admin_responses_wide_and_long_views(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    wide = client.get(
        f"/api/admin/events/{event.slug}/responses",
        params={"view": "wide"},
        headers=auth_headers(admin),
    )
    long = client.get(
        f"/api/admin/events/{event.slug}/responses",
        params={"view": "long"},
        headers=auth_headers(admin),
    )

    assert wide.status_code == 200
    wide_data = wide.json()
    assert len(wide_data["rows"]) == 1
    assert wide_data["rows"][0]["eventSlug"] == event.slug
    assert wide_data["rows"][0]["sessionStatus"] == "completed"

    assert long.status_code == 200
    long_data = long.json()
    assert long_data["total"] == 1
    assert len(long_data["rows"]) == 2
    first_answer = next(row for row in long_data["rows"] if row["questionNo"] == 1)
    assert first_answer["answerValue"] == "q01_opt02"
    assert first_answer["answerLabel"] == "30대"


def test_admin_responses_optional_risk_flag_columns(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)
    create_response_dataset(db_session, event)

    without_risk = client.get(
        f"/api/admin/events/{event.slug}/responses",
        params={"includeRiskFlags": "false"},
        headers=auth_headers(admin),
    )
    with_risk = client.get(
        f"/api/admin/events/{event.slug}/responses",
        params={"includeRiskFlags": "true"},
        headers=auth_headers(admin),
    )

    assert without_risk.status_code == 200
    assert "helpNoticeRequired" not in {column["key"] for column in without_risk.json()["columns"]}

    assert with_risk.status_code == 200
    data = with_risk.json()
    assert "helpNoticeRequired" in {column["key"] for column in data["columns"]}
    assert data["rows"][0]["helpNoticeRequired"] is True
