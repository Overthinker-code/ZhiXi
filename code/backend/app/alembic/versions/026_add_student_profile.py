"""Add the persistent AI learner digital-twin snapshot.

Revision ID: 027
Revises: 026
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("student_profile"):
        return
    op.create_table(
        "student_profile",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("learning_stage", sa.String(80), nullable=False, server_default="画像形成期"),
        sa.Column("learning_goal", sa.String(500), nullable=False, server_default=""),
        sa.Column("learning_style", sa.String(160), nullable=False, server_default="持续观察型"),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("knowledge_state", sa.JSON(), nullable=False),
        sa.Column("learning_behavior", sa.JSON(), nullable=False),
        sa.Column("learning_preference", sa.JSON(), nullable=False),
        sa.Column("cognitive_style", sa.String(160), nullable=False, server_default="持续观察中"),
        sa.Column("knowledge_graph", sa.JSON(), nullable=False),
        sa.Column("dimension_scores", sa.JSON(), nullable=False),
        sa.Column("ai_summary", sa.String(4000), nullable=False, server_default=""),
        sa.Column("last_updates", sa.JSON(), nullable=False),
        sa.Column("evidence_cursor", sa.JSON(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_student_profile_user_id"),
    )
    op.create_index("ix_student_profile_user_id", "student_profile", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("student_profile")
