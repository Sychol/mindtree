from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ScaleScore(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "scale_scores"
    __table_args__ = (
        UniqueConstraint("session_id", "scale_code"),
        Index("idx_scale_scores_session", "session_id"),
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
    scale_code: Mapped[str] = mapped_column(String, nullable=False)
    raw_score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    severity_level: Mapped[str | None] = mapped_column(String)
    sub_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    rule_version: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="v1",
        server_default="v1",
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
