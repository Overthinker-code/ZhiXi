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
    op.add_column('chat_thread', sa.Column('user_id', sa.String(50), nullable=True))
    op.create_index(op.f('ix_chat_thread_user_id'), 'chat_thread', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_thread_user_id'), table_name='chat_thread')
    op.drop_column('chat_thread', 'user_id')
