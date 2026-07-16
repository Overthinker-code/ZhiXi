"""Add idempotency and execution lease fields to resource runs.

Revision ID: 025
Revises: 024
Create Date: 2026-07-14
"""

from alembic import op
import sqlalchemy as sa


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {
        column["name"]
        for column in inspector.get_columns("resource_generation_run")
    }
    indexes = {
        item["name"]
        for item in inspector.get_indexes("resource_generation_run")
    }
    if {
        "active_attempt_id",
        "attempt_sequence",
        "lease_expires_at",
        "idempotency_key",
        "request_digest",
    }.issubset(columns) and {
        "ix_resource_generation_run_active_attempt_id",
        "uq_resource_generation_run_user_idempotency",
    }.issubset(indexes):
        return
    op.add_column(
        "resource_generation_run",
        sa.Column("active_attempt_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "resource_generation_run",
        sa.Column("attempt_sequence", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "resource_generation_run",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "resource_generation_run",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "resource_generation_run",
        sa.Column("request_digest", sa.String(length=64), server_default="", nullable=False),
    )
    op.create_index(
        "ix_resource_generation_run_active_attempt_id",
        "resource_generation_run",
        ["active_attempt_id"],
        unique=False,
    )
    op.create_index(
        "uq_resource_generation_run_user_idempotency",
        "resource_generation_run",
        ["user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_resource_generation_run_user_idempotency",
        table_name="resource_generation_run",
    )
    op.drop_index(
        "ix_resource_generation_run_active_attempt_id",
        table_name="resource_generation_run",
    )
    op.drop_column("resource_generation_run", "request_digest")
    op.drop_column("resource_generation_run", "idempotency_key")
    op.drop_column("resource_generation_run", "lease_expires_at")
    op.drop_column("resource_generation_run", "attempt_sequence")
    op.drop_column("resource_generation_run", "active_attempt_id")
