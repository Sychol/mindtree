from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.cards import KeywordJobPayload


class CreateReplyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target_card_id: UUID = Field(alias="targetCardId")
    reply_type: str = Field(alias="replyType")
    content: str


class ReplyPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    reply_type: str = Field(alias="replyType")
    safety_status: str = Field(alias="safetyStatus")
    public_status: str = Field(alias="publicStatus")


class CompletionPayload(BaseModel):
    eligible: bool
    code: str | None = None


class CreateReplyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reply: ReplyPayload
    keyword_job: KeywordJobPayload | None = Field(default=None, alias="keywordJob")
    completion: CompletionPayload
    session_status: str = Field(alias="sessionStatus")
