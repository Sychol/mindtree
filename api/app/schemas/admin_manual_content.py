from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import PublicStatus, ReplyType, SafetyStatus
from app.schemas.cards import KeywordJobPayload


class _ManualContentBaseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str
    origin_tag: str | None = Field(default=None, alias="originTag")
    public_status: str = Field(default=PublicStatus.PUBLIC.value, alias="publicStatus")
    create_keyword_job: bool = Field(default=True, alias="createKeywordJob")
    reason: str | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        trimmed = value.strip()
        if not 1 <= len(trimmed) <= 300:
            raise ValueError("content must be 1-300 characters")
        return trimmed

    @field_validator("origin_tag")
    @classmethod
    def validate_origin_tag(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 30:
            raise ValueError("originTag must be at most 30 characters")
        return trimmed

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 500:
            raise ValueError("reason must be at most 500 characters")
        return trimmed


class AdminManualCardCreateRequest(_ManualContentBaseRequest):
    prompt_type: str = Field(alias="promptType")


class AdminManualReplyCreateRequest(_ManualContentBaseRequest):
    reply_type: str = Field(default=ReplyType.COMFORT.value, alias="replyType")
    target_card_id: UUID | None = Field(default=None, alias="targetCardId")


class AdminManualContentStatusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if len(trimmed) > 500:
            raise ValueError("reason must be at most 500 characters")
        return trimmed


class AdminManualCardPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    event_slug: str | None = Field(default=None, alias="eventSlug")
    session_id: UUID | None = Field(default=None, alias="sessionId")
    prompt_type: str | None = Field(default=None, alias="promptType")
    content_raw: str | None = Field(default=None, alias="contentRaw")
    content_redacted: str | None = Field(default=None, alias="contentRedacted")
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    origin: str
    origin_tag: str | None = Field(default=None, alias="originTag")
    created_by_admin_id: UUID | None = Field(default=None, alias="createdByAdminId")
    created_at: datetime | None = Field(default=None, alias="createdAt")


class AdminManualReplyPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    event_slug: str | None = Field(default=None, alias="eventSlug")
    session_id: UUID | None = Field(default=None, alias="sessionId")
    target_card_id: UUID | None = Field(default=None, alias="targetCardId")
    reply_type: str | None = Field(default=None, alias="replyType")
    content_raw: str | None = Field(default=None, alias="contentRaw")
    content_redacted: str | None = Field(default=None, alias="contentRedacted")
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    origin: str
    origin_tag: str | None = Field(default=None, alias="originTag")
    created_by_admin_id: UUID | None = Field(default=None, alias="createdByAdminId")
    created_at: datetime | None = Field(default=None, alias="createdAt")


class AdminManualCardCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card: AdminManualCardPayload
    keyword_job: KeywordJobPayload | None = Field(default=None, alias="keywordJob")
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminManualReplyCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reply: AdminManualReplyPayload
    keyword_job: KeywordJobPayload | None = Field(default=None, alias="keywordJob")
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminManualCardStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card: AdminManualCardPayload
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminManualReplyStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reply: AdminManualReplyPayload
    audit_log_created: bool = Field(alias="auditLogCreated")
