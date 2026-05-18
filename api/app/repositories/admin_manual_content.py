from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.reply import Reply
from app.repositories.cards import MindCardRepository
from app.repositories.replies import ReplyRepository


class AdminManualContentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.cards = MindCardRepository(db)
        self.replies = ReplyRepository(db)

    def get_card(self, card_id: UUID) -> MindCard | None:
        return self.cards.get_by_id(card_id)

    def get_reply(self, reply_id: UUID) -> Reply | None:
        return self.replies.get_by_id(reply_id)
