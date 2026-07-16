"""Add per-user favorite and resource library configuration.

Revision ID: 014
Revises: 013
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("resource_favorite"):
        op.create_table(
            "resource_favorite",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("resource_id", sa.Uuid(), nullable=False),
            sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["resource_id"], ["resource.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "resource_id", name="uq_resource_favorite_user_resource"),
        )
        op.create_index("ix_resource_favorite_user_id", "resource_favorite", ["user_id"])
        op.create_index("ix_resource_favorite_resource_id", "resource_favorite", ["resource_id"])

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("user_resource_config"):
        op.create_table(
            "user_resource_config",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("resource_id", sa.Uuid(), nullable=False),
            sa.Column("is_top", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["resource_id"], ["resource.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "resource_id", name="uq_user_resource_config_user_resource"),
        )
        op.create_index("ix_user_resource_config_user_id", "user_resource_config", ["user_id"])
        op.create_index("ix_user_resource_config_resource_id", "user_resource_config", ["resource_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("user_resource_config"):
        op.drop_index("ix_user_resource_config_resource_id", table_name="user_resource_config")
        op.drop_index("ix_user_resource_config_user_id", table_name="user_resource_config")
        op.drop_table("user_resource_config")
    if inspector.has_table("resource_favorite"):
        op.drop_index("ix_resource_favorite_resource_id", table_name="resource_favorite")
        op.drop_index("ix_resource_favorite_user_id", table_name="resource_favorite")
        op.drop_table("resource_favorite")
