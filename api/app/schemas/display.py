from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DisplayKeyword(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    weight: float
    category: str | None = None
    display_part: str | None = Field(default=None, alias="displayPart")


class DisplaySnapshotResponse(BaseModel):
    eventSlug: str
    participantCount: int
    completedCount: int
    topMindKeywords: list[DisplayKeyword]
    topSupportKeywords: list[DisplayKeyword]
    cloudKeywords: list[DisplayKeyword]
    generatedAt: datetime
