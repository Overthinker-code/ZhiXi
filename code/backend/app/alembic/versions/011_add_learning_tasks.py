"""Add current learning tasks.

Revision ID: 011
Revises: 010
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("learning_task"):
        return
    op.create_table(
        "learning_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=False),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_stage", sa.String(length=100), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "session_id", "status"):
        op.create_index(f"ix_learning_task_{column}", "learning_task", [column])


def downgrade() -> None:
    for column in ("status", "session_id", "user_id"):
        op.drop_index(f"ix_learning_task_{column}", table_name="learning_task")
    op.drop_table("learning_task")
