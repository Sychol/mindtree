from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ConsentLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "consent_logs"
    __table_args__ = (
        Index("idx_consent_logs_session", "session_id"),
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
    consent_version: Mapped[str] = mapped_column(String, nullable=False)
    accepted_items: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String)
    user_agent_hash: Mapped[str | None] = mapped_column(String)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
