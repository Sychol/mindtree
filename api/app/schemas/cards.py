from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateMindCardRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prompt_type: str = Field(alias="promptType")
    content: str


class MindCardPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    prompt_type: str = Field(alias="promptType")
    content: str
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    created_at: datetime | None = Field(default=None, alias="createdAt")


class KeywordJobPayload(BaseModel):
    id: UUID
    status: str


class CreateMindCardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card: MindCardPayload
    keyword_job: KeywordJobPayload | None = Field(default=None, alias="keywordJob")
    session_status: str = Field(alias="sessionStatus")


class MyMindCardsResponse(BaseModel):
    cards: list[MindCardPayload]


class PublicMindCardPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    prompt_type: str = Field(alias="promptType")
    content: str
    created_at: datetime = Field(alias="createdAt")


class PublicMindCardsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cards: list[PublicMindCardPayload]
    fallback_used: bool = Field(alias="fallbackUsed")
    message: str | None = None


class SelectCardRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    selected_card_id: UUID = Field(alias="selectedCardId")


class SelectCardResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    selected_card_id: UUID = Field(alias="selectedCardId")
    selected_at: datetime = Field(alias="selectedAt")
