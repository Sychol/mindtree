from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import CompletionCodeStatus


class CompletionCode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "completion_codes"
    __table_args__ = (
        UniqueConstraint("event_id", "session_id"),
        UniqueConstraint("code"),
        Index("idx_completion_codes_event_code", "event_id", "code"),
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
    code: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=CompletionCodeStatus.ISSUED.value,
        server_default=CompletionCodeStatus.ISSUED.value,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    redeemed_by: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)
