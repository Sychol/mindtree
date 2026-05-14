from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.enums import EventStatus
from app.repositories.events import EventRepository
from app.repositories.questions import QuestionRepository
from app.schemas.questions import QuestionItem, QuestionsResponse


def get_event_questions(db: Session, event_slug: str) -> QuestionsResponse:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    if event.status != EventStatus.OPEN.value:
        raise AppError(
            ErrorCode.EVENT_NOT_OPEN,
            "공개 진입 가능한 이벤트가 아닙니다.",
            status.HTTP_403_FORBIDDEN,
            details={"status": event.status},
        )

    questions = QuestionRepository(db).list_by_event_id(event.id)
    return QuestionsResponse(
        questions=[
            QuestionItem(
                id=question.id,
                question_no=question.question_no,
                scale_code=question.scale_code,
                question_key=question.question_key,
                title=question.title,
                description=question.description,
                question_type=question.question_type,
                required=question.required,
                display_order=question.display_order,
                options=question.options,
            )
            for question in questions
        ]
    )
