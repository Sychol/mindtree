from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, distinct, func, or_, select, union_all
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.enums import (
    CompletionCodeStatus,
    KeywordSourceType,
    KeywordStatus,
    PublicStatus,
    SafetyStatus,
)
from app.models.event import Event
from app.models.keyword import Keyword
from app.models.reply import Reply
from app.models.risk import RiskFlag
from app.models.session import Session as EventSession


@dataclass(frozen=True)
class DisplayKeywordRow:
    text: str
    category: str
    weight: Decimal


class DisplayRepository:
    def __init__(self, db: SQLAlchemySession) -> None:
        self.db = db

    def get_event_by_slug(self, event_slug: str) -> Event | None:
        statement = select(Event).where(Event.slug == event_slug)
        return self.db.execute(statement).scalar_one_or_none()

    def count_event_sessions(self, event_id: UUID) -> int:
        statement = select(func.count(EventSession.id)).where(EventSession.event_id == event_id)
        return int(self.db.execute(statement).scalar_one() or 0)

    def count_completed_sessions(self, event_id: UUID) -> int:
        statement = select(func.count(distinct(CompletionCode.session_id))).where(
            CompletionCode.event_id == event_id,
            CompletionCode.status.in_(
                [
                    CompletionCodeStatus.ISSUED.value,
                    CompletionCodeStatus.REDEEMED.value,
                ]
            ),
        )
        return int(self.db.execute(statement).scalar_one() or 0)

    def list_display_keyword_rows(self, event_id: UUID) -> list[DisplayKeywordRow]:
        risk_allows_card = (
            or_(RiskFlag.id.is_(None), RiskFlag.public_restriction.is_(False)),
            or_(RiskFlag.id.is_(None), RiskFlag.crisis_expression_detected.is_(False)),
        )
        risk_allows_reply = (
            or_(RiskFlag.id.is_(None), RiskFlag.public_restriction.is_(False)),
            or_(RiskFlag.id.is_(None), RiskFlag.crisis_expression_detected.is_(False)),
        )

        card_keywords = (
            select(
                Keyword.normalized_keyword.label("text"),
                Keyword.category.label("category"),
                Keyword.weight.label("weight"),
            )
            .select_from(Keyword)
            .join(
                MindCard,
                and_(
                    Keyword.source_type == KeywordSourceType.MIND_CARD.value,
                    Keyword.source_id == MindCard.id,
                    MindCard.event_id == event_id,
                ),
            )
            .outerjoin(RiskFlag, MindCard.session_id == RiskFlag.session_id)
            .where(
                Keyword.event_id == event_id,
                Keyword.status == KeywordStatus.ACTIVE.value,
                MindCard.safety_status == SafetyStatus.SAFE.value,
                MindCard.public_status == PublicStatus.PUBLIC.value,
                *risk_allows_card,
            )
        )

        reply_keywords = (
            select(
                Keyword.normalized_keyword.label("text"),
                Keyword.category.label("category"),
                Keyword.weight.label("weight"),
            )
            .select_from(Keyword)
            .join(
                Reply,
                and_(
                    Keyword.source_type == KeywordSourceType.REPLY.value,
                    Keyword.source_id == Reply.id,
                    Reply.event_id == event_id,
                ),
            )
            .outerjoin(RiskFlag, Reply.session_id == RiskFlag.session_id)
            .where(
                Keyword.event_id == event_id,
                Keyword.status == KeywordStatus.ACTIVE.value,
                Reply.safety_status == SafetyStatus.SAFE.value,
                Reply.public_status == PublicStatus.PUBLIC.value,
                *risk_allows_reply,
            )
        )

        statement = union_all(card_keywords, reply_keywords)
        rows = self.db.execute(statement).all()
        return [
            DisplayKeywordRow(
                text=str(row[0]),
                category=str(row[1]),
                weight=Decimal(row[2]),
            )
            for row in rows
        ]
