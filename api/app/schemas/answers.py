from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnswerInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_id: UUID = Field(alias="questionId")
    answer_value: Any = Field(alias="answerValue")


class BulkAnswerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    answers: list[AnswerInput]
    client_progress: dict[str, Any] = Field(default_factory=dict, alias="clientProgress")


class ScaleScoreSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scale_code: str = Field(alias="scaleCode")
    raw_score: float = Field(alias="rawScore")
    severity_level: str | None = Field(alias="severityLevel")


class RiskFlagsSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    phq9_item9_positive: bool = Field(alias="phq9Item9Positive")
    crisis_expression_detected: bool = Field(alias="crisisExpressionDetected")
    trauma_high_signal: bool = Field(alias="traumaHighSignal")
    moral_injury_high_signal: bool = Field(alias="moralInjuryHighSignal")
    public_restriction: bool = Field(alias="publicRestriction")
    help_notice_required: bool = Field(alias="helpNoticeRequired")


class BulkAnswerScoringResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    calculated: bool
    scale_scores: list[ScaleScoreSummary] = Field(alias="scaleScores")
    risk_flags: RiskFlagsSummary | None = Field(default=None, alias="riskFlags")


class BulkAnswerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    saved_count: int = Field(alias="savedCount")
    missing_question_nos: list[int] = Field(alias="missingQuestionNos")
    session_status: str = Field(alias="sessionStatus")
    scoring: BulkAnswerScoringResponse
