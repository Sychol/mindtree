from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PublicStatus, ReplyType, SafetyStatus


class Reply(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "replies"
    __table_args__ = (
        Index(
            "idx_replies_event_public",
            "event_id",
            "safety_status",
            "public_status",
            "created_at",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=False,
    )
    target_card_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mind_cards.id"),
        nullable=False,
    )
    reply_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ReplyType.COMFORT.value,
    )
    content_raw: Mapped[str] = mapped_column(Text, nullable=False)
    content_redacted: Mapped[str | None] = mapped_column(Text)
    safety_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=SafetyStatus.REVIEW.value,
        server_default=SafetyStatus.REVIEW.value,
    )
    public_status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=PublicStatus.PENDING.value,
        server_default=PublicStatus.PENDING.value,
    )
    moderation_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True))
