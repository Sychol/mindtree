from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SessionStatus


class Session(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("event_id", "anonymous_key_hash"),
        Index("idx_sessions_event_status", "event_id", "status"),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    anonymous_key_hash: Mapped[str] = mapped_column(String, nullable=False)
    resume_token_hash: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=SessionStatus.CREATED.value,
        server_default=SessionStatus.CREATED.value,
    )
    last_step: Mapped[str | None] = mapped_column(String)
    client_meta: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
