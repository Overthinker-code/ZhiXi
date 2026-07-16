"""Persist generated resource packages and link course resources.

Revision ID: 006
Revises: 005
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("generated_resource_package"):
        op.create_table(
            "generated_resource_package",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("course_id", sa.Uuid(), nullable=True),
            sa.Column("subject", sa.String(length=80), nullable=False),
            sa.Column("topic", sa.String(length=120), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=True),
            sa.Column("resource_id", sa.String(length=120), nullable=True),
            sa.Column("node_id", sa.String(length=120), nullable=True),
            sa.Column("node_label", sa.String(length=120), nullable=True),
            sa.Column("map_type", sa.String(length=40), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("persistence_status", sa.String(length=32), nullable=False),
            sa.Column("model_profile", sa.JSON(), nullable=False),
            sa.Column("agent_trace", sa.JSON(), nullable=False),
            sa.Column("quality_notes", sa.JSON(), nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["course_id"], ["course.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_generated_resource_package_user_id",
            "generated_resource_package",
            ["user_id"],
        )
        op.create_index(
            "ix_generated_resource_package_course_id",
            "generated_resource_package",
            ["course_id"],
        )
        op.create_index(
            "ix_generated_resource_package_generated_at",
            "generated_resource_package",
            ["generated_at"],
        )

    inspector = sa.inspect(bind)
    if inspector.has_table("resource"):
        resource_columns = {col["name"] for col in inspector.get_columns("resource")}
        if "package_id" not in resource_columns:
            op.add_column(
                "resource",
                sa.Column("package_id", sa.String(length=64), nullable=True),
            )
            op.create_index(
                "ix_resource_package_id",
                "resource",
                ["package_id"],
            )
            op.create_foreign_key(
                "fk_resource_package_id_generated_resource_package",
                "resource",
                "generated_resource_package",
                ["package_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("resource"):
        resource_columns = {col["name"] for col in inspector.get_columns("resource")}
        if "package_id" in resource_columns:
            op.drop_constraint(
                "fk_resource_package_id_generated_resource_package",
                "resource",
                type_="foreignkey",
            )
            op.drop_index("ix_resource_package_id", table_name="resource")
            op.drop_column("resource", "package_id")

    if inspector.has_table("generated_resource_package"):
        op.drop_index(
            "ix_generated_resource_package_generated_at",
            table_name="generated_resource_package",
        )
        op.drop_index(
            "ix_generated_resource_package_course_id",
            table_name="generated_resource_package",
        )
        op.drop_index(
            "ix_generated_resource_package_user_id",
            table_name="generated_resource_package",
        )
        op.drop_table("generated_resource_package")
