"""Add verified external resources for personalized recommendations.

Revision ID: 015
Revises: 014
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("external_resource"):
        return
    op.create_table(
        "external_resource",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("knowledge_point", sa.String(length=160), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("recommend_reason", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    for column in ("source", "type", "knowledge_point", "difficulty", "created_by"):
        op.create_index(f"ix_external_resource_{column}", "external_resource", [column])


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("external_resource"):
        return
    for column in ("created_by", "difficulty", "knowledge_point", "type", "source"):
        op.drop_index(f"ix_external_resource_{column}", table_name="external_resource")
    op.drop_table("external_resource")
