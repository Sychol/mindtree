from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import CardSelection
from app.repositories.base import BaseRepository


class CardSelectionRepository(BaseRepository[CardSelection]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CardSelection)

    def get_by_session_id(self, session_id: UUID) -> CardSelection | None:
        statement = select(CardSelection).where(CardSelection.session_id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def upsert_selection(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        selected_card_id: UUID,
    ) -> CardSelection:
        selection = self.get_by_session_id(session_id)
        now = datetime.now(timezone.utc)
        if selection is None:
            selection = CardSelection(
                event_id=event_id,
                session_id=session_id,
                selected_card_id=selected_card_id,
                selected_at=now,
            )
        else:
            selection.selected_card_id = selected_card_id
            selection.selected_at = now

        self.db.add(selection)
        self.db.flush()
        return selection
