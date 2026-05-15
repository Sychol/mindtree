from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminRiskFlagsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    phq9_item9_positive: bool = Field(default=False, alias="phq9Item9Positive")
    crisis_expression_detected: bool = Field(default=False, alias="crisisExpressionDetected")
    trauma_high_signal: bool = Field(default=False, alias="traumaHighSignal")
    moral_injury_high_signal: bool = Field(default=False, alias="moralInjuryHighSignal")
    public_restriction: bool = Field(default=False, alias="publicRestriction")
    help_notice_required: bool = Field(default=False, alias="helpNoticeRequired")


class AdminCardReviewItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    content_raw: str = Field(alias="contentRaw")
    content_redacted: str | None = Field(default=None, alias="contentRedacted")
    prompt_type: str = Field(alias="promptType")
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    moderation_reason: str | None = Field(default=None, alias="moderationReason")
    risk_flags: AdminRiskFlagsPayload = Field(alias="riskFlags")
    created_at: datetime = Field(alias="createdAt")


class AdminReplyReviewItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    content_raw: str = Field(alias="contentRaw")
    content_redacted: str | None = Field(default=None, alias="contentRedacted")
    reply_type: str = Field(alias="replyType")
    target_card_id: UUID = Field(alias="targetCardId")
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    moderation_reason: str | None = Field(default=None, alias="moderationReason")
    risk_flags: AdminRiskFlagsPayload = Field(alias="riskFlags")
    created_at: datetime = Field(alias="createdAt")


class AdminCardReviewListResponse(BaseModel):
    items: list[AdminCardReviewItem]
    total: int


class AdminReplyReviewListResponse(BaseModel):
    items: list[AdminReplyReviewItem]
    total: int


class AdminReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    content_redacted: str | None = Field(default=None, alias="contentRedacted")
    reason: str | None = None


class AdminReviewedSourcePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")
    content_redacted: str | None = Field(default=None, alias="contentRedacted")


class AdminCardReviewPayload(AdminReviewedSourcePayload):
    pass


class AdminReplyReviewPayload(AdminReviewedSourcePayload):
    pass


class AdminCardReviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    card: AdminCardReviewPayload
    audit_log_created: bool = Field(alias="auditLogCreated")


class AdminReplyReviewResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reply: AdminReplyReviewPayload
    audit_log_created: bool = Field(alias="auditLogCreated")


AdminCardListResponse = AdminCardReviewListResponse
AdminReplyListResponse = AdminReplyReviewListResponse
