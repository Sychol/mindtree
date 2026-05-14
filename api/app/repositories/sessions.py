from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.event import Event
from app.models.session import Session
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    def __init__(self, db: SQLAlchemySession) -> None:
        super().__init__(db, Session)

    def get_session_and_event_by_id(self, session_id: UUID) -> tuple[Session, Event] | None:
        statement = (
            select(Session, Event)
            .join(Event, Session.event_id == Event.id)
            .where(Session.id == session_id)
        )
        row = self.db.execute(statement).one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    def get_by_resume_token_hash(
        self,
        event_id: UUID,
        resume_token_hash: str,
    ) -> Session | None:
        statement = select(Session).where(
            Session.event_id == event_id,
            Session.resume_token_hash == resume_token_hash,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_anonymous_key_hash(
        self,
        event_id: UUID,
        anonymous_key_hash: str,
    ) -> Session | None:
        statement = select(Session).where(
            Session.event_id == event_id,
            Session.anonymous_key_hash == anonymous_key_hash,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def create_session(
        self,
        event_id: UUID,
        anonymous_key_hash: str,
        resume_token_hash: str,
        client_meta: dict[str, str],
    ) -> Session:
        session = Session(
            event_id=event_id,
            anonymous_key_hash=anonymous_key_hash,
            resume_token_hash=resume_token_hash,
            status="created",
            last_step="landing",
            client_meta=client_meta,
        )
        self.db.add(session)
        self.db.flush()
        return session

    def set_status_and_step(
        self,
        session: Session,
        status: str,
        last_step: str,
    ) -> Session:
        session.status = status
        session.last_step = last_step
        self.db.add(session)
        self.db.flush()
        return session
