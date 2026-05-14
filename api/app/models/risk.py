from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "risk_flags"
    __table_args__ = (
        UniqueConstraint("session_id"),
        Index("idx_risk_flags_session", "session_id"),
        Index("idx_risk_flags_event", "event_id", "public_restriction", "help_notice_required"),
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
    phq9_item9_positive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    crisis_expression_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    trauma_high_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    moral_injury_high_signal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    public_restriction: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    help_notice_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    rule_version: Mapped[str] = mapped_column(String, nullable=False, default="v1", server_default="v1")
