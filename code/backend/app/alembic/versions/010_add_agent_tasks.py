"""Add persistent Agent workflow tasks.

Revision ID: 010
Revises: 009
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("agent_task"):
        return
    op.create_table(
        "agent_task",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("task_key", sa.String(length=50), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "task_key", name="uq_agent_task_run_key"),
    )
    for column in ("session_id", "user_id", "run_id", "status"):
        op.create_index(f"ix_agent_task_{column}", "agent_task", [column])


def downgrade() -> None:
    for column in ("status", "run_id", "user_id", "session_id"):
        op.drop_index(f"ix_agent_task_{column}", table_name="agent_task")
    op.drop_table("agent_task")
