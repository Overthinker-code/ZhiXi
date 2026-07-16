"""Auto-collect existing wrong-question records.

Revision ID: 019
Revises: 018
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("wrong_question"):
        op.execute(sa.text("UPDATE wrong_question SET is_favorite = TRUE"))


def downgrade() -> None:
    pass
