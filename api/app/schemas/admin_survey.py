from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SurveyIntroConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    subtitle: str | None = None
    paragraphs: list[str] = Field(default_factory=list)
    show_logo: bool = Field(default=True, alias="showLogo")
    show_app_screens: bool = Field(default=True, alias="showAppScreens")


class SurveyConsentSection(BaseModel):
    heading: str
    paragraphs: list[str] = Field(default_factory=list)


class SurveyConsentItem(BaseModel):
    key: str
    label: str
    description: str
    required: bool = True


class SurveyConsentConfig(BaseModel):
    title: str
    sections: list[SurveyConsentSection] = Field(default_factory=list)
    items: list[SurveyConsentItem] = Field(default_factory=list)


class SurveySectionConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    section_no: int = Field(alias="sectionNo")
    title: str
    description: str | None = None
    question_no_range: tuple[int, int] | None = Field(default=None, alias="questionNoRange")


class SurveyQuestionOverride(BaseModel):
    title: str | None = None
    description: str | None = None


class SurveyThanksConfig(BaseModel):
    title: str
    paragraphs: list[str] = Field(default_factory=list)


class SurveyConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version: str = "v1"
    intro: SurveyIntroConfig
    consent: SurveyConsentConfig
    sections: list[SurveySectionConfig] = Field(default_factory=list)
    question_overrides: dict[str, SurveyQuestionOverride] = Field(
        default_factory=dict,
        alias="questionOverrides",
    )
    thanks: SurveyThanksConfig


class AdminSurveyEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slug: str
    name: str
    status: str
    consent_version: str = Field(alias="consentVersion")


class SurveySectionSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    section_no: int = Field(alias="sectionNo")
    title: str
    description: str | None = None
    question_no_range: tuple[int, int] | None = Field(default=None, alias="questionNoRange")
    question_count: int = Field(alias="questionCount")
    required_count: int = Field(alias="requiredCount")


class AdminSurveyQuestionEditable(BaseModel):
    title: bool = True
    description: bool = True
    question_no: bool = Field(default=False, alias="questionNo")
    question_key: bool = Field(default=False, alias="questionKey")
    scale_code: bool = Field(default=False, alias="scaleCode")
    question_type: bool = Field(default=False, alias="questionType")
    score_map: bool = Field(default=False, alias="scoreMap")
    options: bool = False
    required: bool = False


class AdminSurveyQuestionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    question_no: int = Field(alias="questionNo")
    question_key: str = Field(alias="questionKey")
    scale_code: str = Field(alias="scaleCode")
    question_type: str = Field(alias="questionType")
    title: str
    display_title: str = Field(alias="displayTitle")
    description: str | None = None
    display_description: str | None = Field(default=None, alias="displayDescription")
    required: bool
    options_count: int = Field(alias="optionsCount")
    editable: AdminSurveyQuestionEditable


class AdminSurveyQuestionsBySection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    section_id: str = Field(alias="sectionId")
    section_no: int = Field(alias="sectionNo")
    title: str
    questions: list[AdminSurveyQuestionItem]


class AdminSurveyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: AdminSurveyEvent
    survey_config: SurveyConfig = Field(alias="surveyConfig")
    section_summaries: list[SurveySectionSummary] = Field(alias="sectionSummaries")
    questions_by_section: list[AdminSurveyQuestionsBySection] = Field(alias="questionsBySection")


class SurveyReasonMixin(BaseModel):
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class SurveyIntroUpdateRequest(SurveyReasonMixin):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    subtitle: str | None = Field(default=None, max_length=120)
    paragraphs: list[str] = Field(default_factory=list, max_length=10)
    show_logo: bool = Field(default=True, alias="showLogo")
    show_app_screens: bool = Field(default=True, alias="showAppScreens")

    @field_validator("paragraphs")
    @classmethod
    def validate_paragraphs(cls, value: list[str]) -> list[str]:
        return [_trim_text(item, max_length=1000, field_name="paragraph") for item in value]


class SurveyConsentUpdateRequest(SurveyReasonMixin):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    sections: list[SurveyConsentSection] = Field(default_factory=list, max_length=20)
    items: list[SurveyConsentItem]

    @field_validator("sections")
    @classmethod
    def validate_sections(cls, value: list[SurveyConsentSection]) -> list[SurveyConsentSection]:
        for section in value:
            section.heading = _trim_text(section.heading, min_length=1, max_length=100, field_name="heading")
            section.paragraphs = [
                _trim_text(item, max_length=1500, field_name="paragraph") for item in section.paragraphs
            ]
        return value


class SurveySectionUpdateRequest(SurveyReasonMixin):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)


class SurveyQuestionPresentationUpdateRequest(SurveyReasonMixin):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=1000)


class SurveyThanksUpdateRequest(SurveyReasonMixin):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    paragraphs: list[str] = Field(default_factory=list, max_length=10)

    @field_validator("paragraphs")
    @classmethod
    def validate_paragraphs(cls, value: list[str]) -> list[str]:
        return [_trim_text(item, max_length=1000, field_name="paragraph") for item in value]


class SurveyResetRequest(SurveyReasonMixin):
    model_config = ConfigDict(extra="forbid")


class AdminSurveyMutationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    survey_config: SurveyConfig = Field(alias="surveyConfig")
    audit_log_created: bool = Field(default=True, alias="auditLogCreated")


def _trim_text(
    value: str,
    *,
    field_name: str,
    min_length: int = 0,
    max_length: int,
) -> str:
    stripped = value.strip()
    if len(stripped) < min_length:
        raise ValueError(f"{field_name} is too short.")
    if len(stripped) > max_length:
        raise ValueError(f"{field_name} is too long.")
    return stripped


def config_to_dict(config: SurveyConfig) -> dict[str, Any]:
    return config.model_dump(by_alias=True, mode="json")
