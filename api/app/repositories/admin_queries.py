from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, KeywordJobStatus, PublicStatus, SafetyStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.models.session import Session as EventSession


class AdminQueryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _count(self, statement) -> int:
        return int(self.db.execute(statement).scalar_one() or 0)

    def count_sessions(self, event_id: UUID) -> int:
        return self._count(select(func.count(EventSession.id)).where(EventSession.event_id == event_id))

    def count_completed_sessions(self, event_id: UUID) -> int:
        return self._count(
            select(func.count(EventSession.id)).where(
                EventSession.event_id == event_id,
                EventSession.status == "completed",
            )
        )

    def count_cards(self, event_id: UUID) -> int:
        return self._count(select(func.count(MindCard.id)).where(MindCard.event_id == event_id))

    def count_replies(self, event_id: UUID) -> int:
        return self._count(select(func.count(Reply.id)).where(Reply.event_id == event_id))

    def count_review_items(self, event_id: UUID) -> int:
        card_count = self._count(
            select(func.count(MindCard.id)).where(
                MindCard.event_id == event_id,
                (MindCard.safety_status == SafetyStatus.REVIEW.value)
                | (MindCard.public_status == PublicStatus.PENDING.value),
            )
        )
        reply_count = self._count(
            select(func.count(Reply.id)).where(
                Reply.event_id == event_id,
                (Reply.safety_status == SafetyStatus.REVIEW.value)
                | (Reply.public_status == PublicStatus.PENDING.value),
            )
        )
        return card_count + reply_count

    def count_keyword_jobs(self, event_id: UUID, status: str) -> int:
        return self._count(
            select(func.count(KeywordJob.id)).where(
                KeywordJob.event_id == event_id,
                KeywordJob.status == status,
            )
        )

    def count_completion_codes(self, event_id: UUID) -> int:
        return self._count(select(func.count(CompletionCode.id)).where(CompletionCode.event_id == event_id))

    def count_redeemed_codes(self, event_id: UUID) -> int:
        return self._count(
            select(func.count(CompletionCode.id)).where(
                CompletionCode.event_id == event_id,
                CompletionCode.status == CompletionCodeStatus.REDEEMED.value,
            )
        )

    def dashboard_metrics(self, event_id: UUID) -> dict[str, int]:
        return {
            "sessionCount": self.count_sessions(event_id),
            "completedCount": self.count_completed_sessions(event_id),
            "cardCount": self.count_cards(event_id),
            "replyCount": self.count_replies(event_id),
            "reviewCount": self.count_review_items(event_id),
            "keywordPendingCount": self.count_keyword_jobs(event_id, KeywordJobStatus.PENDING.value),
            "keywordFailedCount": self.count_keyword_jobs(event_id, KeywordJobStatus.FAILED.value),
            "completionIssuedCount": self.count_completion_codes(event_id),
            "redeemedCount": self.count_redeemed_codes(event_id),
        }
