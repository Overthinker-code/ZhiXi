"""Limit each user to one active resource run.

Revision ID: 022
Revises: 021
Create Date: 2026-07-12
"""

from alembic import op
import sqlalchemy as sa


revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    indexes = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes("resource_generation_run")
    }
    if "uq_resource_generation_run_active_user" in indexes:
        return
    op.execute(
        "CREATE UNIQUE INDEX uq_resource_generation_run_active_user "
        "ON resource_generation_run (user_id) "
        "WHERE status IN ('requested', 'running')"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_resource_generation_run_active_user")
