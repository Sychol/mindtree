from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    source_id: UUID = Field(alias="sourceId")
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
