from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.models.admin import AdminUser
from app.models.answer import Answer
from app.models.completion import CompletionCode
from app.models.enums import SessionStatus
from app.models.question import Question
from app.models.risk import RiskFlag
from app.models.score import ScaleScore
from app.models.session import Session as EventSession
from app.repositories.admin_responses import (
    AdminResponseSessionFilters,
    AdminResponsesRepository,
)
from app.schemas.admin_responses import (
    AdminResponseColumn,
    AdminResponsesColumnsResponse,
    AdminResponsesExportRequest,
    AdminResponsesListResponse,
)
from app.services.audit_log import create_audit_log
from app.services.csv_export import CsvExportFile, CsvExportService
from app.services.sessions import status_at_least


ALLOWED_VIEWS = {"summary", "wide", "long"}
ALLOWED_STATUSES = {
    SessionStatus.CREATED.value,
    SessionStatus.CONSENTED.value,
    SessionStatus.QUESTIONS_COMPLETED.value,
    SessionStatus.SUMMARY_VIEWED.value,
    SessionStatus.CARD_CREATED.value,
    SessionStatus.REPLY_CREATED.value,
    SessionStatus.COMPLETED.value,
    "all",
}

SCALE_CODES: tuple[tuple[str, str], ...] = (
    ("phq9", "PHQ-9"),
    ("pcl5", "PCL-5"),
    ("kmies", "K-MIES"),
    ("kscs", "K-SCS"),
)

RISK_COLUMN_DEFS: tuple[tuple[str, str, str], ...] = (
    ("phq9Item9Positive", "phq9_item9_positive", "PHQ-9 9번 양성"),
    ("crisisExpressionDetected", "crisis_expression_detected", "위기 표현 감지"),
    ("traumaHighSignal", "trauma_high_signal", "트라우마 고신호"),
    ("moralInjuryHighSignal", "moral_injury_high_signal", "도덕적 손상 고신호"),
    ("publicRestriction", "public_restriction", "공개 제한"),
    ("helpNoticeRequired", "help_notice_required", "도움 안내 필요"),
)

WIDE_BASE_HEADERS = [
    "event_slug",
    "session_short_id",
    "session_status",
    "created_at",
    "completed_at",
    "consent_accepted",
    "questions_completed",
    "summary_viewed",
    "card_count",
    "reply_created",
    "completion_status",
]

LONG_HEADERS = [
    "event_slug",
    "session_short_id",
    "session_status",
    "question_no",
    "question_key",
    "scale_code",
    "question_title",
    "answer_value",
    "answer_label",
    "score_value",
    "submitted_at",
]


@dataclass(frozen=True)
class AdminResponsesQuery:
    view: str = "summary"
    status: str = "all"
    completed_only: bool = False
    include_scores: bool = True
    include_risk_flags: bool = False
    include_completion_status: bool = True
    created_from: datetime | None = None
    created_to: datetime | None = None
    limit: int = 50
    offset: int = 0


def _event_not_found() -> AppError:
    return AppError(
        ErrorCode.EVENT_NOT_FOUND,
        "이벤트를 찾을 수 없습니다.",
        status.HTTP_404_NOT_FOUND,
    )


def _validate_filters(
    *,
    view: str | None,
    status_filter: str,
    created_from: datetime | None,
    created_to: datetime | None,
) -> None:
    if view is not None and view not in ALLOWED_VIEWS:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 응답 데이터 view입니다.")
    if status_filter not in ALLOWED_STATUSES:
        raise AppError(ErrorCode.BAD_REQUEST, "지원하지 않는 세션 상태 필터입니다.")
    if created_from is not None and created_to is not None and created_from > created_to:
        raise AppError(ErrorCode.BAD_REQUEST, "createdFrom은 createdTo보다 이후일 수 없습니다.")


def _session_filters(query: AdminResponsesQuery | AdminResponsesExportRequest) -> AdminResponseSessionFilters:
    return AdminResponseSessionFilters(
        status=query.status,
        completed_only=query.completed_only,
        created_from=query.created_from,
        created_to=query.created_to,
    )


def _question_key(question: Question) -> str:
    return f"q{question.question_no:03d}"


def _question_label(question: Question) -> str:
    return f"Q{question.question_no}. {question.title}"


def _summary_columns(include_completion_status: bool = True) -> list[AdminResponseColumn]:
    columns = [
        AdminResponseColumn(key="sessionShortId", label="참여 번호", type="text"),
        AdminResponseColumn(key="status", label="세션 상태", type="text"),
        AdminResponseColumn(key="createdAt", label="생성 일시", type="text"),
        AdminResponseColumn(key="completedAt", label="완료 일시", type="text"),
        AdminResponseColumn(key="cardCount", label="마음카드 수", type="text"),
        AdminResponseColumn(key="replyCreated", label="응원 작성", type="completion"),
    ]
    if include_completion_status:
        columns.append(AdminResponseColumn(key="completionStatus", label="완료 코드 상태", type="completion"))
    return columns


def _wide_base_columns(include_completion_status: bool = True) -> list[AdminResponseColumn]:
    columns = [
        AdminResponseColumn(key="eventSlug", label="이벤트", type="text"),
        AdminResponseColumn(key="sessionShortId", label="참여 번호", type="text"),
        AdminResponseColumn(key="sessionStatus", label="세션 상태", type="text"),
        AdminResponseColumn(key="createdAt", label="생성 일시", type="text"),
        AdminResponseColumn(key="completedAt", label="완료 일시", type="text"),
        AdminResponseColumn(key="consentAccepted", label="동의 완료", type="completion"),
        AdminResponseColumn(key="questionsCompleted", label="문항 완료", type="completion"),
        AdminResponseColumn(key="summaryViewed", label="요약 확인", type="completion"),
        AdminResponseColumn(key="cardCount", label="마음카드 수", type="text"),
        AdminResponseColumn(key="replyCreated", label="응원 작성", type="completion"),
    ]
    if include_completion_status:
        columns.append(AdminResponseColumn(key="completionStatus", label="완료 코드 상태", type="completion"))
    return columns


def _question_columns(questions: list[Question]) -> list[AdminResponseColumn]:
    return [
        AdminResponseColumn(
            key=_question_key(question),
            label=_question_label(question),
            type="answer",
            questionNo=question.question_no,
            questionKey=question.question_key,
            scaleCode=question.scale_code,
        )
        for question in questions
    ]


def _score_columns() -> list[AdminResponseColumn]:
    columns: list[AdminResponseColumn] = []
    for scale_code, label in SCALE_CODES:
        columns.extend(
            [
                AdminResponseColumn(
                    key=f"{scale_code}RawScore",
                    label=f"{label} 점수",
                    type="score",
                    scaleCode=scale_code,
                ),
                AdminResponseColumn(
                    key=f"{scale_code}Severity",
                    label=f"{label} 수준",
                    type="score",
                    scaleCode=scale_code,
                ),
            ]
        )
    return columns


def _risk_columns() -> list[AdminResponseColumn]:
    return [
        AdminResponseColumn(key=camel_key, label=label, type="risk")
        for camel_key, _snake_key, label in RISK_COLUMN_DEFS
    ]


def _long_columns() -> list[AdminResponseColumn]:
    return [
        AdminResponseColumn(key="eventSlug", label="이벤트", type="text"),
        AdminResponseColumn(key="sessionShortId", label="참여 번호", type="text"),
        AdminResponseColumn(key="sessionStatus", label="세션 상태", type="text"),
        AdminResponseColumn(key="questionNo", label="문항 번호", type="text"),
        AdminResponseColumn(key="questionKey", label="문항 키", type="text"),
        AdminResponseColumn(key="scaleCode", label="척도", type="text"),
        AdminResponseColumn(key="questionTitle", label="문항", type="text"),
        AdminResponseColumn(key="answerValue", label="응답 원값", type="answer"),
        AdminResponseColumn(key="answerLabel", label="응답 표시값", type="answer"),
        AdminResponseColumn(key="scoreValue", label="문항 점수", type="score"),
        AdminResponseColumn(key="submittedAt", label="제출 일시", type="text"),
    ]


def _value_to_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _row_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _values_match(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if str(left) == str(right):
        return True
    try:
        return json.dumps(left, sort_keys=True, ensure_ascii=False) == json.dumps(
            right,
            sort_keys=True,
            ensure_ascii=False,
        )
    except TypeError:
        return False


def _option_label(question: Question, value: Any) -> str | None:
    for option in question.options or []:
        if not isinstance(option, dict):
            continue
        if _values_match(option.get("value"), value):
            label = option.get("label")
            return str(label) if label is not None else None
    return None


def _answer_label(question: Question, answer_value: Any) -> str:
    if isinstance(answer_value, list):
        labels = []
        for item in answer_value:
            labels.append(_option_label(question, item) or _value_to_string(item))
        return "; ".join(labels)
    if isinstance(answer_value, dict) and "value" in answer_value:
        inner_value = answer_value.get("value")
        return _option_label(question, inner_value) or _value_to_string(inner_value)
    return _option_label(question, answer_value) or _value_to_string(answer_value)


def _short_session_id(session: EventSession) -> str:
    return session.id.hex[:8]


def _completion_status(completion: CompletionCode | None) -> str | None:
    if completion is None:
        return None
    return completion.status


def _score_maps(scores: list[ScaleScore]) -> dict[UUID, dict[str, ScaleScore]]:
    result: dict[UUID, dict[str, ScaleScore]] = {}
    for score in scores:
        result.setdefault(score.session_id, {})[score.scale_code] = score
    return result


def _answer_maps(answers: list[Answer]) -> tuple[dict[tuple[UUID, UUID], Answer], dict[UUID, list[Answer]]]:
    by_session_question: dict[tuple[UUID, UUID], Answer] = {}
    by_session: dict[UUID, list[Answer]] = {}
    for answer in answers:
        by_session_question[(answer.session_id, answer.question_id)] = answer
        by_session.setdefault(answer.session_id, []).append(answer)
    return by_session_question, by_session


def _session_summary_values(
    session: EventSession,
    *,
    card_count: int,
    reply_count: int,
    completion: CompletionCode | None,
) -> dict[str, Any]:
    return {
        "sessionShortId": _short_session_id(session),
        "status": session.status,
        "createdAt": _row_value(session.created_at),
        "completedAt": _row_value(session.completed_at),
        "cardCount": card_count,
        "replyCreated": reply_count > 0 or status_at_least(session.status, SessionStatus.REPLY_CREATED.value),
        "completionStatus": _completion_status(completion),
    }


def _session_wide_values(
    session: EventSession,
    *,
    event_slug: str,
    card_count: int,
    reply_count: int,
    completion: CompletionCode | None,
) -> dict[str, Any]:
    return {
        "eventSlug": event_slug,
        "sessionShortId": _short_session_id(session),
        "sessionStatus": session.status,
        "createdAt": _row_value(session.created_at),
        "completedAt": _row_value(session.completed_at),
        "consentAccepted": status_at_least(session.status, SessionStatus.CONSENTED.value),
        "questionsCompleted": status_at_least(session.status, SessionStatus.QUESTIONS_COMPLETED.value),
        "summaryViewed": status_at_least(session.status, SessionStatus.SUMMARY_VIEWED.value),
        "cardCount": card_count,
        "replyCreated": reply_count > 0 or status_at_least(session.status, SessionStatus.REPLY_CREATED.value),
        "completionStatus": _completion_status(completion),
    }


def _add_question_values(
    row: dict[str, Any],
    *,
    session: EventSession,
    questions: list[Question],
    answers_by_session_question: dict[tuple[UUID, UUID], Answer],
) -> None:
    for question in questions:
        answer = answers_by_session_question.get((session.id, question.id))
        row[_question_key(question)] = None if answer is None else _answer_label(question, answer.answer_value)


def _add_score_values(row: dict[str, Any], scores_by_session: dict[str, ScaleScore] | dict[UUID, ScaleScore]) -> None:
    for scale_code, _label in SCALE_CODES:
        score = scores_by_session.get(scale_code)  # type: ignore[arg-type]
        row[f"{scale_code}RawScore"] = None if score is None else _row_value(score.raw_score)
        row[f"{scale_code}Severity"] = None if score is None else score.severity_level


def _add_risk_values(row: dict[str, Any], risk_flag: RiskFlag | None) -> None:
    for camel_key, snake_key, _label in RISK_COLUMN_DEFS:
        row[camel_key] = False if risk_flag is None else bool(getattr(risk_flag, snake_key))


def _load_related(
    repo: AdminResponsesRepository,
    sessions: list[EventSession],
    *,
    include_scores: bool,
    include_risk_flags: bool,
    include_completion_status: bool,
) -> dict[str, Any]:
    session_ids = [session.id for session in sessions]
    answers = repo.list_answers_for_sessions(session_ids)
    answers_by_session_question, answers_by_session = _answer_maps(answers)
    return {
        "answersBySessionQuestion": answers_by_session_question,
        "answersBySession": answers_by_session,
        "scoresBySession": _score_maps(repo.list_scale_scores_for_sessions(session_ids)) if include_scores else {},
        "riskBySession": {
            risk.session_id: risk
            for risk in repo.list_risk_flags_for_sessions(session_ids)
        }
        if include_risk_flags
        else {},
        "completionBySession": {
            completion.session_id: completion
            for completion in repo.list_completion_status_for_sessions(session_ids)
        }
        if include_completion_status
        else {},
        "cardCounts": repo.count_cards_by_session_ids(session_ids),
        "replyCounts": repo.count_replies_by_session_ids(session_ids),
    }


def get_admin_response_columns(
    db: SQLAlchemySession,
    *,
    event_slug: str,
) -> AdminResponsesColumnsResponse:
    repo = AdminResponsesRepository(db)
    event = repo.get_event_by_slug(event_slug)
    if event is None:
        raise _event_not_found()
    questions = repo.list_questions_for_event(event.id)
    return AdminResponsesColumnsResponse(
        summaryColumns=_summary_columns(include_completion_status=True),
        questionColumns=_question_columns(questions),
        scoreColumns=_score_columns(),
        riskColumns=_risk_columns(),
    )


def list_admin_responses(
    db: SQLAlchemySession,
    *,
    event_slug: str,
    query: AdminResponsesQuery,
) -> AdminResponsesListResponse:
    _validate_filters(
        view=query.view,
        status_filter=query.status,
        created_from=query.created_from,
        created_to=query.created_to,
    )
    repo = AdminResponsesRepository(db)
    event = repo.get_event_by_slug(event_slug)
    if event is None:
        raise _event_not_found()

    filters = _session_filters(query)
    questions = repo.list_questions_for_event(event.id)
    sessions = repo.list_sessions_for_export(event.id, filters, limit=query.limit, offset=query.offset)
    total = repo.count_sessions_for_export(event.id, filters)
    related = _load_related(
        repo,
        sessions,
        include_scores=query.include_scores,
        include_risk_flags=query.include_risk_flags,
        include_completion_status=query.include_completion_status,
    )

    if query.view == "long":
        columns = _long_columns()
        rows = _build_long_rows(
            event_slug=event.slug,
            sessions=sessions,
            questions=questions,
            answers_by_session=related["answersBySession"],
        )
    else:
        base_columns = (
            _wide_base_columns(query.include_completion_status)
            if query.view == "wide"
            else _summary_columns(query.include_completion_status)
        )
        columns = [*base_columns, *_question_columns(questions)]
        if query.include_scores:
            columns.extend(_score_columns())
        if query.include_risk_flags:
            columns.extend(_risk_columns())
        rows = _build_session_rows(
            view=query.view,
            event_slug=event.slug,
            sessions=sessions,
            questions=questions,
            related=related,
            include_scores=query.include_scores,
            include_risk_flags=query.include_risk_flags,
            include_completion_status=query.include_completion_status,
        )

    return AdminResponsesListResponse(
        columns=columns,
        rows=rows,
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


def _build_session_rows(
    *,
    view: str,
    event_slug: str,
    sessions: list[EventSession],
    questions: list[Question],
    related: dict[str, Any],
    include_scores: bool,
    include_risk_flags: bool,
    include_completion_status: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in sessions:
        card_count = related["cardCounts"].get(session.id, 0)
        reply_count = related["replyCounts"].get(session.id, 0)
        completion = related["completionBySession"].get(session.id)
        if view == "wide":
            row = _session_wide_values(
                session,
                event_slug=event_slug,
                card_count=card_count,
                reply_count=reply_count,
                completion=completion,
            )
        else:
            row = _session_summary_values(
                session,
                card_count=card_count,
                reply_count=reply_count,
                completion=completion,
            )
        if not include_completion_status:
            row.pop("completionStatus", None)
        elif "completionStatus" in row and completion is None:
            row["completionStatus"] = None
        _add_question_values(
            row,
            session=session,
            questions=questions,
            answers_by_session_question=related["answersBySessionQuestion"],
        )
        if include_scores:
            _add_score_values(row, related["scoresBySession"].get(session.id, {}))
        if include_risk_flags:
            _add_risk_values(row, related["riskBySession"].get(session.id))
        rows.append(row)
    return rows


def _build_long_rows(
    *,
    event_slug: str,
    sessions: list[EventSession],
    questions: list[Question],
    answers_by_session: dict[UUID, list[Answer]],
) -> list[dict[str, Any]]:
    question_by_id = {question.id: question for question in questions}
    rows: list[dict[str, Any]] = []
    for session in sessions:
        answers = sorted(
            answers_by_session.get(session.id, []),
            key=lambda answer: question_by_id.get(answer.question_id).display_order
            if question_by_id.get(answer.question_id) is not None
            else 9999,
        )
        for answer in answers:
            question = question_by_id.get(answer.question_id)
            if question is None:
                continue
            rows.append(
                {
                    "eventSlug": event_slug,
                    "sessionShortId": _short_session_id(session),
                    "sessionStatus": session.status,
                    "questionNo": question.question_no,
                    "questionKey": question.question_key,
                    "scaleCode": question.scale_code,
                    "questionTitle": question.title,
                    "answerValue": _value_to_string(answer.answer_value),
                    "answerLabel": _answer_label(question, answer.answer_value),
                    "scoreValue": _row_value(answer.score_value),
                    "submittedAt": _row_value(answer.submitted_at),
                }
            )
    return rows


def _wide_csv_headers(
    *,
    questions: list[Question],
    include_scores: bool,
    include_risk_flags: bool,
    include_completion_status: bool,
) -> list[str]:
    headers = list(WIDE_BASE_HEADERS)
    if not include_completion_status:
        headers.remove("completion_status")
    headers.extend(_question_key(question) for question in questions)
    if include_scores:
        for scale_code, _label in SCALE_CODES:
            headers.extend([f"{scale_code}_raw_score", f"{scale_code}_severity"])
    if include_risk_flags:
        headers.extend(snake_key for _camel_key, snake_key, _label in RISK_COLUMN_DEFS)
    return headers


def _build_wide_csv_rows(
    *,
    event_slug: str,
    sessions: list[EventSession],
    questions: list[Question],
    related: dict[str, Any],
    include_scores: bool,
    include_risk_flags: bool,
    include_completion_status: bool,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for session in sessions:
        card_count = related["cardCounts"].get(session.id, 0)
        reply_count = related["replyCounts"].get(session.id, 0)
        completion = related["completionBySession"].get(session.id)
        row: dict[str, Any] = {
            "event_slug": event_slug,
            "session_short_id": _short_session_id(session),
            "session_status": session.status,
            "created_at": _row_value(session.created_at),
            "completed_at": _row_value(session.completed_at),
            "consent_accepted": status_at_least(session.status, SessionStatus.CONSENTED.value),
            "questions_completed": status_at_least(session.status, SessionStatus.QUESTIONS_COMPLETED.value),
            "summary_viewed": status_at_least(session.status, SessionStatus.SUMMARY_VIEWED.value),
            "card_count": card_count,
            "reply_created": reply_count > 0 or status_at_least(session.status, SessionStatus.REPLY_CREATED.value),
        }
        if include_completion_status:
            row["completion_status"] = _completion_status(completion)
        for question in questions:
            answer = related["answersBySessionQuestion"].get((session.id, question.id))
            row[_question_key(question)] = None if answer is None else _answer_label(question, answer.answer_value)
        if include_scores:
            scores = related["scoresBySession"].get(session.id, {})
            for scale_code, _label in SCALE_CODES:
                score = scores.get(scale_code)
                row[f"{scale_code}_raw_score"] = None if score is None else _row_value(score.raw_score)
                row[f"{scale_code}_severity"] = None if score is None else score.severity_level
        if include_risk_flags:
            risk_flag = related["riskBySession"].get(session.id)
            for _camel_key, snake_key, _label in RISK_COLUMN_DEFS:
                row[snake_key] = False if risk_flag is None else bool(getattr(risk_flag, snake_key))
        rows.append(row)
    return rows


def _build_long_csv_rows(
    *,
    event_slug: str,
    sessions: list[EventSession],
    questions: list[Question],
    answers_by_session: dict[UUID, list[Answer]],
) -> list[dict[str, Any]]:
    api_rows = _build_long_rows(
        event_slug=event_slug,
        sessions=sessions,
        questions=questions,
        answers_by_session=answers_by_session,
    )
    return [
        {
            "event_slug": row["eventSlug"],
            "session_short_id": row["sessionShortId"],
            "session_status": row["sessionStatus"],
            "question_no": row["questionNo"],
            "question_key": row["questionKey"],
            "scale_code": row["scaleCode"],
            "question_title": row["questionTitle"],
            "answer_value": row["answerValue"],
            "answer_label": row["answerLabel"],
            "score_value": row["scoreValue"],
            "submitted_at": row["submittedAt"],
        }
        for row in api_rows
    ]


def export_admin_responses_csv(
    db: SQLAlchemySession,
    *,
    event_slug: str,
    payload: AdminResponsesExportRequest,
    admin: AdminUser,
) -> CsvExportFile:
    _validate_filters(
        view=payload.format,
        status_filter=payload.status,
        created_from=payload.created_from,
        created_to=payload.created_to,
    )
    reason = payload.reason.strip()
    if not reason:
        raise AppError(ErrorCode.BAD_REQUEST, "CSV export 사유를 입력해야 합니다.")

    repo = AdminResponsesRepository(db)
    event = repo.get_event_by_slug(event_slug)
    if event is None:
        raise _event_not_found()

    filters = _session_filters(payload)
    questions = repo.list_questions_for_event(event.id)
    sessions = repo.list_sessions_for_export(event.id, filters, limit=None, offset=0)
    related = _load_related(
        repo,
        sessions,
        include_scores=payload.include_scores,
        include_risk_flags=payload.include_risk_flags,
        include_completion_status=payload.include_completion_status,
    )

    csv_service = CsvExportService()
    if payload.format == "long":
        headers = list(LONG_HEADERS)
        rows = _build_long_csv_rows(
            event_slug=event.slug,
            sessions=sessions,
            questions=questions,
            answers_by_session=related["answersBySession"],
        )
        csv_file = csv_service.build_long_csv(event_slug=event.slug, headers=headers, rows=rows)
    else:
        headers = _wide_csv_headers(
            questions=questions,
            include_scores=payload.include_scores,
            include_risk_flags=payload.include_risk_flags,
            include_completion_status=payload.include_completion_status,
        )
        rows = _build_wide_csv_rows(
            event_slug=event.slug,
            sessions=sessions,
            questions=questions,
            related=related,
            include_scores=payload.include_scores,
            include_risk_flags=payload.include_risk_flags,
            include_completion_status=payload.include_completion_status,
        )
        csv_file = csv_service.build_wide_csv(event_slug=event.slug, headers=headers, rows=rows)

    create_audit_log(
        db,
        admin_user_id=admin.id,
        event_id=event.id,
        action="responses.export",
        target_type="responses",
        target_id=None,
        before_value=None,
        after_value={
            "format": payload.format,
            "filters": {
                "status": payload.status,
                "completedOnly": payload.completed_only,
                "createdFrom": payload.created_from,
                "createdTo": payload.created_to,
            },
            "includeScores": payload.include_scores,
            "includeRiskFlags": payload.include_risk_flags,
            "includeCompletionStatus": payload.include_completion_status,
            "rowCount": len(rows),
        },
        reason=reason,
    )
    db.commit()
    return csv_file
