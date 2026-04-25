"""add dashboard/resource columns

Revision ID: 003
Revises: 002
Create Date: 2026-04-24

"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("course"):
        course_columns = {col["name"] for col in inspector.get_columns("course")}
        if "click_number" not in course_columns:
            op.add_column(
                "course",
                sa.Column("click_number", sa.Integer(), nullable=False, server_default="0"),
            )
            op.alter_column("course", "click_number", server_default=None)

    if inspector.has_table("resource"):
        resource_columns = {col["name"] for col in inspector.get_columns("resource")}
        if "file_name" not in resource_columns:
            op.add_column(
                "resource",
                sa.Column("file_name", sa.String(length=255), nullable=False, server_default=""),
            )
        if "file_path" not in resource_columns:
            op.add_column(
                "resource",
                sa.Column("file_path", sa.String(length=255), nullable=False, server_default=""),
            )
        if "file_size" not in resource_columns:
            op.add_column(
                "resource",
                sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
            )
        if "content_type" not in resource_columns:
            op.add_column(
                "resource",
                sa.Column(
                    "content_type",
                    sa.String(length=150),
                    nullable=False,
                    server_default="application/octet-stream",
                ),
            )
        if "uploader_id" not in resource_columns:
            op.add_column("resource", sa.Column("uploader_id", sa.Uuid(), nullable=True))

        # 尽量清理临时 server default，避免影响后续写入语义。
        op.alter_column("resource", "file_name", server_default=None)
        op.alter_column("resource", "file_path", server_default=None)
        op.alter_column("resource", "file_size", server_default=None)
        op.alter_column("resource", "content_type", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("resource"):
        resource_columns = {col["name"] for col in inspector.get_columns("resource")}
        if "uploader_id" in resource_columns:
            op.drop_column("resource", "uploader_id")
        if "content_type" in resource_columns:
            op.drop_column("resource", "content_type")
        if "file_size" in resource_columns:
            op.drop_column("resource", "file_size")
        if "file_path" in resource_columns:
            op.drop_column("resource", "file_path")
        if "file_name" in resource_columns:
            op.drop_column("resource", "file_name")

    if inspector.has_table("course"):
        course_columns = {col["name"] for col in inspector.get_columns("course")}
        if "click_number" in course_columns:
            op.drop_column("course", "click_number")
