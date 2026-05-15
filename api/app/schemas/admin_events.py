from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AdminDashboardEvent(BaseModel):
    slug: str
    status: str


class AdminDashboardMetrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    session_count: int = Field(alias="sessionCount")
    completed_count: int = Field(alias="completedCount")
    card_count: int = Field(alias="cardCount")
    reply_count: int = Field(alias="replyCount")
    review_count: int = Field(alias="reviewCount")
    keyword_pending_count: int = Field(alias="keywordPendingCount")
    keyword_failed_count: int = Field(alias="keywordFailedCount")
    completion_issued_count: int = Field(alias="completionIssuedCount")
    redeemed_count: int = Field(alias="redeemedCount")


class AdminDashboardResponse(BaseModel):
    event: AdminDashboardEvent
    metrics: AdminDashboardMetrics
