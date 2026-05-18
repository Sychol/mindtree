from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.admin import AdminUser
from app.models.enums import EventStatus
from app.models.event import Event
from app.models.question import Question
from app.repositories.events import EventRepository
from app.repositories.questions import QuestionRepository
from app.schemas.admin_survey import (
    AdminSurveyEvent,
    AdminSurveyMutationResponse,
    AdminSurveyQuestionEditable,
    AdminSurveyQuestionItem,
    AdminSurveyQuestionsBySection,
    AdminSurveyResponse,
    SurveyConfig,
    SurveyConsentUpdateRequest,
    SurveyIntroUpdateRequest,
    SurveyQuestionPresentationUpdateRequest,
    SurveyResetRequest,
    SurveySectionSummary,
    SurveySectionUpdateRequest,
    SurveyThanksUpdateRequest,
    config_to_dict,
)
from app.schemas.survey_content import PublicSurveyContentResponse
from app.services.audit_log import create_audit_log

SURVEY_CONFIG_KEY = "surveyConfig"
SURVEY_CONFIG_VERSION = "v1"

REQUIRED_CONSENT_ITEM_KEYS = (
    "researchParticipationConsent",
    "personalDataUseConsent",
    "sensitiveInfoConsent",
    "deidentifiedAiRagUseConsent",
)

FINAL_61_SECTIONS: list[dict[str, Any]] = [
    {"id": "intro", "sectionNo": 1, "title": "리본톡 소개 및 설문"},
    {"id": "consent", "sectionNo": 2, "title": "연구 참여 동의설명문 및 동의서"},
    {"id": "profile", "sectionNo": 3, "title": "인구통계", "questionNoRange": [1, 14]},
    {
        "id": "kmies",
        "sectionNo": 4,
        "title": "앞서 떠올린 경험에 비추어 응답해주세요.",
        "questionNoRange": [15, 20],
    },
    {
        "id": "phq9",
        "sectionNo": 5,
        "title": "지난 2주 동안, 아래 나열되는 증상들에 얼마나 자주 시달렸습니까?",
        "description": "최근 2주 동안의 상태를 기준으로 응답해 주세요.",
        "questionNoRange": [21, 29],
    },
    {
        "id": "pcl5",
        "sectionNo": 6,
        "title": "지난 2주 동안, 아래 나열되는 증상들에 얼마나 자주 시달렸습니까?",
        "description": "앞서 떠올린 스트레스 경험과 관련해 응답해 주세요.",
        "questionNoRange": [30, 49],
    },
    {
        "id": "kscs",
        "sectionNo": 7,
        "title": "각 문항을 읽고 평소 자신과 얼마나 일치하는지 체크해 주십시오.",
        "questionNoRange": [50, 61],
    },
    {"id": "thanks", "sectionNo": 8, "title": "참여해주셔서 감사합니다."},
]

SCALE_TITLES = {
    "profile": "인구통계",
    "kmies": "앞서 떠올린 경험에 비추어 응답해주세요.",
    "phq9": "지난 2주 동안, 아래 나열되는 증상들에 얼마나 자주 시달렸습니까?",
    "pcl5": "지난 2주 동안, 아래 나열되는 증상들에 얼마나 자주 시달렸습니까?",
    "kscs": "각 문항을 읽고 평소 자신과 얼마나 일치하는지 체크해 주십시오.",
}

SCALE_DESCRIPTIONS = {
    "phq9": "최근 2주 동안의 상태를 기준으로 응답해 주세요.",
    "pcl5": "앞서 떠올린 스트레스 경험과 관련해 응답해 주세요.",
}


def _default_intro() -> dict[str, Any]:
    return {
        "title": "리본톡 소개 및 설문",
        "subtitle": "소방안전박람회 마음 점검",
        "paragraphs": [
            "리본톡은 소방공무원 등 재난 현장에서 강한 외상 사건을 반복적으로 경험하는 분들의 트라우마 예방과 회복을 돕기 위한 공감 기반 AI 심리상담 앱입니다.",
            "리본톡은 진단이나 치료를 대신하는 의료서비스가 아니라, 언제든지 접근 가능한 심리적 지지 도구로서 추후 필요 시 전문 상담·치료로 연결되는 다리 역할을 목표로 하고 있습니다.",
        ],
        "showLogo": True,
        "showAppScreens": True,
    }


def _default_consent_sections() -> list[dict[str, Any]]:
    return [
        {
            "heading": "1. 연구 목적",
            "paragraphs": [
                "본 설문은 소방 및 재난 대응 관련 종사자의 심리적 어려움을 파악하여 회복을 돕는 AI 상담 서비스 리본톡 개발 및 학술연구의 기초자료로 활용하기 위한 것입니다.",
            ],
        },
        {
            "heading": "2. 연구대상자의 참여기간, 절차 및 방법",
            "paragraphs": [
                "본 연구는 온라인 설문 방식으로 진행됩니다. 연구대상자는 연구 설명문을 확인한 뒤 연구 참여 동의 여부를 선택합니다. 동의한 경우에만 설문 문항으로 이동하며, 설문은 1회 참여로 진행되고 예상 소요시간은 약 15~20분입니다.",
            ],
        },
        {
            "heading": "3. 연구대상자에게 예상되는 위험 및 이득",
            "paragraphs": [
                "본 연구 참여로 인한 특별한 신체적 위험은 없습니다. 다만 일부 문항은 심리적 어려움과 관련된 내용을 포함하므로 응답 중 일시적인 불편감을 느낄 수 있습니다. 불편감이 느껴질 경우 언제든지 설문을 중단할 수 있으며 이에 따른 불이익은 없습니다.",
            ],
        },
        {
            "heading": "4. 개인정보 보호에 관한 사항",
            "paragraphs": [
                "본 연구는 이름, 연락처, 주민등록번호 등 직접 식별정보를 수집하지 않습니다. 수집된 자료는 연구 목적에 한하여 사용되며, 연구 결과는 개인을 식별할 수 없는 통계자료 또는 비식별화된 형태로만 제시됩니다.",
            ],
        },
        {
            "heading": "5. 연구 참여에 따른 손실에 대한 보상",
            "paragraphs": [
                "본 연구 참여로 인한 특별한 손실이나 위험은 없습니다. 다만 설문 작성에 약 15~20분 정도가 소요될 수 있습니다.",
            ],
        },
        {
            "heading": "6. 개인정보 제공 및 보관기간에 관한 내용",
            "paragraphs": [
                "수집된 설문 자료는 비식별화하여 연구 목적에 한해 사용합니다. 자료는 접근 권한이 제한된 연구자 계정 또는 암호화된 저장공간에 보관하며, 연구 종료 후 3년간 보관한 뒤 복구가 불가능한 방식으로 삭제 또는 폐기합니다.",
            ],
        },
        {
            "heading": "7. 동의의 철회에 관한 사항",
            "paragraphs": [
                "연구 참여는 자발적이며, 언제든지 불이익 없이 중단할 수 있습니다. 제출 전에는 설문 작성을 중단하거나 창을 닫는 방식으로 참여를 철회할 수 있습니다. 제출 이후에는 특정 응답을 식별하기 어려워 개별 자료 삭제가 제한될 수 있습니다.",
            ],
        },
        {
            "heading": "8. 연구 관련 문의",
            "paragraphs": [
                "담당연구원: 최동혁 / 소속: 트래시스(주) / 이메일: trasys21@nate.com / 연락처: 062-653-5151",
            ],
        },
    ]


def _default_consent_items() -> list[dict[str, Any]]:
    return [
        {
            "key": "researchParticipationConsent",
            "label": "[필수] 연구 참여 동의",
            "description": "본인은 연구의 목적, 절차, 예상 소요시간, 예상되는 불편감, 연구 참여 중단 및 철회 가능성에 대한 설명을 확인하였으며, 자발적으로 본 연구에 참여하는 것에 동의합니다.",
            "required": True,
        },
        {
            "key": "personalDataUseConsent",
            "label": "[필수] 개인정보 수집·이용 동의",
            "description": "본인은 연구자가 연령대, 성별, 직무 관련 정보, 사건 경험 관련 정보, 설문 응답자료를 수집하고, 이를 연구 목적의 통계 분석, 학술연구 및 서비스 개선에 이용하는 것에 동의합니다.",
            "required": True,
        },
        {
            "key": "sensitiveInfoConsent",
            "label": "[필수] 민감정보 처리 동의",
            "description": "본인은 본 설문에 우울감, 자해 관련 생각, 외상 경험, 심리적 고통, 상담·병원 이용 경험 등 건강 또는 정신건강과 관련될 수 있는 문항이 포함되어 있음을 확인하였으며, 해당 정보를 연구 목적의 분석에 이용하는 것에 동의합니다.",
            "required": True,
        },
        {
            "key": "deidentifiedAiRagUseConsent",
            "label": "[필수] 비식별 자료의 AI 학습/RAG 활용 동의",
            "description": "본인은 본 설문에서 수집된 응답자료가 익명화·가명화 등 비식별 처리된 후, AI 상담 서비스 리본톡의 성능 개선, AI 학습 데이터 구축 또는 RAG 데이터 구축에 활용될 수 있음에 동의합니다.",
            "required": True,
        },
    ]


def _default_thanks() -> dict[str, Any]:
    return {
        "title": "참여해주셔서 감사합니다.",
        "paragraphs": [
            "응답이 저장되었습니다.",
            "이제 마음신호 요약을 확인할 수 있습니다.",
        ],
    }


def get_default_survey_config(questions: list[Question]) -> SurveyConfig:
    question_nos = {question.question_no for question in questions}
    if not questions or question_nos == set(range(1, 62)):
        sections = deepcopy(FINAL_61_SECTIONS)
    else:
        sections = _sections_from_current_questions(questions)

    return SurveyConfig.model_validate(
        {
            "version": SURVEY_CONFIG_VERSION,
            "intro": _default_intro(),
            "consent": {
                "title": "연구 참여 동의설명문 및 동의서",
                "sections": _default_consent_sections(),
                "items": _default_consent_items(),
            },
            "sections": sections,
            "questionOverrides": {},
            "thanks": _default_thanks(),
        }
    )


def get_admin_survey_config(db: Session, event_slug: str) -> AdminSurveyResponse:
    event = _event_or_404(db, event_slug)
    questions = QuestionRepository(db).list_by_event_id(event.id)
    config = _merged_survey_config(event, questions)
    return _admin_response(event, config, questions)


def update_intro(
    db: Session,
    event_slug: str,
    payload: SurveyIntroUpdateRequest,
    admin: AdminUser,
) -> AdminSurveyMutationResponse:
    event, questions, config = _event_questions_config(db, event_slug)
    before = config["intro"]
    config["intro"] = {
        "title": payload.title.strip(),
        "subtitle": _optional_text(payload.subtitle),
        "paragraphs": payload.paragraphs,
        "showLogo": payload.show_logo,
        "showAppScreens": payload.show_app_screens,
    }
    return _save_with_audit(
        db,
        event=event,
        questions=questions,
        config=config,
        admin=admin,
        action="survey_intro.update",
        target_type="survey_intro",
        target_id=event.id,
        before=before,
        after=config["intro"],
        reason=payload.reason,
    )


def update_consent(
    db: Session,
    event_slug: str,
    payload: SurveyConsentUpdateRequest,
    admin: AdminUser,
) -> AdminSurveyMutationResponse:
    _validate_consent_items(payload)
    event, questions, config = _event_questions_config(db, event_slug)
    before = config["consent"]
    config["consent"] = {
        "title": payload.title.strip(),
        "sections": [
            {
                "heading": section.heading.strip(),
                "paragraphs": [paragraph.strip() for paragraph in section.paragraphs],
            }
            for section in payload.sections
        ],
        "items": [
            {
                "key": item.key,
                "label": _validated_text(item.label, "label", 1, 160),
                "description": _validated_text(item.description, "description", 1, 1500),
                "required": True,
            }
            for item in payload.items
        ],
    }
    return _save_with_audit(
        db,
        event=event,
        questions=questions,
        config=config,
        admin=admin,
        action="survey_consent.update",
        target_type="survey_consent",
        target_id=event.id,
        before=before,
        after=config["consent"],
        reason=payload.reason,
    )


def update_section(
    db: Session,
    event_slug: str,
    section_id: str,
    payload: SurveySectionUpdateRequest,
    admin: AdminUser,
) -> AdminSurveyMutationResponse:
    event, questions, config = _event_questions_config(db, event_slug)
    section = _section_or_404(config, section_id)
    before = deepcopy(section)
    section["title"] = payload.title.strip()
    section["description"] = _optional_text(payload.description)
    return _save_with_audit(
        db,
        event=event,
        questions=questions,
        config=config,
        admin=admin,
        action="survey_section.update",
        target_type="survey_section",
        target_id=event.id,
        before=before,
        after=section,
        reason=payload.reason,
    )


def update_question_presentation(
    db: Session,
    event_slug: str,
    question_no: int,
    payload: SurveyQuestionPresentationUpdateRequest,
    admin: AdminUser,
) -> AdminSurveyMutationResponse:
    event, questions, config = _event_questions_config(db, event_slug)
    question = next((item for item in questions if item.question_no == question_no), None)
    if question is None:
        raise AppError(ErrorCode.BAD_REQUEST, "해당 문항을 찾을 수 없습니다.")

    overrides = config.setdefault("questionOverrides", {})
    key = str(question_no)
    before = deepcopy(overrides.get(key))

    next_override = {
        "title": _optional_text(payload.title),
        "description": _optional_text(payload.description),
    }
    next_override = {name: value for name, value in next_override.items() if value is not None}
    if next_override:
        overrides[key] = next_override
    else:
        overrides.pop(key, None)

    return _save_with_audit(
        db,
        event=event,
        questions=questions,
        config=config,
        admin=admin,
        action="survey_question_presentation.update",
        target_type="survey_question",
        target_id=question.id,
        before=before,
        after=overrides.get(key),
        reason=payload.reason,
    )


def update_thanks(
    db: Session,
    event_slug: str,
    payload: SurveyThanksUpdateRequest,
    admin: AdminUser,
) -> AdminSurveyMutationResponse:
    event, questions, config = _event_questions_config(db, event_slug)
    before = config["thanks"]
    config["thanks"] = {
        "title": payload.title.strip(),
        "paragraphs": payload.paragraphs,
    }
    return _save_with_audit(
        db,
        event=event,
        questions=questions,
        config=config,
        admin=admin,
        action="survey_thanks.update",
        target_type="survey_thanks",
        target_id=event.id,
        before=before,
        after=config["thanks"],
        reason=payload.reason,
    )


def reset_survey_config(
    db: Session,
    event_slug: str,
    admin: AdminUser,
    payload: SurveyResetRequest | None = None,
) -> AdminSurveyMutationResponse:
    event = _event_or_404(db, event_slug)
    questions = QuestionRepository(db).list_by_event_id(event.id)
    before = deepcopy((event.settings or {}).get(SURVEY_CONFIG_KEY))
    settings = dict(event.settings or {})
    settings.pop(SURVEY_CONFIG_KEY, None)
    EventRepository(db).save_settings(event, settings)
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=event.id,
        action="survey_config.reset",
        target_type="survey_config",
        target_id=event.id,
        before_value=before,
        after_value=None,
        reason=payload.reason if payload else None,
    )
    db.commit()
    db.refresh(event)
    config = _merged_survey_config(event, questions)
    return AdminSurveyMutationResponse(surveyConfig=config, auditLogCreated=True)


def get_public_survey_content(db: Session, event_slug: str) -> PublicSurveyContentResponse:
    event = _event_or_404(db, event_slug)
    if event.status != EventStatus.OPEN.value:
        raise AppError(
            ErrorCode.EVENT_NOT_OPEN,
            "공개 진입 가능한 이벤트가 아닙니다.",
            status.HTTP_403_FORBIDDEN,
            details={"status": event.status},
        )
    questions = QuestionRepository(db).list_by_event_id(event.id)
    config = _merged_survey_config(event, questions)
    return PublicSurveyContentResponse(eventSlug=event.slug, surveyConfig=config)


def merge_question_with_presentation_override(
    question: Question,
    survey_config: SurveyConfig | dict[str, Any],
) -> dict[str, Any]:
    config_dict = (
        config_to_dict(survey_config)
        if isinstance(survey_config, SurveyConfig)
        else survey_config
    )
    override = (config_dict.get("questionOverrides") or {}).get(str(question.question_no), {})
    return {
        "id": question.id,
        "questionNo": question.question_no,
        "questionKey": question.question_key,
        "scaleCode": question.scale_code,
        "questionType": question.question_type,
        "title": question.title,
        "displayTitle": override.get("title") or question.title,
        "description": question.description,
        "displayDescription": override.get("description") or question.description,
        "required": question.required,
        "optionsCount": len(question.options or []),
    }


def _sections_from_current_questions(questions: list[Question]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = [
        {"id": "intro", "sectionNo": 1, "title": "리본톡 소개 및 설문"},
        {"id": "consent", "sectionNo": 2, "title": "연구 참여 동의설명문 및 동의서"},
    ]
    groups: dict[str, list[Question]] = {}
    for question in questions:
        groups.setdefault(question.scale_code, []).append(question)

    sorted_groups = sorted(groups.items(), key=lambda item: min(question.question_no for question in item[1]))
    for index, (scale_code, scale_questions) in enumerate(sorted_groups, start=3):
        ordered = sorted(scale_questions, key=lambda question: question.question_no)
        section: dict[str, Any] = {
            "id": scale_code,
            "sectionNo": index,
            "title": SCALE_TITLES.get(scale_code, scale_code.upper()),
            "questionNoRange": [ordered[0].question_no, ordered[-1].question_no],
        }
        description = SCALE_DESCRIPTIONS.get(scale_code)
        if description:
            section["description"] = description
        sections.append(section)

    sections.append(
        {
            "id": "thanks",
            "sectionNo": len(sections) + 1,
            "title": "참여해주셔서 감사합니다.",
        }
    )
    return sections


def _event_or_404(db: Session, event_slug: str) -> Event:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return event


def _event_questions_config(db: Session, event_slug: str) -> tuple[Event, list[Question], dict[str, Any]]:
    event = _event_or_404(db, event_slug)
    questions = QuestionRepository(db).list_by_event_id(event.id)
    config = config_to_dict(_merged_survey_config(event, questions))
    return event, questions, config


def _merged_survey_config(event: Event, questions: list[Question]) -> SurveyConfig:
    default_config = config_to_dict(get_default_survey_config(questions))
    stored = (event.settings or {}).get(SURVEY_CONFIG_KEY)
    if not isinstance(stored, dict):
        return SurveyConfig.model_validate(default_config)

    merged = deepcopy(default_config)
    _merge_intro(merged, stored)
    _merge_consent(merged, stored)
    _merge_sections(merged, stored)
    _merge_question_overrides(merged, stored, {question.question_no for question in questions})
    _merge_thanks(merged, stored)
    return SurveyConfig.model_validate(merged)


def _merge_intro(merged: dict[str, Any], stored: dict[str, Any]) -> None:
    source = stored.get("intro")
    if not isinstance(source, dict):
        return
    for key in ("title", "subtitle", "paragraphs", "showLogo", "showAppScreens"):
        if key in source:
            merged["intro"][key] = source[key]


def _merge_consent(merged: dict[str, Any], stored: dict[str, Any]) -> None:
    source = stored.get("consent")
    if not isinstance(source, dict):
        return
    if isinstance(source.get("title"), str) and source["title"].strip():
        merged["consent"]["title"] = source["title"]
    if isinstance(source.get("sections"), list):
        merged["consent"]["sections"] = source["sections"]

    stored_items = source.get("items")
    if not isinstance(stored_items, list):
        return
    by_key = {item.get("key"): item for item in stored_items if isinstance(item, dict)}
    next_items: list[dict[str, Any]] = []
    for default_item in merged["consent"]["items"]:
        stored_item = by_key.get(default_item["key"])
        if not isinstance(stored_item, dict):
            next_items.append(default_item)
            continue
        next_items.append(
            {
                "key": default_item["key"],
                "label": stored_item.get("label") or default_item["label"],
                "description": stored_item.get("description") or default_item["description"],
                "required": True,
            }
        )
    merged["consent"]["items"] = next_items


def _merge_sections(merged: dict[str, Any], stored: dict[str, Any]) -> None:
    stored_sections = stored.get("sections")
    if not isinstance(stored_sections, list):
        return
    by_id = {section.get("id"): section for section in stored_sections if isinstance(section, dict)}
    for section in merged["sections"]:
        stored_section = by_id.get(section["id"])
        if not isinstance(stored_section, dict):
            continue
        if isinstance(stored_section.get("title"), str) and stored_section["title"].strip():
            section["title"] = stored_section["title"]
        if "description" in stored_section:
            section["description"] = _optional_text(stored_section.get("description"))


def _merge_question_overrides(
    merged: dict[str, Any],
    stored: dict[str, Any],
    known_question_nos: set[int],
) -> None:
    source = stored.get("questionOverrides")
    if not isinstance(source, dict):
        return
    overrides: dict[str, dict[str, str]] = {}
    for raw_key, value in source.items():
        try:
            question_no = int(raw_key)
        except (TypeError, ValueError):
            continue
        if known_question_nos and question_no not in known_question_nos:
            continue
        if not isinstance(value, dict):
            continue
        override = {
            key: text
            for key in ("title", "description")
            if isinstance((text := _optional_text(value.get(key))), str)
        }
        if override:
            overrides[str(question_no)] = override
    merged["questionOverrides"] = overrides


def _merge_thanks(merged: dict[str, Any], stored: dict[str, Any]) -> None:
    source = stored.get("thanks")
    if not isinstance(source, dict):
        return
    for key in ("title", "paragraphs"):
        if key in source:
            merged["thanks"][key] = source[key]


def _admin_response(event: Event, config: SurveyConfig, questions: list[Question]) -> AdminSurveyResponse:
    config_dict = config_to_dict(config)
    return AdminSurveyResponse(
        event=AdminSurveyEvent(
            slug=event.slug,
            name=event.name,
            status=event.status,
            consentVersion=event.consent_version,
        ),
        surveyConfig=config,
        sectionSummaries=_section_summaries(config_dict, questions),
        questionsBySection=_questions_by_section(config_dict, questions),
    )


def _section_summaries(config: dict[str, Any], questions: list[Question]) -> list[SurveySectionSummary]:
    summaries: list[SurveySectionSummary] = []
    for section in config["sections"]:
        section_questions = _questions_for_section(questions, section)
        summaries.append(
            SurveySectionSummary(
                id=section["id"],
                sectionNo=section["sectionNo"],
                title=section["title"],
                description=section.get("description"),
                questionNoRange=section.get("questionNoRange"),
                questionCount=len(section_questions),
                requiredCount=len([question for question in section_questions if question.required]),
            )
        )
    return summaries


def _questions_by_section(config: dict[str, Any], questions: list[Question]) -> list[AdminSurveyQuestionsBySection]:
    groups: list[AdminSurveyQuestionsBySection] = []
    for section in config["sections"]:
        if not section.get("questionNoRange"):
            continue
        section_questions = _questions_for_section(questions, section)
        groups.append(
            AdminSurveyQuestionsBySection(
                sectionId=section["id"],
                sectionNo=section["sectionNo"],
                title=section["title"],
                questions=[
                    AdminSurveyQuestionItem(
                        **merge_question_with_presentation_override(question, config),
                        editable=AdminSurveyQuestionEditable(),
                    )
                    for question in section_questions
                ],
            )
        )
    return groups


def _questions_for_section(questions: list[Question], section: dict[str, Any]) -> list[Question]:
    question_range = section.get("questionNoRange")
    if not question_range:
        return []
    start, end = question_range
    return [
        question
        for question in sorted(questions, key=lambda item: (item.display_order, item.question_no))
        if start <= question.question_no <= end
    ]


def _section_or_404(config: dict[str, Any], section_id: str) -> dict[str, Any]:
    section = next((item for item in config["sections"] if item["id"] == section_id), None)
    if section is None:
        raise AppError(ErrorCode.BAD_REQUEST, "해당 섹션을 찾을 수 없습니다.")
    return section


def _save_with_audit(
    db: Session,
    *,
    event: Event,
    questions: list[Question],
    config: dict[str, Any],
    admin: AdminUser,
    action: str,
    target_type: str,
    target_id,
    before: Any,
    after: Any,
    reason: str | None,
) -> AdminSurveyMutationResponse:
    settings = dict(event.settings or {})
    settings[SURVEY_CONFIG_KEY] = config
    EventRepository(db).save_settings(event, settings)
    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=event.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before_value=before if isinstance(before, dict) else {"value": before},
        after_value=after if isinstance(after, dict) else {"value": after},
        reason=reason,
    )
    db.commit()
    db.refresh(event)
    return AdminSurveyMutationResponse(
        surveyConfig=_merged_survey_config(event, questions),
        auditLogCreated=True,
    )


def _validate_consent_items(payload: SurveyConsentUpdateRequest) -> None:
    keys = [item.key for item in payload.items]
    if set(keys) != set(REQUIRED_CONSENT_ITEM_KEYS) or len(keys) != len(REQUIRED_CONSENT_ITEM_KEYS):
        raise AppError(ErrorCode.BAD_REQUEST, "동의 항목 key는 변경할 수 없습니다.")
    for item in payload.items:
        if item.required is not True:
            raise AppError(ErrorCode.BAD_REQUEST, "필수 동의 항목은 required=true를 유지해야 합니다.")


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _validated_text(value: str, name: str, min_length: int, max_length: int) -> str:
    stripped = value.strip()
    if len(stripped) < min_length or len(stripped) > max_length:
        raise AppError(ErrorCode.BAD_REQUEST, f"{name} 길이가 올바르지 않습니다.")
    return stripped
