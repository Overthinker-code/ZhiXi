"""Add auditable incremental profile update events.

Revision ID: 009
Revises: 008
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("agent_profile_update_event"):
        return
    op.create_table(
        "agent_profile_update_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("message_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("alpha", sa.Float(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("profile_patch", sa.JSON(), nullable=False),
        sa.Column("before_snapshot", sa.JSON(), nullable=False),
        sa.Column("after_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "session_id", "message_id"):
        op.create_index(
            f"ix_agent_profile_update_event_{column}",
            "agent_profile_update_event",
            [column],
        )


def downgrade() -> None:
    for column in ("message_id", "session_id", "user_id"):
        op.drop_index(
            f"ix_agent_profile_update_event_{column}",
            table_name="agent_profile_update_event",
        )
    op.drop_table("agent_profile_update_event")
