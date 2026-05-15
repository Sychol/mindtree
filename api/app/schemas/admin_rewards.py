from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminCompletionCodePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    status: str
    issued_at: datetime = Field(alias="issuedAt")
    redeemed_at: datetime | None = Field(default=None, alias="redeemedAt")


class AdminCompletionCodeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    completion_code: AdminCompletionCodePayload = Field(alias="completionCode")


class AdminCompletionCodeRedeemRequest(BaseModel):
    notes: str | None = None


class AdminCompletionCodeRedeemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    completion_code: AdminCompletionCodePayload = Field(alias="completionCode")
    audit_log_created: bool = Field(alias="auditLogCreated")


AdminRedeemCompletionCodeRequest = AdminCompletionCodeRedeemRequest
AdminRedeemCompletionCodeResponse = AdminCompletionCodeRedeemResponse
