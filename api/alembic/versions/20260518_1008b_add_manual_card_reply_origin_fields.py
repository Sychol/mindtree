"""add manual card reply origin fields

Revision ID: 20260518_1008b
Revises: 20260518_1008
Create Date: 2026-05-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260518_1008b"
down_revision: str | None = "20260518_1008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mind_cards",
        sa.Column("origin", sa.Text(), server_default="participant", nullable=False),
    )
    op.add_column("mind_cards", sa.Column("origin_tag", sa.Text(), nullable=True))
    op.add_column(
        "mind_cards",
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_mind_cards_created_by_admin_id_admin_users",
        "mind_cards",
        "admin_users",
        ["created_by_admin_id"],
        ["id"],
    )
    op.alter_column(
        "mind_cards",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.execute("UPDATE mind_cards SET origin = 'participant' WHERE origin IS NULL")
    op.create_index(
        "idx_mind_cards_event_origin",
        "mind_cards",
        ["event_id", "origin"],
    )

    op.add_column(
        "replies",
        sa.Column("origin", sa.Text(), server_default="participant", nullable=False),
    )
    op.add_column("replies", sa.Column("origin_tag", sa.Text(), nullable=True))
    op.add_column(
        "replies",
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_replies_created_by_admin_id_admin_users",
        "replies",
        "admin_users",
        ["created_by_admin_id"],
        ["id"],
    )
    op.alter_column(
        "replies",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "replies",
        "target_card_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.execute("UPDATE replies SET origin = 'participant' WHERE origin IS NULL")
    op.create_index(
        "idx_replies_event_origin",
        "replies",
        ["event_id", "origin"],
    )


def downgrade() -> None:
    op.drop_index("idx_replies_event_origin", table_name="replies")
    op.alter_column(
        "replies",
        "target_card_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "replies",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint(
        "fk_replies_created_by_admin_id_admin_users",
        "replies",
        type_="foreignkey",
    )
    op.drop_column("replies", "created_by_admin_id")
    op.drop_column("replies", "origin_tag")
    op.drop_column("replies", "origin")

    op.drop_index("idx_mind_cards_event_origin", table_name="mind_cards")
    op.alter_column(
        "mind_cards",
        "session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_constraint(
        "fk_mind_cards_created_by_admin_id_admin_users",
        "mind_cards",
        type_="foreignkey",
    )
    op.drop_column("mind_cards", "created_by_admin_id")
    op.drop_column("mind_cards", "origin_tag")
    op.drop_column("mind_cards", "origin")
