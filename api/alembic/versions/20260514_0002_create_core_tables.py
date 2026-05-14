"""create core tables

Revision ID: 20260514_0002
Revises:
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260514_0002"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), server_default="draft", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_version", sa.String(), server_default="v1", nullable=False),
        sa.Column("settings", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_events_slug"),
    )

    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), server_default="operator", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_admin_users_email"),
    )

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("anonymous_key_hash", sa.String(), nullable=False),
        sa.Column("resume_token_hash", sa.String(), nullable=True),
        sa.Column("status", sa.String(), server_default="created", nullable=False),
        sa.Column("last_step", sa.String(), nullable=True),
        sa.Column("client_meta", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_sessions_event_id_events"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "anonymous_key_hash", name="uq_sessions_event_id_anonymous_key_hash"),
    )
    op.create_index("idx_sessions_event_status", "sessions", ["event_id", "status"])

    op.create_table(
        "questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_no", sa.Integer(), nullable=False),
        sa.Column("scale_code", sa.String(), nullable=False),
        sa.Column("question_key", sa.String(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("question_type", sa.String(), nullable=False),
        sa.Column("options", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("score_map", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_questions_event_id_events"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "question_key", name="uq_questions_event_id_question_key"),
        sa.UniqueConstraint("event_id", "question_no", name="uq_questions_event_id_question_no"),
    )
    op.create_index("idx_questions_event_order", "questions", ["event_id", "display_order"])

    op.create_table(
        "consent_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_version", sa.String(), nullable=False),
        sa.Column("accepted_items", postgresql.JSONB(), nullable=False),
        sa.Column("ip_hash", sa.String(), nullable=True),
        sa.Column("user_agent_hash", sa.String(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_consent_logs_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_consent_logs_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_consent_logs_session", "consent_logs", ["session_id"])

    op.create_table(
        "answers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("answer_value", postgresql.JSONB(), nullable=False),
        sa.Column("score_value", sa.Numeric(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_answers_event_id_events"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], name="fk_answers_question_id_questions"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_answers_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "question_id", name="uq_answers_session_id_question_id"),
    )
    op.create_index("idx_answers_session", "answers", ["session_id"])

    op.create_table(
        "scale_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scale_code", sa.String(), nullable=False),
        sa.Column("raw_score", sa.Numeric(), nullable=False),
        sa.Column("severity_level", sa.String(), nullable=True),
        sa.Column("sub_scores", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("rule_version", sa.String(), server_default="v1", nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_scale_scores_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_scale_scores_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "scale_code", name="uq_scale_scores_session_id_scale_code"),
    )
    op.create_index("idx_scale_scores_session", "scale_scores", ["session_id"])

    op.create_table(
        "risk_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phq9_item9_positive", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("crisis_expression_detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("trauma_high_signal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("moral_injury_high_signal", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("public_restriction", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("help_notice_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("rule_version", sa.String(), server_default="v1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_risk_flags_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_risk_flags_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_risk_flags_session_id"),
    )
    op.create_index("idx_risk_flags_session", "risk_flags", ["session_id"])
    op.create_index("idx_risk_flags_event", "risk_flags", ["event_id", "public_restriction", "help_notice_required"])

    op.create_table(
        "summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("llm_text", sa.Text(), nullable=True),
        sa.Column("final_text", sa.Text(), nullable=False),
        sa.Column("generation_mode", sa.String(), server_default="template", nullable=False),
        sa.Column("llm_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_summaries_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_summaries_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_summaries_session_id"),
    )

    op.create_table(
        "mind_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_type", sa.String(), nullable=False),
        sa.Column("content_raw", sa.Text(), nullable=False),
        sa.Column("content_redacted", sa.Text(), nullable=True),
        sa.Column("safety_status", sa.String(), server_default="review", nullable=False),
        sa.Column("public_status", sa.String(), server_default="pending", nullable=False),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_mind_cards_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_mind_cards_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_mind_cards_event_public", "mind_cards", ["event_id", "safety_status", "public_status", "created_at"])

    op.create_table(
        "card_selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_card_selections_event_id_events"),
        sa.ForeignKeyConstraint(["selected_card_id"], ["mind_cards.id"], name="fk_card_selections_selected_card_id_mind_cards"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_card_selections_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_card_selections_session_id"),
    )

    op.create_table(
        "replies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reply_type", sa.String(), nullable=False),
        sa.Column("content_raw", sa.Text(), nullable=False),
        sa.Column("content_redacted", sa.Text(), nullable=True),
        sa.Column("safety_status", sa.String(), server_default="review", nullable=False),
        sa.Column("public_status", sa.String(), server_default="pending", nullable=False),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_replies_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_replies_session_id_sessions"),
        sa.ForeignKeyConstraint(["target_card_id"], ["mind_cards.id"], name="fk_replies_target_card_id_mind_cards"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_replies_event_public", "replies", ["event_id", "safety_status", "public_status", "created_at"])

    op.create_table(
        "keyword_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="2", nullable=False),
        sa.Column("provider", sa.String(), nullable=True),
        sa.Column("fallback_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("output_snapshot", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_keyword_jobs_event_id_events"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_keyword_jobs_status", "keyword_jobs", ["status", "next_run_at", "created_at"])

    op.create_table(
        "keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword_text", sa.String(), nullable=False),
        sa.Column("normalized_keyword", sa.String(), nullable=False),
        sa.Column("category", sa.String(), server_default="neutral", nullable=False),
        sa.Column("weight", sa.Numeric(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(), server_default="active", nullable=False),
        sa.Column("extraction_method", sa.String(), server_default="fallback", nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_keywords_event_id_events"),
        sa.ForeignKeyConstraint(["job_id"], ["keyword_jobs.id"], name="fk_keywords_job_id_keyword_jobs"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_keywords_event_status", "keywords", ["event_id", "status", "normalized_keyword"])
    op.create_index("idx_keywords_event_status_category", "keywords", ["event_id", "status", "category"])

    op.create_table(
        "completion_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="issued", nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_completion_codes_event_id_events"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], name="fk_completion_codes_session_id_sessions"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_completion_codes_code"),
        sa.UniqueConstraint("event_id", "session_id", name="uq_completion_codes_event_id_session_id"),
    )
    op.create_index("idx_completion_codes_event_code", "completion_codes", ["event_id", "code"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_value", postgresql.JSONB(), nullable=True),
        sa.Column("after_value", postgresql.JSONB(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], name="fk_admin_audit_logs_admin_user_id_admin_users"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_admin_audit_logs_event_id_events"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_admin_audit_logs_event_created", "admin_audit_logs", ["event_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_admin_audit_logs_event_created", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_index("idx_completion_codes_event_code", table_name="completion_codes")
    op.drop_table("completion_codes")
    op.drop_index("idx_keywords_event_status_category", table_name="keywords")
    op.drop_index("idx_keywords_event_status", table_name="keywords")
    op.drop_table("keywords")
    op.drop_index("idx_keyword_jobs_status", table_name="keyword_jobs")
    op.drop_table("keyword_jobs")
    op.drop_index("idx_replies_event_public", table_name="replies")
    op.drop_table("replies")
    op.drop_table("card_selections")
    op.drop_index("idx_mind_cards_event_public", table_name="mind_cards")
    op.drop_table("mind_cards")
    op.drop_table("summaries")
    op.drop_index("idx_risk_flags_event", table_name="risk_flags")
    op.drop_index("idx_risk_flags_session", table_name="risk_flags")
    op.drop_table("risk_flags")
    op.drop_index("idx_scale_scores_session", table_name="scale_scores")
    op.drop_table("scale_scores")
    op.drop_index("idx_answers_session", table_name="answers")
    op.drop_table("answers")
    op.drop_index("idx_consent_logs_session", table_name="consent_logs")
    op.drop_table("consent_logs")
    op.drop_index("idx_questions_event_order", table_name="questions")
    op.drop_table("questions")
    op.drop_index("idx_sessions_event_status", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("admin_users")
    op.drop_table("events")
