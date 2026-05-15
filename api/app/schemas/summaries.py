from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SummaryPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    final_text: str = Field(alias="finalText")
    generation_mode: str = Field(alias="generationMode")
    help_notice_required: bool = Field(alias="helpNoticeRequired")
    signals: list[str] = Field(default_factory=list)
    recommended_action: str | None = Field(default=None, alias="recommendedAction")
    is_diagnosis: bool = Field(default=False, alias="isDiagnosis")


class RiskNoticePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    show_help_notice: bool = Field(alias="showHelpNotice")
    text: str | None = None


class SummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary: SummaryPayload
    risk_notice: RiskNoticePayload = Field(alias="riskNotice")


class SummaryViewedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_status: str = Field(alias="sessionStatus")
    viewed_at: datetime = Field(alias="viewedAt")
