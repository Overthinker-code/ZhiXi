"""Upgrade chat threads into learning sessions.

Revision ID: 008
Revises: 007
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("chatthread")}
    additions = (
        ("course", sa.String(length=200), True),
        ("knowledge_point", sa.String(length=200), True),
        ("intent", sa.String(length=80), True),
        ("session_status", sa.String(length=20), True),
        ("session_metadata", sa.JSON(), True),
        ("last_message_at", sa.DateTime(timezone=True), True),
    )
    for name, column_type, nullable in additions:
        if name not in columns:
            op.add_column("chatthread", sa.Column(name, column_type, nullable=nullable))
    op.execute("UPDATE chatthread SET session_status = 'active' WHERE session_status IS NULL")
    op.execute("UPDATE chatthread SET session_metadata = '{}' WHERE session_metadata IS NULL")
    op.alter_column("chatthread", "session_status", nullable=False)
    op.alter_column("chatthread", "session_metadata", nullable=False)
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("chatthread")}
    for column in ("course", "knowledge_point", "intent", "session_status", "last_message_at"):
        name = f"ix_chatthread_{column}"
        if name not in indexes:
            op.create_index(name, "chatthread", [column])


def downgrade() -> None:
    for column in ("last_message_at", "session_status", "intent", "knowledge_point", "course"):
        op.drop_index(f"ix_chatthread_{column}", table_name="chatthread")
    for column in ("last_message_at", "session_metadata", "session_status", "intent", "knowledge_point", "course"):
        op.drop_column("chatthread", column)
