from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.consent import ConsentLog
from app.repositories.base import BaseRepository


class ConsentRepository(BaseRepository[ConsentLog]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ConsentLog)

    def get_by_session_and_version(
        self,
        session_id: UUID,
        consent_version: str,
    ) -> ConsentLog | None:
        statement = (
            select(ConsentLog)
            .where(
                ConsentLog.session_id == session_id,
                ConsentLog.consent_version == consent_version,
            )
            .order_by(ConsentLog.accepted_at.asc())
            .limit(1)
        )
        return self.db.execute(statement).scalar_one_or_none()

    def exists_for_session(self, session_id: UUID) -> bool:
        statement = select(ConsentLog.id).where(ConsentLog.session_id == session_id).limit(1)
        return self.db.execute(statement).scalar_one_or_none() is not None

    def count_for_session_and_version(
        self,
        session_id: UUID,
        consent_version: str,
    ) -> int:
        statement = select(ConsentLog.id).where(
            ConsentLog.session_id == session_id,
            ConsentLog.consent_version == consent_version,
        )
        return len(self.db.execute(statement).scalars().all())

    def create_consent_log(
        self,
        event_id: UUID,
        session_id: UUID,
        consent_version: str,
        accepted_items: dict[str, bool],
        ip_hash: str | None,
        user_agent_hash: str | None,
    ) -> ConsentLog:
        consent_log = ConsentLog(
            event_id=event_id,
            session_id=session_id,
            consent_version=consent_version,
            accepted_items=accepted_items,
            ip_hash=ip_hash,
            user_agent_hash=user_agent_hash,
        )
        self.db.add(consent_log)
        self.db.flush()
        self.db.refresh(consent_log)
        return consent_log
