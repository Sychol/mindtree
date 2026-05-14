from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import QuestionType, ScaleCode


class Question(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("event_id", "question_no"),
        UniqueConstraint("event_id", "question_key"),
        Index("idx_questions_event_order", "event_id", "display_order"),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("events.id"),
        nullable=False,
    )
    question_no: Mapped[int] = mapped_column(Integer, nullable=False)
    scale_code: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=ScaleCode.PROFILE.value,
    )
    question_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default=QuestionType.SINGLE_SELECT.value,
    )
    options: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    score_map: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
