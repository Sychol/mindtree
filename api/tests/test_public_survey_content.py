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
    assert data["surveyConfig"]["version"] == "v4-2026-05-18-kmies-9-items"
    assert "intro" in data["surveyConfig"]
    assert "consent" in data["surveyConfig"]
    assert "sections" in data["surveyConfig"]
    assert "questionOverrides" in data["surveyConfig"]
    assert "thanks" in data["surveyConfig"]
    sections = {section["id"]: section for section in data["surveyConfig"]["sections"]}
    assert sections["profile"]["questionNoRange"] == [1, 14]
    assert sections["kmies"]["questionNoRange"] == [15, 23]
    assert sections["phq9"]["questionNoRange"] == [24, 32]
    assert sections["pcl5"]["questionNoRange"] == [33, 52]
    assert sections["kscs"]["questionNoRange"] == [53, 64]
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
        f"/api/admin/events/{event.slug}/survey/questions/24/presentation",
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
    assert next(section for section in config["sections"] if section["id"] == "phq9")["questionNoRange"] == [24, 32]
    assert config["questionOverrides"]["24"] == {
        "title": "공개 반영 문항",
        "description": "공개 반영 문항 설명",
    }


def test_public_survey_content_ignores_old_question_overrides_when_rule_version_changes(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory(
        settings={
            "surveyConfig": {
                "version": "v3-2026-05-15-final-questions",
                "sections": [
                    {
                        "id": "kmies",
                        "sectionNo": 4,
                        "title": "Stored K-MIES title",
                        "questionNoRange": [15, 20],
                    }
                ],
                "questionOverrides": {"24": {"title": "Old shifted override"}},
            }
        }
    )
    seed_questions_for_event(db_session, event.slug)

    response = client.get(f"/api/events/{event.slug}/survey-content")

    assert response.status_code == 200
    config = response.json()["surveyConfig"]
    sections = {section["id"]: section for section in config["sections"]}
    assert sections["kmies"]["title"] == "Stored K-MIES title"
    assert sections["kmies"]["questionNoRange"] == [15, 23]
    assert config["questionOverrides"] == {}
