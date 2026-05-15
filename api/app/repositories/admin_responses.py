from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.answer import Answer
from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.event import Event
from app.models.question import Question
from app.models.reply import Reply
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession


@dataclass(frozen=True)
class AdminResponseSessionFilters:
    status: str = "all"
    completed_only: bool = False
    created_from: datetime | None = None
    created_to: datetime | None = None


class AdminResponsesRepository:
    def __init__(self, db: SQLAlchemySession) -> None:
        self.db = db

    def get_event_by_slug(self, event_slug: str) -> Event | None:
        statement = select(Event).where(Event.slug == event_slug)
        return self.db.execute(statement).scalar_one_or_none()

    def _session_statement(self, event_id: UUID, filters: AdminResponseSessionFilters):
        statement = select(EventSession).where(EventSession.event_id == event_id)
        if filters.status != "all":
            statement = statement.where(EventSession.status == filters.status)
        if filters.completed_only:
            statement = statement.where(EventSession.status == "completed")
        if filters.created_from is not None:
            statement = statement.where(EventSession.created_at >= filters.created_from)
        if filters.created_to is not None:
            statement = statement.where(EventSession.created_at <= filters.created_to)
        return statement

    def list_sessions_for_export(
        self,
        event_id: UUID,
        filters: AdminResponseSessionFilters,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[EventSession]:
        statement = (
            self._session_statement(event_id, filters)
            .order_by(EventSession.created_at.desc(), EventSession.id.desc())
            .offset(offset)
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list(self.db.execute(statement).scalars())

    def count_sessions_for_export(
        self,
        event_id: UUID,
        filters: AdminResponseSessionFilters,
    ) -> int:
        session_statement = self._session_statement(event_id, filters).subquery()
        statement = select(func.count()).select_from(session_statement)
        return int(self.db.execute(statement).scalar_one() or 0)

    def list_questions_for_event(self, event_id: UUID) -> list[Question]:
        statement = (
            select(Question)
            .where(Question.event_id == event_id)
            .order_by(Question.display_order.asc(), Question.question_no.asc())
        )
        return list(self.db.execute(statement).scalars())

    def list_answers_for_sessions(self, session_ids: list[UUID]) -> list[Answer]:
        if not session_ids:
            return []
        statement = (
            select(Answer)
            .where(Answer.session_id.in_(session_ids))
            .order_by(Answer.session_id.asc(), Answer.submitted_at.asc())
        )
        return list(self.db.execute(statement).scalars())

    def list_scale_scores_for_sessions(self, session_ids: list[UUID]) -> list[ScaleScore]:
        if not session_ids:
            return []
        statement = select(ScaleScore).where(ScaleScore.session_id.in_(session_ids))
        return list(self.db.execute(statement).scalars())

    def list_risk_flags_for_sessions(self, session_ids: list[UUID]) -> list[RiskFlag]:
        if not session_ids:
            return []
        statement = select(RiskFlag).where(RiskFlag.session_id.in_(session_ids))
        return list(self.db.execute(statement).scalars())

    def list_completion_status_for_sessions(self, session_ids: list[UUID]) -> list[CompletionCode]:
        if not session_ids:
            return []
        statement = select(CompletionCode).where(CompletionCode.session_id.in_(session_ids))
        return list(self.db.execute(statement).scalars())

    def count_cards_by_session_ids(self, session_ids: list[UUID]) -> dict[UUID, int]:
        if not session_ids:
            return {}
        statement = (
            select(MindCard.session_id, func.count(MindCard.id))
            .where(MindCard.session_id.in_(session_ids))
            .group_by(MindCard.session_id)
        )
        return {session_id: int(count or 0) for session_id, count in self.db.execute(statement).all()}

    def count_replies_by_session_ids(self, session_ids: list[UUID]) -> dict[UUID, int]:
        if not session_ids:
            return {}
        statement = (
            select(Reply.session_id, func.count(Reply.id))
            .where(Reply.session_id.in_(session_ids))
            .group_by(Reply.session_id)
        )
        return {session_id: int(count or 0) for session_id, count in self.db.execute(statement).all()}
