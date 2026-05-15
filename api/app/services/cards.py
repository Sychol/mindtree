from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.models.card import CardSelection, MindCard
from app.models.enums import PublicStatus, SafetyStatus, SessionStatus
from app.models.event import Event
from app.models.keyword import KeywordJob
from app.models.session import Session as EventSession
from app.repositories.card_selections import CardSelectionRepository
from app.repositories.cards import MindCardRepository
from app.repositories.events import EventRepository
from app.repositories.risk_flags import RiskFlagRepository
from app.repositories.sessions import SessionRepository
from app.schemas.cards import (
    CreateMindCardRequest,
    CreateMindCardResponse,
    KeywordJobPayload,
    MindCardPayload,
    MyMindCardsResponse,
    PublicMindCardPayload,
    PublicMindCardsResponse,
    SelectCardRequest,
    SelectCardResponse,
)
from app.services.keyword_job_factory import create_keyword_job_for_card
from app.services.safety_filter import evaluate_safety
from app.services.sessions import status_at_least

ALLOWED_PROMPT_TYPES = {
    "to_past_me",
    "to_now_me",
    "to_colleague",
    "stress_memory",
}
PROMPT_TYPE_ALIASES = {
    "to_current_me": "to_now_me",
}
MAX_CONTENT_LENGTH = 300
PUBLIC_CARD_EMPTY_MESSAGE = (
    "아직 공개 가능한 카드가 충분하지 않습니다. 잠시 후 다시 시도하거나 다음 안내를 확인해 주세요."
)


def _session_and_event_or_raise(
    db: SQLAlchemySession,
    session_id: UUID,
) -> tuple[EventSession, Event]:
    row = SessionRepository(db).get_session_and_event_by_id(session_id)
    if row is None:
        raise AppError(
            ErrorCode.SESSION_NOT_FOUND,
            "세션을 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return row


def _event_or_raise(db: SQLAlchemySession, event_slug: str) -> Event:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    return event


def _ensure_min_status(session: EventSession, required_status: str) -> None:
    if not status_at_least(session.status, required_status):
        raise AppError(
            ErrorCode.INVALID_SESSION_STATUS,
            "현재 세션 상태에서는 이 단계를 진행할 수 없습니다.",
            status.HTTP_409_CONFLICT,
            details={"status": session.status, "requiredStatus": required_status},
        )


def _validate_content(content: str) -> str:
    normalized = content.strip()
    if not normalized:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "내용을 입력해 주세요.",
            status.HTTP_400_BAD_REQUEST,
        )
    if len(normalized) > MAX_CONTENT_LENGTH:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "내용은 300자 이내로 입력해 주세요.",
            status.HTTP_400_BAD_REQUEST,
            details={"maxLength": MAX_CONTENT_LENGTH},
        )
    return normalized


def _normalize_prompt_type(prompt_type: str) -> str:
    normalized = PROMPT_TYPE_ALIASES.get(prompt_type, prompt_type)
    if normalized not in ALLOWED_PROMPT_TYPES:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "허용되지 않는 마음카드 유형입니다.",
            status.HTTP_400_BAD_REQUEST,
            details={"promptType": prompt_type},
        )
    return normalized


def _card_payload(card: MindCard) -> MindCardPayload:
    return MindCardPayload(
        id=card.id,
        prompt_type=card.prompt_type,
        content=card.content_redacted or card.content_raw,
        safety_status=card.safety_status,
        public_status=card.public_status,
        created_at=card.created_at,
    )


def _keyword_job_payload(job: KeywordJob | None) -> KeywordJobPayload | None:
    if job is None:
        return None
    return KeywordJobPayload(id=job.id, status=job.status)


def create_mind_card(
    db: SQLAlchemySession,
    session_id: UUID,
    payload: CreateMindCardRequest,
) -> CreateMindCardResponse:
    session, event = _session_and_event_or_raise(db, session_id)
    _ensure_min_status(session, SessionStatus.SUMMARY_VIEWED.value)

    prompt_type = _normalize_prompt_type(payload.prompt_type)
    content = _validate_content(payload.content)
    safety_result = evaluate_safety("mind_card", content)

    card = MindCardRepository(db).create_card(
        event_id=event.id,
        session_id=session.id,
        prompt_type=prompt_type,
        content_raw=content,
        content_redacted=safety_result.content_redacted,
        safety_status=safety_result.safety_status,
        public_status=safety_result.public_status,
        moderation_reason=safety_result.moderation_reason,
    )

    if safety_result.crisis_expression_detected:
        RiskFlagRepository(db).mark_crisis_expression_detected(
            event_id=event.id,
            session_id=session.id,
            reason=safety_result.moderation_reason or "crisis_expression",
        )

    keyword_job = create_keyword_job_for_card(db, card)

    if session.status == SessionStatus.SUMMARY_VIEWED.value:
        SessionRepository(db).set_status_and_step(
            session,
            SessionStatus.CARD_CREATED.value,
            "cards/select",
        )
    elif status_at_least(session.status, SessionStatus.CARD_CREATED.value):
        session.last_step = session.last_step or "cards/select"
        db.add(session)
        db.flush()

    db.commit()
    db.refresh(card)
    if keyword_job is not None:
        db.refresh(keyword_job)
    db.refresh(session)

    return CreateMindCardResponse(
        card=_card_payload(card),
        keyword_job=_keyword_job_payload(keyword_job),
        session_status=session.status,
    )


def list_my_cards(
    db: SQLAlchemySession,
    session_id: UUID,
) -> MyMindCardsResponse:
    _session_and_event_or_raise(db, session_id)
    cards = MindCardRepository(db).list_by_session_id(session_id)
    return MyMindCardsResponse(cards=[_card_payload(card) for card in cards])


def list_public_cards(
    db: SQLAlchemySession,
    *,
    event_slug: str,
    exclude_session_id: UUID | None,
    limit: int,
) -> PublicMindCardsResponse:
    event = _event_or_raise(db, event_slug)
    safe_limit = max(1, min(limit, 30))
    cards = MindCardRepository(db).list_public_cards(
        event_id=event.id,
        exclude_session_id=exclude_session_id,
        limit=safe_limit,
    )
    return PublicMindCardsResponse(
        cards=[
            PublicMindCardPayload(
                id=card.id,
                prompt_type=card.prompt_type,
                content=card.content_redacted or card.content_raw,
                created_at=card.created_at,
            )
            for card in cards
        ],
        fallback_used=not cards,
        message=PUBLIC_CARD_EMPTY_MESSAGE if not cards else None,
    )


def _validate_selectable_card(
    db: SQLAlchemySession,
    *,
    session: EventSession,
    card_id: UUID,
) -> MindCard:
    card = MindCardRepository(db).get_by_id(card_id)
    if card is None:
        raise AppError(
            ErrorCode.CARD_NOT_FOUND,
            "선택할 카드를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )
    if card.event_id != session.event_id:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "같은 이벤트의 카드만 선택할 수 있습니다.",
            status.HTTP_400_BAD_REQUEST,
        )
    if card.session_id == session.id:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "본인이 작성한 카드는 선택할 수 없습니다.",
            status.HTTP_400_BAD_REQUEST,
        )
    if card.safety_status != SafetyStatus.SAFE.value or card.public_status != PublicStatus.PUBLIC.value:
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "공개 가능한 카드만 선택할 수 있습니다.",
            status.HTTP_400_BAD_REQUEST,
        )

    risk_flag = RiskFlagRepository(db).get_by_session_id(card.session_id)
    if risk_flag and (risk_flag.public_restriction or risk_flag.crisis_expression_detected):
        raise AppError(
            ErrorCode.BAD_REQUEST,
            "공개 제한된 카드는 선택할 수 없습니다.",
            status.HTTP_400_BAD_REQUEST,
        )

    return card


def select_peer_card(
    db: SQLAlchemySession,
    session_id: UUID,
    payload: SelectCardRequest,
) -> SelectCardResponse:
    session, _event = _session_and_event_or_raise(db, session_id)
    _ensure_min_status(session, SessionStatus.CARD_CREATED.value)
    selected_card = _validate_selectable_card(
        db,
        session=session,
        card_id=payload.selected_card_id,
    )

    selection = CardSelectionRepository(db).upsert_selection(
        event_id=selected_card.event_id,
        session_id=session.id,
        selected_card_id=selected_card.id,
    )
    db.commit()
    db.refresh(selection)

    return SelectCardResponse(
        selected_card_id=selection.selected_card_id,
        selected_at=selection.selected_at,
    )
