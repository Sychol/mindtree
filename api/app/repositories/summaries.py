from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.summary import Summary
from app.repositories.base import BaseRepository


class SummaryRepository(BaseRepository[Summary]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Summary)

    def get_by_session_id(self, session_id: UUID) -> Summary | None:
        statement = select(Summary).where(Summary.session_id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def create_summary(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        template_text: str,
        llm_text: str | None,
        final_text: str,
        generation_mode: str,
        llm_job_id: UUID | None = None,
    ) -> Summary:
        summary = Summary(
            event_id=event_id,
            session_id=session_id,
            template_text=template_text,
            llm_text=llm_text,
            final_text=final_text,
            generation_mode=generation_mode,
            llm_job_id=llm_job_id,
        )
        self.db.add(summary)
        self.db.flush()
        return summary

    def update_viewed_at(
        self,
        summary: Summary,
        viewed_at: datetime,
    ) -> Summary:
        summary.viewed_at = viewed_at
        self.db.add(summary)
        self.db.flush()
        return summary
