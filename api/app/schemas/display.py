from datetime import datetime

from pydantic import BaseModel


class DisplayKeyword(BaseModel):
    text: str
    weight: float
    category: str | None = None


class DisplaySnapshotResponse(BaseModel):
    eventSlug: str
    participantCount: int
    completedCount: int
    topMindKeywords: list[DisplayKeyword]
    topSupportKeywords: list[DisplayKeyword]
    cloudKeywords: list[DisplayKeyword]
    generatedAt: datetime
