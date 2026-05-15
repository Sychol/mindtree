from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.question import Question
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.scripts.seed_questions import seed_questions_for_event


def _required_consent_payload(consent_version: str = "v1") -> dict:
    return {
        "consentVersion": consent_version,
        "acceptedItems": {
            "eventIsNotDiagnosis": True,
            "anonymousKeywordDisplay": True,
            "cardMayBeShownAnonymously": True,
            "noIdentifyingInfo": True,
            "adminModeration": True,
        },
    }


def _create_session(client: TestClient, event_slug: str) -> dict:
    response = client.post(
        f"/api/events/{event_slug}/sessions",
        json={"clientMeta": {"device": "mobile", "timezone": "Asia/Seoul"}},
    )
    assert response.status_code == 200
    return response.json()


def _create_consented_session(client: TestClient, event_slug: str) -> UUID:
    created = _create_session(client, event_slug)
    session_id = UUID(created["session"]["id"])
    response = client.post(
        f"/api/sessions/{session_id}/consent",
        json=_required_consent_payload(),
    )
    assert response.status_code == 200
    return session_id


def _questions(db_session: Session, event_id) -> list[Question]:
    return list(
        db_session.execute(
            select(Question).where(Question.event_id == event_id).order_by(Question.question_no)
        ).scalars()
    )


def _default_answer_value(question: Question):
    if question.question_no == 3:
        return "q03_opt01"
    return question.options[0]["value"]


def _payload_for_questions(questions: list[Question]) -> dict:
    return {
        "answers": [
            {
                "questionId": str(question.id),
                "answerValue": _default_answer_value(question),
            }
            for question in questions
        ],
        "clientProgress": {"lastQuestionNo": questions[-1].question_no if questions else None},
    }


def test_consented_session_can_submit_all_answers_and_transition(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    session_id = _create_consented_session(client, event.slug)
    questions = _questions(db_session, event.id)

    response = client.put(
        f"/api/sessions/{session_id}/answers/bulk",
        json=_payload_for_questions(questions),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["savedCount"] == 61
    assert data["missingQuestionNos"] == []
    assert data["sessionStatus"] == "questions_completed"
    assert data["scoring"]["calculated"] is True
    assert {score["scaleCode"] for score in data["scoring"]["scaleScores"]} == {
        "phq9",
        "pcl5",
        "kmies",
        "kscs",
    }
    assert data["scoring"]["riskFlags"]["phq9Item9Positive"] is False

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session_id)
    assert stored_session is not None
    assert stored_session.status == "questions_completed"
    assert stored_session.last_step == "summary"
    assert db_session.execute(
        select(Answer).where(Answer.session_id == session_id)
    ).scalars().all()
    assert len(db_session.execute(select(ScaleScore).where(ScaleScore.session_id == session_id)).scalars().all()) == 4
    assert db_session.execute(
        select(RiskFlag).where(RiskFlag.session_id == session_id)
    ).scalar_one().rule_version == "v3-2026-05-15-final-questions"


def test_same_payload_is_idempotent(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    session_id = _create_consented_session(client, event.slug)
    payload = _payload_for_questions(_questions(db_session, event.id))

    first = client.put(f"/api/sessions/{session_id}/answers/bulk", json=payload)
    second = client.put(f"/api/sessions/{session_id}/answers/bulk", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    db_session.expire_all()
    answers = db_session.execute(
        select(Answer).where(Answer.session_id == session_id)
    ).scalars().all()
    assert len(answers) == 61


def test_partial_submission_returns_missing_question_nos(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    session_id = _create_consented_session(client, event.slug)
    questions = _questions(db_session, event.id)

    response = client.put(
        f"/api/sessions/{session_id}/answers/bulk",
        json=_payload_for_questions(questions[:40]),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["savedCount"] == 40
    assert data["sessionStatus"] == "consented"
    assert data["scoring"]["calculated"] is False
    assert data["missingQuestionNos"][0] == 41


def test_general_public_profile_answer_allows_skipping_questions_4_and_5(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    session_id = _create_consented_session(client, event.slug)
    questions = [
        question
        for question in _questions(db_session, event.id)
        if question.question_no not in {4, 5}
    ]
    payload = _payload_for_questions(questions)
    for answer in payload["answers"]:
        question = next(
            question
            for question in questions
            if str(question.id) == answer["questionId"]
        )
        if question.question_no == 3:
            answer["answerValue"] = "q03_opt05"

    response = client.put(
        f"/api/sessions/{session_id}/answers/bulk",
        json=payload,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["savedCount"] == 59
    assert data["missingQuestionNos"] == []
    assert data["sessionStatus"] == "questions_completed"


def test_created_session_cannot_submit_answers(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    created = _create_session(client, event.slug)
    question = _questions(db_session, event.id)[0]

    response = client.put(
        f"/api/sessions/{created['session']['id']}/answers/bulk",
        json={
            "answers": [{"questionId": str(question.id), "answerValue": question.options[0]["value"]}],
            "clientProgress": {},
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CONSENT_REQUIRED"


def test_invalid_answer_value_returns_bad_request(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    session_id = _create_consented_session(client, event.slug)
    phq9_question = next(question for question in _questions(db_session, event.id) if question.question_no == 21)

    response = client.put(
        f"/api/sessions/{session_id}/answers/bulk",
        json={
            "answers": [{"questionId": str(phq9_question.id), "answerValue": 99}],
            "clientProgress": {},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_other_event_question_id_returns_bad_request(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    other_event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    seed_questions_for_event(db_session, other_event.slug)
    session_id = _create_consented_session(client, event.slug)
    other_question = _questions(db_session, other_event.id)[0]

    response = client.put(
        f"/api/sessions/{session_id}/answers/bulk",
        json={
            "answers": [{"questionId": str(other_question.id), "answerValue": other_question.options[0]["value"]}],
            "clientProgress": {},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
