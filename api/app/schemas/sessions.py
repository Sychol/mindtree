from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateOrResumeSessionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resume_token: str | None = Field(default=None, alias="resumeToken")
    client_meta: dict[str, Any] = Field(default_factory=dict, alias="clientMeta")


class SessionInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    event_slug: str = Field(alias="eventSlug")
    status: str
    last_step: str | None = Field(default=None, alias="lastStep")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class CreateOrResumeSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session: SessionInfo
    resume_token: str = Field(alias="resumeToken")


class SessionProgress(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    consent_accepted: bool = Field(alias="consentAccepted")
    questions_completed: bool = Field(alias="questionsCompleted")
    summary_viewed: bool = Field(alias="summaryViewed")
    mind_card_count: int = Field(alias="mindCardCount")
    selected_card: bool = Field(alias="selectedCard")
    reply_created: bool = Field(alias="replyCreated")
    completion_code_issued: bool = Field(alias="completionCodeIssued")


class SessionResponse(BaseModel):
    session: SessionInfo
    progress: SessionProgress


class ConsentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    consent_version: str = Field(alias="consentVersion")
    accepted_items: dict[str, bool] = Field(alias="acceptedItems")


class ConsentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_status: str = Field(alias="sessionStatus")
    accepted_at: datetime = Field(alias="acceptedAt")
