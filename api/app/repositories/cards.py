from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.risk import RiskFlag
from app.repositories.base import BaseRepository


class MindCardRepository(BaseRepository[MindCard]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, MindCard)

    def create_card(
        self,
        *,
        event_id: UUID,
        session_id: UUID | None,
        prompt_type: str,
        content_raw: str,
        content_redacted: str | None,
        safety_status: str,
        public_status: str,
        moderation_reason: str | None,
        origin: str | None = None,
        origin_tag: str | None = None,
        created_by_admin_id: UUID | None = None,
        reviewed_by: UUID | None = None,
        reviewed_at=None,
    ) -> MindCard:
        card = MindCard(
            event_id=event_id,
            session_id=session_id,
            prompt_type=prompt_type,
            content_raw=content_raw,
            content_redacted=content_redacted,
            safety_status=safety_status,
            public_status=public_status,
            moderation_reason=moderation_reason,
            origin=origin or "participant",
            origin_tag=origin_tag,
            created_by_admin_id=created_by_admin_id,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
        )
        self.db.add(card)
        self.db.flush()
        return card

    def get_by_id(self, card_id: UUID) -> MindCard | None:
        return self.db.get(MindCard, card_id)

    def delete_card(self, card: MindCard) -> None:
        self.db.delete(card)
        self.db.flush()

    def list_by_session_id(self, session_id: UUID) -> list[MindCard]:
        statement = (
            select(MindCard)
            .where(MindCard.session_id == session_id)
            .order_by(desc(MindCard.created_at))
        )
        return list(self.db.execute(statement).scalars())

    def count_by_session_id(self, session_id: UUID) -> int:
        statement = select(func.count(MindCard.id)).where(MindCard.session_id == session_id)
        return int(self.db.execute(statement).scalar_one() or 0)

    def list_public_cards(
        self,
        *,
        event_id: UUID,
        exclude_session_id: UUID | None,
        limit: int,
    ) -> list[MindCard]:
        statement = (
            select(MindCard)
            .outerjoin(RiskFlag, MindCard.session_id == RiskFlag.session_id)
            .where(
                MindCard.event_id == event_id,
                MindCard.safety_status == "safe",
                MindCard.public_status == "public",
                or_(RiskFlag.id.is_(None), RiskFlag.public_restriction.is_(False)),
                or_(RiskFlag.id.is_(None), RiskFlag.crisis_expression_detected.is_(False)),
            )
            .order_by(desc(MindCard.created_at))
            .limit(limit)
        )
        if exclude_session_id is not None:
            statement = statement.where(
                or_(MindCard.session_id.is_(None), MindCard.session_id != exclude_session_id)
            )

        return list(self.db.execute(statement).scalars())

    def list_admin_cards(
        self,
        *,
        event_id: UUID,
        status_filter: str,
        origin_filter: str = "all",
        limit: int,
        offset: int,
    ) -> list[MindCard]:
        statement = select(MindCard).where(MindCard.event_id == event_id)
        statement = _apply_card_status_filter(statement, status_filter)
        statement = _apply_card_origin_filter(statement, origin_filter)
        statement = statement.order_by(desc(MindCard.created_at)).limit(limit).offset(offset)
        return list(self.db.execute(statement).scalars())

    def count_admin_cards(self, *, event_id: UUID, status_filter: str, origin_filter: str = "all") -> int:
        statement = select(func.count(MindCard.id)).where(MindCard.event_id == event_id)
        statement = _apply_card_status_filter(statement, status_filter)
        statement = _apply_card_origin_filter(statement, origin_filter)
        return int(self.db.execute(statement).scalar_one() or 0)


def _apply_card_status_filter(statement, status_filter: str):
    if status_filter == "all":
        return statement
    if status_filter in {"safe", "review", "exclude"}:
        return statement.where(MindCard.safety_status == status_filter)
    if status_filter in {"pending", "public", "hidden", "excluded"}:
        return statement.where(MindCard.public_status == status_filter)
    return statement.where(MindCard.safety_status == "review")


def _apply_card_origin_filter(statement, origin_filter: str):
    if origin_filter == "all":
        return statement
    return statement.where(MindCard.origin == origin_filter)
