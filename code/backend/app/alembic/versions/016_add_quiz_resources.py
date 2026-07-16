"""Add structured quiz questions and attempts.

Revision ID: 016
Revises: 015
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("question"):
        op.create_table(
            "question",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("resource_id", sa.Uuid(), nullable=False),
            sa.Column("knowledge_point", sa.String(length=160), nullable=False),
            sa.Column("question_type", sa.String(length=32), nullable=False),
            sa.Column("content", sa.String(length=2000), nullable=False),
            sa.Column("options", sa.JSON(), nullable=False),
            sa.Column("answer", sa.String(length=500), nullable=False),
            sa.Column("analysis", sa.String(length=3000), nullable=False),
            sa.Column("difficulty", sa.String(length=32), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["resource_id"], ["resource.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        for column in ("resource_id", "knowledge_point", "difficulty"):
            op.create_index(f"ix_question_{column}", "question", [column])
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("quiz_attempt"):
        op.create_table(
            "quiz_attempt",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("resource_id", sa.Uuid(), nullable=False),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("total_questions", sa.Integer(), nullable=False),
            sa.Column("correct_count", sa.Integer(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("wrong_knowledge_points", sa.JSON(), nullable=False),
            sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["resource_id"], ["resource.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_quiz_attempt_user_id", "quiz_attempt", ["user_id"])
        op.create_index("ix_quiz_attempt_resource_id", "quiz_attempt", ["resource_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("quiz_attempt"):
        op.drop_index("ix_quiz_attempt_resource_id", table_name="quiz_attempt")
        op.drop_index("ix_quiz_attempt_user_id", table_name="quiz_attempt")
        op.drop_table("quiz_attempt")
    if inspector.has_table("question"):
        for column in ("difficulty", "knowledge_point", "resource_id"):
            op.drop_index(f"ix_question_{column}", table_name="question")
        op.drop_table("question")
