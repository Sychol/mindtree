from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    email: str
    display_name: str = Field(alias="displayName")
    role: str


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="bearer", alias="tokenType")
    admin: AdminPayload


class AdminMeResponse(BaseModel):
    admin: AdminPayload
