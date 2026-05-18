from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    ContentOrigin,
    KeywordCategory,
    KeywordExtractionMethod,
    KeywordJobStatus,
    KeywordStatus,
)


class KeywordJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "keyword_jobs"
    __table_args__ = (
        Index("idx_keyword_jobs_status", "status", "next_run_at", "created_at"),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=KeywordJobStatus.PENDING.value,
        server_default=KeywordJobStatus.PENDING.value,
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=2, server_default="2")
    provider: Mapped[str | None] = mapped_column(String)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Keyword(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "keywords"
    __table_args__ = (
        Index("idx_keywords_event_status", "event_id", "status", "normalized_keyword"),
        Index("idx_keywords_event_status_category", "event_id", "status", "category"),
        Index("idx_keywords_event_origin_status", "event_id", "origin", "status"),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True))
    keyword_text: Mapped[str] = mapped_column(String, nullable=False)
    normalized_keyword: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=KeywordCategory.NEUTRAL.value,
        server_default=KeywordCategory.NEUTRAL.value,
    )
    weight: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=Decimal("1"), server_default="1")
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=KeywordStatus.ACTIVE.value,
        server_default=KeywordStatus.ACTIVE.value,
    )
    extraction_method: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=KeywordExtractionMethod.FALLBACK.value,
        server_default=KeywordExtractionMethod.FALLBACK.value,
    )
    job_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("keyword_jobs.id"),
    )
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
