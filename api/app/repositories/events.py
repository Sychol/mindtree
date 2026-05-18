from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.repositories.base import BaseRepository


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Event)

    def get_by_slug(self, slug: str) -> Event | None:
        statement = select(Event).where(Event.slug == slug)
        return self.db.execute(statement).scalar_one_or_none()

    def save_settings(self, event: Event, settings: dict) -> Event:
        event.settings = settings
        self.db.add(event)
        self.db.flush()
        return event
