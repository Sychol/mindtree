from __future__ import annotations

from sqlalchemy.orm import Session as SQLAlchemySession

from app.models.card import MindCard
from app.models.enums import KeywordSourceType, PublicStatus, SafetyStatus
from app.models.keyword import KeywordJob
from app.models.reply import Reply
from app.repositories.keyword_jobs import KeywordJobRepository


def _should_create_job(safety_status: str, public_status: str) -> bool:
    return safety_status in {SafetyStatus.SAFE.value, SafetyStatus.REVIEW.value} and (
        public_status != PublicStatus.EXCLUDED.value
    )


def create_keyword_job_for_card(
    db: SQLAlchemySession,
    card: MindCard,
) -> KeywordJob | None:
    if not _should_create_job(card.safety_status, card.public_status):
        return None

    content_for_length = card.content_redacted or card.content_raw
    return KeywordJobRepository(db).create_pending_job(
        event_id=card.event_id,
        source_type=KeywordSourceType.MIND_CARD.value,
        source_id=card.id,
        input_snapshot={
            "source_type": KeywordSourceType.MIND_CARD.value,
            "source_id": str(card.id),
            "prompt_type": card.prompt_type,
            "content_length": len(content_for_length),
            "safety_status": card.safety_status,
            "public_status": card.public_status,
        },
    )


def create_keyword_job_for_reply(
    db: SQLAlchemySession,
    reply: Reply,
) -> KeywordJob | None:
    if not _should_create_job(reply.safety_status, reply.public_status):
        return None

    content_for_length = reply.content_redacted or reply.content_raw
    return KeywordJobRepository(db).create_pending_job(
        event_id=reply.event_id,
        source_type=KeywordSourceType.REPLY.value,
        source_id=reply.id,
        input_snapshot={
            "source_type": KeywordSourceType.REPLY.value,
            "source_id": str(reply.id),
            "reply_type": reply.reply_type,
            "content_length": len(content_for_length),
            "safety_status": reply.safety_status,
            "public_status": reply.public_status,
        },
    )
