from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Summary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "summaries"
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
    template_text: Mapped[str] = mapped_column(Text, nullable=False)
    llm_text: Mapped[str | None] = mapped_column(Text)
    final_text: Mapped[str] = mapped_column(Text, nullable=False)
    generation_mode: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="template",
        server_default="template",
    )
    llm_job_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
