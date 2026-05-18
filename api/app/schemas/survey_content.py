from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.admin_survey import SurveyConfig


class PublicSurveyContentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_slug: str = Field(alias="eventSlug")
    survey_config: SurveyConfig = Field(alias="surveyConfig")
