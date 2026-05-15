from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompletionCodePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    status: str
    issued_at: datetime = Field(alias="issuedAt")


class CompletionCodeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    completion_code: CompletionCodePayload = Field(alias="completionCode")
