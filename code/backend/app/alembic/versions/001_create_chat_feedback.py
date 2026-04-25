"""create chat_feedback table

Revision ID: 001
Revises: 
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("chat_feedback"):
        op.create_table(
            "chat_feedback",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("record_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.String(50), nullable=True),
            sa.Column("rating", sa.String(10), nullable=False),
            sa.Column("prompt_key", sa.String(50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.ForeignKeyConstraint(["record_id"], ["chat.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("chat_feedback")}
    if op.f("ix_chat_feedback_id") not in existing_indexes:
        op.create_index(op.f("ix_chat_feedback_id"), "chat_feedback", ["id"], unique=False)
    if op.f("ix_chat_feedback_record_id") not in existing_indexes:
        op.create_index(
            op.f("ix_chat_feedback_record_id"),
            "chat_feedback",
            ["record_id"],
            unique=False,
        )
    if op.f("ix_chat_feedback_user_id") not in existing_indexes:
        op.create_index(
            op.f("ix_chat_feedback_user_id"),
            "chat_feedback",
            ["user_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("chat_feedback"):
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("chat_feedback")}
        if op.f("ix_chat_feedback_user_id") in existing_indexes:
            op.drop_index(op.f("ix_chat_feedback_user_id"), table_name="chat_feedback")
        if op.f("ix_chat_feedback_record_id") in existing_indexes:
            op.drop_index(op.f("ix_chat_feedback_record_id"), table_name="chat_feedback")
        if op.f("ix_chat_feedback_id") in existing_indexes:
            op.drop_index(op.f("ix_chat_feedback_id"), table_name="chat_feedback")
        op.drop_table("chat_feedback")
