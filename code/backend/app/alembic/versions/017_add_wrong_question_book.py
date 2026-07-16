"""Add personal wrong question book.

Revision ID: 017
Revises: 016
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("wrong_question"):
        return
    op.create_table(
        "wrong_question",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("source_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("wrong_count", sa.Integer(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("mastered", sa.Boolean(), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["question.id"]),
        sa.ForeignKeyConstraint(["source_attempt_id"], ["quiz_attempt.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "question_id", name="uq_wrong_question_user_question"),
    )
    for column in ("user_id", "question_id", "source_attempt_id", "is_favorite", "mastered"):
        op.create_index(f"ix_wrong_question_{column}", "wrong_question", [column])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("wrong_question"):
        return
    for column in ("mastered", "is_favorite", "source_attempt_id", "question_id", "user_id"):
        op.drop_index(f"ix_wrong_question_{column}", table_name="wrong_question")
    op.drop_table("wrong_question")
