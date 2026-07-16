"""Persist course graph node workflow actions.

Revision ID: 024
Revises: 023
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("course_knowledge_node_action"):
        return
    op.create_table(
        "course_knowledge_node_action",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column(
            "node_id",
            sa.Uuid(),
            sa.ForeignKey("course_knowledge_node.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "user_id", "node_id", "action_type",
            name="uq_course_knowledge_node_action_user_node_type",
        ),
    )
    for name in ("user_id", "course_id", "node_id", "action_type"):
        op.create_index(
            f"ix_course_knowledge_node_action_{name}",
            "course_knowledge_node_action",
            [name],
        )


def downgrade() -> None:
    op.drop_table("course_knowledge_node_action")
