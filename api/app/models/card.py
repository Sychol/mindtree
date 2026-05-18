from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ContentOrigin, PublicStatus, SafetyStatus


class MindCard(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "mind_cards"
    __table_args__ = (
        Index(
            "idx_mind_cards_event_public",
            "event_id",
            "safety_status",
            "public_status",
            "created_at",
        ),
        Index("idx_mind_cards_event_origin", "event_id", "origin"),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    session_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=True,
    )
    prompt_type: Mapped[str] = mapped_column(String, nullable=False)
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
    origin: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=ContentOrigin.PARTICIPANT.value,
        server_default=ContentOrigin.PARTICIPANT.value,
    )
    origin_tag: Mapped[str | None] = mapped_column(Text)
    created_by_admin_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("admin_users.id"),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True))


class CardSelection(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "card_selections"
    __table_args__ = (
        UniqueConstraint("session_id"),
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
    selected_card_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("mind_cards.id"),
        nullable=False,
    )
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
