from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.completion import CompletionCode
from app.models.keyword import KeywordJob
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.scripts.seed_questions import seed_questions_for_event
from tests.test_cards_api import _card, _session


def _consent_payload(consent_version: str = "v1") -> dict:
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


def _answer_value(question: dict):
    options = question.get("options") or []
    if question["questionNo"] == 3:
        return "q03_opt01"
    if question["questionType"] == "multi_select" and options:
        return [options[0]["value"]]
    if options:
        return options[0]["value"]
    if question["questionType"] == "number":
        return 0
    return "field integration safe response"


def test_participant_backend_field_flow_reaches_completion_and_keyword_jobs(
    client,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory(settings={"completionCodePrefix": "TREE"})
    seed_questions_for_event(db_session, event.slug)
    peer_session = _session(db_session, event)
    peer_card = _card(
        db_session,
        event,
        peer_session,
        content="A calm pause and a steady breath helped me continue.",
    )

    created = client.post(
        f"/api/events/{event.slug}/sessions",
        json={"clientMeta": {"device": "api-smoke"}},
    )
    assert created.status_code == 200
    session_id = created.json()["session"]["id"]
    assert created.json()["resumeToken"]

    consent = client.post(
        f"/api/sessions/{session_id}/consent",
        json=_consent_payload(event.consent_version),
    )
    assert consent.status_code == 200
    assert consent.json()["sessionStatus"] == "consented"

    questions = client.get(f"/api/events/{event.slug}/questions")
    assert questions.status_code == 200
    question_items = questions.json()["questions"]
    assert len(question_items) == 64

    answers = client.put(
        f"/api/sessions/{session_id}/answers/bulk",
        json={
            "answers": [
                {"questionId": question["id"], "answerValue": _answer_value(question)}
                for question in question_items
            ],
            "clientProgress": {"lastQuestionNo": question_items[-1]["questionNo"]},
        },
    )
    assert answers.status_code == 200
    assert answers.json()["sessionStatus"] == "questions_completed"
    assert answers.json()["scoring"]["riskFlags"]["phq9Item9Positive"] is False

    summary = client.get(f"/api/sessions/{session_id}/summary")
    assert summary.status_code == 200
    assert summary.json()["summary"]["finalText"]

    viewed = client.post(f"/api/sessions/{session_id}/summary/viewed")
    assert viewed.status_code == 200
    assert viewed.json()["sessionStatus"] == "summary_viewed"

    card = client.post(
        f"/api/sessions/{session_id}/cards",
        json={
            "promptType": "to_now_me",
            "content": "I can pause, breathe, and take the next small step.",
        },
    )
    assert card.status_code == 200
    assert card.json()["sessionStatus"] == "card_created"
    assert card.json()["keywordJob"]["status"] == "pending"

    public_cards = client.get(
        f"/api/events/{event.slug}/cards/public",
        params={"excludeSessionId": session_id, "limit": 10},
    )
    assert public_cards.status_code == 200
    assert public_cards.json()["cards"][0]["id"] == str(peer_card.id)

    selected = client.post(
        f"/api/sessions/{session_id}/selected-card",
        json={"selectedCardId": str(peer_card.id)},
    )
    assert selected.status_code == 200

    reply = client.post(
        f"/api/sessions/{session_id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "comfort",
            "content": "I am cheering for your next steady step.",
        },
    )
    assert reply.status_code == 200
    assert reply.json()["sessionStatus"] == "completed"
    assert reply.json()["completion"]["eligible"] is True

    completion = client.get(f"/api/sessions/{session_id}/completion-code")
    assert completion.status_code == 200
    assert completion.json()["completionCode"]["status"] == "issued"

    stored_session = db_session.get(EventSession, session_id)
    assert stored_session is not None
    assert stored_session.status == "completed"
    assert db_session.execute(select(Answer).where(Answer.session_id == stored_session.id)).scalars().all()
    assert len(db_session.execute(select(ScaleScore).where(ScaleScore.session_id == stored_session.id)).scalars().all()) == 4
    assert db_session.execute(select(RiskFlag).where(RiskFlag.session_id == stored_session.id)).scalar_one()
    assert db_session.execute(select(CompletionCode).where(CompletionCode.session_id == stored_session.id)).scalar_one()
    assert len(db_session.execute(select(KeywordJob).where(KeywordJob.event_id == event.id)).scalars().all()) >= 2
