from pydantic import BaseModel, ConfigDict, Field


class PublicEventSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    display_enabled: bool = Field(alias="displayEnabled")
    max_mind_cards_per_session: int = Field(alias="maxMindCardsPerSession")
    help_notice_enabled: bool = Field(alias="helpNoticeEnabled")


class PublicEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    slug: str
    name: str
    status: str
    description: str | None
    consent_version: str = Field(alias="consentVersion")
    settings: PublicEventSettings


class PublicEventNotices(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    not_diagnosis: str = Field(alias="notDiagnosis")
    anonymous_keyword_display: str = Field(alias="anonymousKeywordDisplay")


class PublicEventResponse(BaseModel):
    event: PublicEvent
    notices: PublicEventNotices
