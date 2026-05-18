from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AdminAuditLog
from app.scripts.seed_questions import seed_questions_for_event
from tests.admin_test_utils import auth_headers, create_admin


def _seeded_event(db_session: Session, event_factory):
    event = event_factory()
    seed_questions_for_event(db_session, event.slug)
    db_session.refresh(event)
    return event


def _consent_payload(consent: dict, *, title: str | None = None) -> dict:
    return {
        "title": title or consent["title"],
        "sections": consent["sections"],
        "items": consent["items"],
        "reason": "동의서 문구 확정",
    }


def _audit_actions(db_session: Session, event_id) -> list[str]:
    return list(
        db_session.execute(
            select(AdminAuditLog.action)
            .where(AdminAuditLog.event_id == event_id)
            .order_by(AdminAuditLog.created_at.asc())
        ).scalars()
    )


def test_admin_survey_requires_auth(client: TestClient, db_session: Session, event_factory) -> None:
    event = _seeded_event(db_session, event_factory)

    response = client.get(f"/api/admin/events/{event.slug}/survey")

    assert response.status_code == 401


def test_admin_survey_get_returns_default_64_question_flow(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = _seeded_event(db_session, event_factory)
    admin = create_admin(db_session)

    response = client.get(f"/api/admin/events/{event.slug}/survey", headers=auth_headers(admin))

    assert response.status_code == 200
    data = response.json()
    assert data["event"]["slug"] == event.slug
    assert data["surveyConfig"]["version"] == "v4-2026-05-18-kmies-9-items"
    assert len(data["surveyConfig"]["sections"]) == 8
    assert [section["id"] for section in data["surveyConfig"]["sections"]] == [
        "intro",
        "consent",
        "profile",
        "kmies",
        "phq9",
        "pcl5",
        "kscs",
        "thanks",
    ]
    summaries = {section["id"]: section for section in data["sectionSummaries"]}
    assert summaries["profile"]["questionNoRange"] == [1, 14]
    assert summaries["profile"]["questionCount"] == 14
    assert summaries["kmies"]["questionNoRange"] == [15, 23]
    assert summaries["kmies"]["questionCount"] == 9
    assert summaries["phq9"]["questionNoRange"] == [24, 32]
    assert summaries["pcl5"]["questionNoRange"] == [33, 52]
    assert summaries["kscs"]["questionNoRange"] == [53, 64]
    assert sum(section["questionCount"] for section in data["sectionSummaries"]) == 64
    assert data["questionsBySection"][0]["sectionId"] == "profile"
    assert sum(len(section["questions"]) for section in data["questionsBySection"]) == 64
    first_question = data["questionsBySection"][0]["questions"][0]
    assert first_question["questionNo"] == 1
    assert first_question["displayTitle"] == first_question["title"]
    assert first_question["editable"]["questionNo"] is False
    assert first_question["editable"]["scoreMap"] is False
    assert first_question["optionsCount"] >= 0


def test_admin_survey_ignores_old_question_overrides_when_rule_version_changes(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory(
        settings={
            "surveyConfig": {
                "version": "v3-2026-05-15-final-questions",
                "intro": {"title": "Stored intro"},
                "sections": [
                    {
                        "id": "phq9",
                        "sectionNo": 5,
                        "title": "Stored PHQ title",
                        "description": "Stored PHQ description",
                        "questionNoRange": [21, 29],
                    }
                ],
                "questionOverrides": {
                    "21": {"title": "Old PHQ item 1"},
                    "24": {"title": "Old shifted item"},
                },
                "thanks": {"title": "Stored thanks", "paragraphs": ["Stored closing"]},
            }
        }
    )
    seed_questions_for_event(db_session, event.slug)
    admin = create_admin(db_session)

    response = client.get(f"/api/admin/events/{event.slug}/survey", headers=auth_headers(admin))

    assert response.status_code == 200
    data = response.json()
    config = data["surveyConfig"]
    summaries = {section["id"]: section for section in data["sectionSummaries"]}
    assert config["version"] == "v4-2026-05-18-kmies-9-items"
    assert config["intro"]["title"] == "Stored intro"
    assert next(section for section in config["sections"] if section["id"] == "phq9")["title"] == "Stored PHQ title"
    assert summaries["phq9"]["questionNoRange"] == [24, 32]
    assert config["questionOverrides"] == {}


def test_admin_survey_updates_and_audit_logs(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = _seeded_event(db_session, event_factory)
    admin = create_admin(db_session)
    headers = auth_headers(admin)

    initial = client.get(f"/api/admin/events/{event.slug}/survey", headers=headers).json()

    intro = client.patch(
        f"/api/admin/events/{event.slug}/survey/intro",
        json={
            "title": "현장 마음 점검",
            "subtitle": "소방안전박람회",
            "paragraphs": ["소개문을 확정했습니다."],
            "showLogo": True,
            "showAppScreens": False,
            "reason": "행사 문구 확정",
        },
        headers=headers,
    )
    consent = client.patch(
        f"/api/admin/events/{event.slug}/survey/consent",
        json=_consent_payload(initial["surveyConfig"]["consent"], title="새 동의서 제목"),
        headers=headers,
    )
    section = client.patch(
        f"/api/admin/events/{event.slug}/survey/sections/profile",
        json={"title": "기본 정보", "description": "기본 정보를 확인합니다.", "reason": "섹션 설명 보완"},
        headers=headers,
    )
    question = client.patch(
        f"/api/admin/events/{event.slug}/survey/questions/1/presentation",
        json={"title": "표시용 1번 문항", "description": "현장 표현 보완", "reason": "문항 표현 보완"},
        headers=headers,
    )
    thanks = client.patch(
        f"/api/admin/events/{event.slug}/survey/thanks",
        json={
            "title": "참여해주셔서 감사합니다.",
            "paragraphs": ["저장되었습니다.", "다음 화면에서 요약을 확인하세요."],
            "reason": "완료 안내 문구 수정",
        },
        headers=headers,
    )

    assert intro.status_code == 200
    assert consent.status_code == 200
    assert section.status_code == 200
    assert question.status_code == 200
    assert thanks.status_code == 200

    db_session.expire_all()
    stored = db_session.get(type(event), event.id)
    config = stored.settings["surveyConfig"]
    assert config["intro"]["title"] == "현장 마음 점검"
    assert config["consent"]["title"] == "새 동의서 제목"
    assert next(item for item in config["sections"] if item["id"] == "profile")["title"] == "기본 정보"
    assert config["questionOverrides"]["1"]["title"] == "표시용 1번 문항"
    assert config["thanks"]["paragraphs"][0] == "저장되었습니다."

    actions = _audit_actions(db_session, event.id)
    assert "survey_intro.update" in actions
    assert "survey_consent.update" in actions
    assert "survey_section.update" in actions
    assert "survey_question_presentation.update" in actions
    assert "survey_thanks.update" in actions


def test_admin_survey_rejects_builder_style_mutations(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = _seeded_event(db_session, event_factory)
    admin = create_admin(db_session)
    headers = auth_headers(admin)
    initial = client.get(f"/api/admin/events/{event.slug}/survey", headers=headers).json()

    invalid_consent = _consent_payload(initial["surveyConfig"]["consent"])
    invalid_consent["items"][0]["key"] = "changedKey"

    consent_response = client.patch(
        f"/api/admin/events/{event.slug}/survey/consent",
        json=invalid_consent,
        headers=headers,
    )
    section_response = client.patch(
        f"/api/admin/events/{event.slug}/survey/sections/profile",
        json={"title": "기본 정보", "questionNoRange": [1, 20]},
        headers=headers,
    )
    question_response = client.patch(
        f"/api/admin/events/{event.slug}/survey/questions/1/presentation",
        json={
            "title": "표시용",
            "scoreMap": {"0": 0},
            "options": [{"label": "변경", "value": "x"}],
        },
        headers=headers,
    )

    assert consent_response.status_code == 400
    assert section_response.status_code == 400
    assert question_response.status_code == 400


def test_admin_survey_reset_removes_saved_config(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = _seeded_event(db_session, event_factory)
    admin = create_admin(db_session)
    headers = auth_headers(admin)

    update = client.patch(
        f"/api/admin/events/{event.slug}/survey/intro",
        json={
            "title": "변경된 제목",
            "subtitle": "",
            "paragraphs": ["변경"],
            "showLogo": True,
            "showAppScreens": True,
        },
        headers=headers,
    )
    assert update.status_code == 200

    reset = client.post(
        f"/api/admin/events/{event.slug}/survey/reset",
        json={"reason": "기본 설문 표시 설정으로 초기화"},
        headers=headers,
    )

    assert reset.status_code == 200
    assert reset.json()["surveyConfig"]["intro"]["title"] == "리본톡 소개 및 설문"
    db_session.expire_all()
    stored = db_session.get(type(event), event.id)
    assert "surveyConfig" not in stored.settings
    assert "survey_config.reset" in _audit_actions(db_session, event.id)
