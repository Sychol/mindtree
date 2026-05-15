from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AdminResponseColumn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str
    label: str
    type: str
    question_no: int | None = Field(default=None, alias="questionNo")
    question_key: str | None = Field(default=None, alias="questionKey")
    scale_code: str | None = Field(default=None, alias="scaleCode")


class AdminResponsesListResponse(BaseModel):
    columns: list[AdminResponseColumn]
    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int


class AdminResponsesColumnsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    summary_columns: list[AdminResponseColumn] = Field(alias="summaryColumns")
    question_columns: list[AdminResponseColumn] = Field(alias="questionColumns")
    score_columns: list[AdminResponseColumn] = Field(alias="scoreColumns")
    risk_columns: list[AdminResponseColumn] = Field(alias="riskColumns")


class AdminResponsesExportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    format: Literal["wide", "long"] = "wide"
    include_scores: bool = Field(default=True, alias="includeScores")
    include_risk_flags: bool = Field(default=False, alias="includeRiskFlags")
    include_completion_status: bool = Field(default=True, alias="includeCompletionStatus")
    status: str = "all"
    completed_only: bool = Field(default=False, alias="completedOnly")
    created_from: datetime | None = Field(default=None, alias="createdFrom")
    created_to: datetime | None = Field(default=None, alias="createdTo")
    reason: str = Field(min_length=1, max_length=500)
