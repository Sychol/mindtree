from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.scripts.seed_questions import seed_questions_for_event
from tests.admin_test_utils import auth_headers, create_admin


def _seeded_event(db_session: Session, event_factory):
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    db_session.refresh(event)
    return event


def test_public_survey_content_returns_display_config_only(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = _seeded_event(db_session, event_factory)

    response = client.get(f"/api/events/{event.slug}/survey-content")

    assert response.status_code == 200
    data = response.json()
    assert data["eventSlug"] == event.slug
    assert "intro" in data["surveyConfig"]
    assert "consent" in data["surveyConfig"]
    assert "sections" in data["surveyConfig"]
    assert "questionOverrides" in data["surveyConfig"]
    assert "thanks" in data["surveyConfig"]
    response_text = response.text
    assert "scoreMap" not in response_text
    assert "riskFlags" not in response_text
    assert "adminUser" not in response_text
    assert "audit" not in response_text


def test_public_survey_content_reflects_admin_presentation_updates(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = _seeded_event(db_session, event_factory)
    admin = create_admin(db_session)
    headers = auth_headers(admin)
    initial = client.get(f"/api/admin/events/{event.slug}/survey", headers=headers).json()
    consent_payload = initial["surveyConfig"]["consent"]
    consent_payload["title"] = "공개 반영 동의서"
    consent_payload["reason"] = "공개 반영 확인"

    intro = client.patch(
        f"/api/admin/events/{event.slug}/survey/intro",
        json={
            "title": "공개 반영 소개",
            "subtitle": "테스트 부제",
            "paragraphs": ["공개 화면에 반영될 소개문입니다."],
            "showLogo": False,
            "showAppScreens": False,
        },
        headers=headers,
    )
    consent = client.patch(
        f"/api/admin/events/{event.slug}/survey/consent",
        json=consent_payload,
        headers=headers,
    )
    section = client.patch(
        f"/api/admin/events/{event.slug}/survey/sections/phq9",
        json={"title": "최근 2주 마음 상태", "description": "공개 반영 섹션 설명"},
        headers=headers,
    )
    question = client.patch(
        f"/api/admin/events/{event.slug}/survey/questions/21/presentation",
        json={"title": "공개 반영 문항", "description": "공개 반영 문항 설명"},
        headers=headers,
    )

    assert intro.status_code == 200
    assert consent.status_code == 200
    assert section.status_code == 200
    assert question.status_code == 200

    response = client.get(f"/api/events/{event.slug}/survey-content")

    assert response.status_code == 200
    config = response.json()["surveyConfig"]
    assert config["intro"]["title"] == "공개 반영 소개"
    assert config["intro"]["showLogo"] is False
    assert config["consent"]["title"] == "공개 반영 동의서"
    assert next(section for section in config["sections"] if section["id"] == "phq9")["title"] == "최근 2주 마음 상태"
    assert config["questionOverrides"]["21"] == {
        "title": "공개 반영 문항",
        "description": "공개 반영 문항 설명",
    }
