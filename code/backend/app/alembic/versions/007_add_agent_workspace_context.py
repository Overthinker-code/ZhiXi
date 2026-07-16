"""Add normalized conversation messages and long-lived learning context.

Revision ID: 007
Revises: 006
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("conversation_message"):
        op.create_table(
            "conversation_message",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(length=50), nullable=False),
            sa.Column("user_id", sa.String(length=50), nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.Column("legacy_chat_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("session_id", "user_id", "role", "legacy_chat_id"):
            op.create_index(f"ix_conversation_message_{column}", "conversation_message", [column])

    inspector = sa.inspect(bind)
    if not inspector.has_table("learning_context"):
        op.create_table(
            "learning_context",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.String(length=50), nullable=False),
            sa.Column("user_id", sa.String(length=50), nullable=False),
            sa.Column("current_course", sa.String(length=200), nullable=True),
            sa.Column("current_knowledge_point", sa.String(length=200), nullable=True),
            sa.Column("user_goal", sa.String(length=500), nullable=True),
            sa.Column("weak_points", sa.JSON(), nullable=False),
            sa.Column("generated_resources", sa.JSON(), nullable=False),
            sa.Column("historical_tasks", sa.JSON(), nullable=False),
            sa.Column("context_data", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_learning_context_session_id", "learning_context", ["session_id"], unique=True)
        op.create_index("ix_learning_context_user_id", "learning_context", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("learning_context"):
        op.drop_index("ix_learning_context_user_id", table_name="learning_context")
        op.drop_index("ix_learning_context_session_id", table_name="learning_context")
        op.drop_table("learning_context")
    inspector = sa.inspect(bind)
    if inspector.has_table("conversation_message"):
        for column in ("legacy_chat_id", "role", "user_id", "session_id"):
            op.drop_index(f"ix_conversation_message_{column}", table_name="conversation_message")
        op.drop_table("conversation_message")
