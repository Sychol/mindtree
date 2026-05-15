from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.completion import CompletionCode
from app.repositories.base import BaseRepository


class CompletionCodeRepository(BaseRepository[CompletionCode]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, CompletionCode)

    def get_by_session_id(self, session_id: UUID) -> CompletionCode | None:
        statement = select(CompletionCode).where(CompletionCode.session_id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_code(self, code: str) -> CompletionCode | None:
        statement = select(CompletionCode).where(CompletionCode.code == code)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_event_and_code(self, *, event_id: UUID, code: str) -> CompletionCode | None:
        statement = select(CompletionCode).where(
            CompletionCode.event_id == event_id,
            CompletionCode.code == code,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def create_code(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        code: str,
    ) -> CompletionCode:
        completion_code = CompletionCode(
            event_id=event_id,
            session_id=session_id,
            code=code,
            status="issued",
        )
        self.db.add(completion_code)
        self.db.flush()
        return completion_code
