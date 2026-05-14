from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuestionItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    question_no: int = Field(alias="questionNo")
    scale_code: str = Field(alias="scaleCode")
    question_key: str = Field(alias="questionKey")
    title: str
    description: str | None
    question_type: str = Field(alias="questionType")
    required: bool
    display_order: int = Field(alias="displayOrder")
    options: list[dict[str, Any]]


class QuestionsResponse(BaseModel):
    questions: list[QuestionItem]
