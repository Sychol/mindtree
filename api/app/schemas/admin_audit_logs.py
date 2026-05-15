from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminAuditLogItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    admin_user_id: UUID | None = Field(default=None, alias="adminUserId")
    action: str
    target_type: str = Field(alias="targetType")
    target_id: UUID | None = Field(default=None, alias="targetId")
    reason: str | None = None
    created_at: datetime = Field(alias="createdAt")


class AdminAuditLogListResponse(BaseModel):
    items: list[AdminAuditLogItem]
    total: int
