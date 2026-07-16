"""add user_id to chat_thread

Revision ID: 002
Revises: 001
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa


revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("chat_thread"):
        return

    existing_columns = {col["name"] for col in inspector.get_columns("chat_thread")}
    if "user_id" not in existing_columns:
        op.add_column("chat_thread", sa.Column("user_id", sa.String(50), nullable=True))

    inspector = sa.inspect(bind)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("chat_thread")}
    if op.f("ix_chat_thread_user_id") not in existing_indexes:
        op.create_index(op.f("ix_chat_thread_user_id"), "chat_thread", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("chat_thread"):
        return

    existing_indexes = {idx["name"] for idx in inspector.get_indexes("chat_thread")}
    if op.f("ix_chat_thread_user_id") in existing_indexes:
        op.drop_index(op.f("ix_chat_thread_user_id"), table_name="chat_thread")

    existing_columns = {col["name"] for col in inspector.get_columns("chat_thread")}
    if "user_id" in existing_columns:
        op.drop_column("chat_thread", "user_id")
