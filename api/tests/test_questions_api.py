from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.scripts.seed_questions import seed_questions_for_event


def test_questions_api_returns_seeded_questions_ordered(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)

    response = client.get(f"/api/events/{event.slug}/questions")

    assert response.status_code == 200
    questions = response.json()["questions"]
    assert len(questions) == 61
    assert [question["questionNo"] for question in questions] == list(range(1, 62))
    assert [question["displayOrder"] for question in questions] == list(range(1, 62))

    by_no = {question["questionNo"]: question for question in questions}
    assert by_no[15]["scaleCode"] == "kmies"
    assert by_no[21]["scaleCode"] == "phq9"
    assert by_no[29]["questionKey"] == "phq9_09"
    assert by_no[30]["scaleCode"] == "pcl5"
    assert by_no[50]["scaleCode"] == "kscs"
    assert by_no[61]["questionKey"] == "kscs_12"
    assert "scoreMap" not in by_no[21]


def test_questions_api_missing_event_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/events/missing-event/questions")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EVENT_NOT_FOUND"
