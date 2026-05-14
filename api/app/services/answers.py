from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.models.answer import Answer
from app.models.enums import SessionStatus
from app.models.question import Question
from app.repositories.answers import AnswerRepository
from app.repositories.risk_flags import RiskFlagRepository
from app.repositories.scale_scores import ScaleScoreRepository
from app.repositories.questions import QuestionRepository
from app.repositories.sessions import SessionRepository
from app.schemas.answers import (
    BulkAnswerRequest,
    BulkAnswerResponse,
    BulkAnswerScoringResponse,
    RiskFlagsSummary,
    ScaleScoreSummary,
)
from app.services.risk_rules import calculate_risk_flags
from app.services.scoring import calculate_answer_score, calculate_scale_scores
from app.services.sessions import status_at_least

PROFILE_GENERAL_PUBLIC_VALUE = "q03_opt05"
PROFILE_GENERAL_PUBLIC_LABEL = "일반인"
SKIPPABLE_PROFILE_QUESTION_NOS = {4, 5}


def _json_key(value: Any) -> str:
    return str(value)


def _option_values(question: Question) -> list[Any]:
    return [option.get("value") for option in question.options]


def _match_option_value(question: Question, answer_value: Any) -> tuple[bool, Any]:
    for option_value in _option_values(question):
        if answer_value == option_value:
            return True, option_value

        if isinstance(option_value, (int, float)) and not isinstance(option_value, bool):
            try:
                if Decimal(str(answer_value)) == Decimal(str(option_value)):
                    return True, option_value
            except Exception:
                pass

    return False, answer_value


def _bad_answer(question: Question, answer_value: Any) -> AppError:
    return AppError(
        ErrorCode.BAD_REQUEST,
        "일부 문항 응답이 올바르지 않습니다.",
        status.HTTP_400_BAD_REQUEST,
        details={
            "questionId": str(question.id),
            "questionNo": question.question_no,
            "answerValue": answer_value,
        },
    )


def validate_answer_value(question: Question, answer_value: Any) -> Any:
    if question.question_type in {"single_select", "likert"}:
        matched, normalized_value = _match_option_value(question, answer_value)
        if not matched:
            raise _bad_answer(question, answer_value)
        return normalized_value

    if question.question_type == "number":
        if isinstance(answer_value, bool) or not isinstance(answer_value, (int, float)):
            raise _bad_answer(question, answer_value)
        matched, normalized_value = _match_option_value(question, answer_value)
        if question.options and not matched:
            raise _bad_answer(question, answer_value)
        return normalized_value

    if question.question_type == "multi_select":
        if not isinstance(answer_value, list):
            raise _bad_answer(question, answer_value)

        normalized_values: list[Any] = []
        for item in answer_value:
            matched, normalized_value = _match_option_value(question, item)
            if not matched:
                raise _bad_answer(question, answer_value)
            normalized_values.append(normalized_value)
        return normalized_values

    if question.question_type == "text":
        if not isinstance(answer_value, str) or len(answer_value) > 300:
            raise _bad_answer(question, answer_value)
        return answer_value

    raise _bad_answer(question, answer_value)


def _score_or_raise(question: Question, answer_value: Any) -> Decimal | None:
    score = calculate_answer_score(question, answer_value)
    if question.score_map and score is None:
        raise _bad_answer(question, answer_value)
    return score


def _answer_is_general_public(question: Question, answer: Answer | None) -> bool:
    if answer is None:
        return False
    if answer.answer_value == PROFILE_GENERAL_PUBLIC_VALUE:
        return True

    matching_option = next(
        (
            option
            for option in question.options
            if option.get("value") == answer.answer_value
        ),
        None,
    )
    return matching_option is not None and matching_option.get("label") == PROFILE_GENERAL_PUBLIC_LABEL


def _missing_required_question_nos(
    questions: list[Question],
    answers: list[Answer],
) -> list[int]:
    question_by_id = {question.id: question for question in questions}
    question_by_no = {question.question_no: question for question in questions}
    answer_by_question_id = {answer.question_id: answer for answer in answers}

    q3 = question_by_no.get(3)
    q3_answer = answer_by_question_id.get(q3.id) if q3 is not None else None
    skip_profile_job_questions = q3 is not None and _answer_is_general_public(q3, q3_answer)

    missing: list[int] = []
    for question in questions:
        if not question.required:
            continue
        if skip_profile_job_questions and question.question_no in SKIPPABLE_PROFILE_QUESTION_NOS:
            continue
        if question.id not in answer_by_question_id:
            missing.append(question.question_no)

    return missing


def _ensure_unique_question_ids(payload: BulkAnswerRequest) -> None:
    seen: set[UUID] = set()
    duplicates: list[str] = []
    for answer in payload.answers:
        if answer.question_id in seen:
            duplicates.append(str(answer.question_id))
        seen.add(answer.question_id)

    if duplicates:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "같은 요청 안에 중복된 questionId가 있습니다.",
            status.HTTP_400_BAD_REQUEST,
            details={"duplicateQuestionIds": duplicates},
        )


def _scale_score_response(scale_scores) -> list[ScaleScoreSummary]:
    return [
        ScaleScoreSummary(
            scale_code=scale_score.scale_code,
            raw_score=float(scale_score.raw_score),
            severity_level=scale_score.severity_level,
        )
        for scale_score in scale_scores
    ]


def save_bulk_answers(
    db: SQLAlchemySession,
    session_id: UUID,
    payload: BulkAnswerRequest,
) -> BulkAnswerResponse:
    if not payload.answers:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "저장할 응답이 없습니다.",
            status.HTTP_400_BAD_REQUEST,
        )
    _ensure_unique_question_ids(payload)

    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    session, event = row
    if session.status == SessionStatus.CREATED.value:
        raise AppError(
            ErrorCode.CONSENT_REQUIRED,
            "필수 동의 후 문항 응답을 제출할 수 있습니다.",
            status.HTTP_403_FORBIDDEN,
        )
    if not status_at_least(session.status, SessionStatus.CONSENTED.value):
        raise AppError(
            ErrorCode.INVALID_SESSION_STATUS,
            "문항 응답을 제출할 수 없는 세션 상태입니다.",
            status.HTTP_400_BAD_REQUEST,
            details={"status": session.status},
        )

    question_repository = QuestionRepository(db)
    answer_repository = AnswerRepository(db)
    scale_score_repository = ScaleScoreRepository(db)
    risk_flag_repository = RiskFlagRepository(db)

    event_questions = question_repository.list_by_event_id(event.id)
    requested_ids = {answer.question_id for answer in payload.answers}
    questions = question_repository.list_by_ids_for_event(event.id, requested_ids)
    question_by_id = {question.id: question for question in questions}

    invalid_question_ids = sorted(
        str(question_id)
        for question_id in requested_ids
        if question_id not in question_by_id
    )
    if invalid_question_ids:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "세션의 이벤트에 속하지 않는 문항이 포함되어 있습니다.",
            status.HTTP_400_BAD_REQUEST,
            details={"invalidQuestionIds": invalid_question_ids},
        )

    for item in payload.answers:
        question = question_by_id[item.question_id]
        answer_value = validate_answer_value(question, item.answer_value)
        score_value = _score_or_raise(question, answer_value)
        answer_repository.upsert_answer(
            event_id=event.id,
            session_id=session.id,
            question_id=question.id,
            answer_value=answer_value,
            score_value=score_value,
        )

    current_answers = answer_repository.list_by_session_id(session.id)
    missing_question_nos = _missing_required_question_nos(event_questions, current_answers)
    if missing_question_nos:
        db.commit()
        db.refresh(session)
        return BulkAnswerResponse(
            saved_count=len(payload.answers),
            missing_question_nos=missing_question_nos,
            session_status=session.status,
            scoring=BulkAnswerScoringResponse(
                calculated=False,
                scale_scores=[],
                risk_flags=None,
            ),
        )

    scale_results = calculate_scale_scores(event_questions, current_answers)
    persisted_scale_scores = [
        scale_score_repository.upsert_scale_score(
            event_id=event.id,
            session_id=session.id,
            scale_code=result.scale_code,
            raw_score=result.raw_score,
            severity_level=result.severity_level,
            sub_scores=result.sub_scores,
            rule_version=result.rule_version,
        )
        for result in scale_results
    ]

    risk_result = calculate_risk_flags(scale_results)
    persisted_risk_flag = risk_flag_repository.upsert_risk_flags(
        event_id=event.id,
        session_id=session.id,
        phq9_item9_positive=risk_result.phq9_item9_positive,
        crisis_expression_detected=risk_result.crisis_expression_detected,
        trauma_high_signal=risk_result.trauma_high_signal,
        moral_injury_high_signal=risk_result.moral_injury_high_signal,
        public_restriction=risk_result.public_restriction,
        help_notice_required=risk_result.help_notice_required,
        details=risk_result.details,
        rule_version=risk_result.rule_version,
    )

    if session.status in {SessionStatus.CONSENTED.value, SessionStatus.QUESTIONS_COMPLETED.value}:
        # TODO(phase06+): define whether already summarized/completed sessions may be re-scored.
        SessionRepository(db).set_status_and_step(
            session,
            SessionStatus.QUESTIONS_COMPLETED.value,
            "summary",
        )

    db.commit()
    db.refresh(session)
    for scale_score in persisted_scale_scores:
        db.refresh(scale_score)
    db.refresh(persisted_risk_flag)

    return BulkAnswerResponse(
        saved_count=len(payload.answers),
        missing_question_nos=[],
        session_status=session.status,
        scoring=BulkAnswerScoringResponse(
            calculated=True,
            scale_scores=_scale_score_response(persisted_scale_scores),
            risk_flags=RiskFlagsSummary(
                phq9_item9_positive=persisted_risk_flag.phq9_item9_positive,
                crisis_expression_detected=persisted_risk_flag.crisis_expression_detected,
                trauma_high_signal=persisted_risk_flag.trauma_high_signal,
                moral_injury_high_signal=persisted_risk_flag.moral_injury_high_signal,
                public_restriction=persisted_risk_flag.public_restriction,
                help_notice_required=persisted_risk_flag.help_notice_required,
            ),
        ),
    )
