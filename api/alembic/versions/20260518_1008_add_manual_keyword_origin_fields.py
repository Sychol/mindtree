"""add manual keyword origin fields

Revision ID: 20260518_1008
Revises: 20260514_0002
Create Date: 2026-05-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_1008"
down_revision: str | None = "20260514_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "keywords",
        sa.Column("origin", sa.Text(), server_default="participant", nullable=False),
    )
    op.add_column("keywords", sa.Column("origin_tag", sa.Text(), nullable=True))
    op.add_column(
        "keywords",
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_keywords_created_by_admin_id_admin_users",
        "keywords",
        "admin_users",
        ["created_by_admin_id"],
        ["id"],
    )
    op.alter_column(
        "keywords",
        "source_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.execute("UPDATE keywords SET origin = 'participant' WHERE origin IS NULL")
    op.create_index(
        "idx_keywords_event_origin_status",
        "keywords",
        ["event_id", "origin", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_keywords_event_origin_status", table_name="keywords")
    op.alter_column(
        "keywords",
        "source_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint(
        "fk_keywords_created_by_admin_id_admin_users",
        "keywords",
        type_="foreignkey",
    )
    op.drop_column("keywords", "created_by_admin_id")
    op.drop_column("keywords", "origin_tag")
    op.drop_column("keywords", "origin")
