from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.repositories.base import BaseRepository


class AnswerRepository(BaseRepository[Answer]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Answer)

    def list_by_session_id(self, session_id: UUID) -> list[Answer]:
        statement = select(Answer).where(Answer.session_id == session_id)
        return list(self.db.execute(statement).scalars())

    def get_by_session_and_question(
        self,
        session_id: UUID,
        question_id: UUID,
    ) -> Answer | None:
        statement = select(Answer).where(
            Answer.session_id == session_id,
            Answer.question_id == question_id,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def upsert_answer(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        question_id: UUID,
        answer_value,
        score_value,
    ) -> Answer:
        answer = self.get_by_session_and_question(session_id, question_id)
        if answer is None:
            answer = Answer(
                event_id=event_id,
                session_id=session_id,
                question_id=question_id,
            )

        answer.answer_value = answer_value
        answer.score_value = score_value
        self.db.add(answer)
        self.db.flush()
        return answer
