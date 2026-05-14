from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question import Question
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Question)

    def list_by_event_id(self, event_id: UUID) -> list[Question]:
        statement = (
            select(Question)
            .where(Question.event_id == event_id)
            .order_by(Question.display_order.asc(), Question.question_no.asc())
        )
        return list(self.db.execute(statement).scalars())

    def list_by_ids_for_event(
        self,
        event_id: UUID,
        question_ids: set[UUID],
    ) -> list[Question]:
        if not question_ids:
            return []

        statement = select(Question).where(
            Question.event_id == event_id,
            Question.id.in_(question_ids),
        )
        return list(self.db.execute(statement).scalars())

    def get_by_event_and_no(self, event_id: UUID, question_no: int) -> Question | None:
        statement = select(Question).where(
            Question.event_id == event_id,
            Question.question_no == question_no,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def upsert_question(
        self,
        *,
        event_id: UUID,
        question_no: int,
        scale_code: str,
        question_key: str,
        title: str,
        description: str | None,
        question_type: str,
        options: list[dict[str, Any]],
        score_map: dict[str, Any],
        required: bool,
        display_order: int,
    ) -> tuple[Question, bool]:
        question = self.get_by_event_and_no(event_id, question_no)
        created = question is None
        if question is None:
            question = Question(event_id=event_id, question_no=question_no)

        question.scale_code = scale_code
        question.question_key = question_key
        question.title = title
        question.description = description
        question.question_type = question_type
        question.options = options
        question.score_map = score_map
        question.required = required
        question.display_order = display_order

        self.db.add(question)
        self.db.flush()
        return question, created
