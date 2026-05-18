from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminKeywordItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    keyword_text: str = Field(alias="keywordText")
    normalized_keyword: str = Field(alias="normalizedKeyword")
    category: str
    weight: float
    status: str
    extraction_method: str = Field(alias="extractionMethod")
    source_type: str = Field(alias="sourceType")
    source_id: UUID | None = Field(alias="sourceId")
    origin: str
    origin_tag: str | None = Field(default=None, alias="originTag")
    created_by_admin_id: UUID | None = Field(default=None, alias="createdByAdminId")
    created_at: datetime = Field(alias="createdAt")


class AdminKeywordListResponse(BaseModel):
    items: list[AdminKeywordItem]
    total: int


class AdminKeywordUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    normalized_keyword: str | None = Field(default=None, alias="normalizedKeyword")
    category: str | None = None
    status: str | None = None
    reason: str | None = None


class AdminKeywordUpdateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keyword: AdminKeywordItem
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminManualKeywordCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keyword_text: str = Field(alias="keywordText")
    normalized_keyword: str | None = Field(default=None, alias="normalizedKeyword")
    category: str
    weight: float = Field(default=3, ge=1, le=50)
    status: str = "active"
    origin_tag: str | None = Field(default=None, alias="originTag")
    reason: str | None = None

    @field_validator("keyword_text")
    @classmethod
    def validate_keyword_text(cls, value: str) -> str:
        trimmed = value.strip()
        if not 1 <= len(trimmed) <= 40:
            raise ValueError("keywordText must be 1-40 characters")
        return trimmed

    @field_validator("normalized_keyword")
    @classmethod
    def validate_normalized_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not 1 <= len(trimmed) <= 40:
            raise ValueError("normalizedKeyword must be 1-40 characters")
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


class AdminManualKeywordStatusRequest(BaseModel):
    status: str
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


class AdminManualKeywordCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keyword: AdminKeywordItem
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminManualKeywordStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keyword: AdminKeywordItem
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminKeywordJobItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    source_type: str = Field(alias="sourceType")
    source_id: UUID = Field(alias="sourceId")
    status: str
    attempts: int
    max_attempts: int = Field(alias="maxAttempts")
    fallback_used: bool = Field(alias="fallbackUsed")
    provider: str | None = None
    error_message: str | None = Field(default=None, alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime | None = Field(default=None, alias="updatedAt")


class AdminKeywordJobListResponse(BaseModel):
    items: list[AdminKeywordJobItem]
    total: int


class AdminKeywordJobRetryRequest(BaseModel):
    reason: str | None = None


class AdminKeywordJobRetryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job: AdminKeywordJobItem
    audit_log_created: bool = Field(alias="auditLogCreated")
