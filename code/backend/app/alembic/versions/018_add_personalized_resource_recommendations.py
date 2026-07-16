"""Add persisted personalized recommendation candidates.

Revision ID: 018
Revises: 017
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("personalized_resource_recommendation"):
        return
    op.create_table(
        "personalized_resource_recommendation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("knowledge_point", sa.String(length=160), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("content_spec", sa.JSON(), nullable=False),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("external_resource_id", sa.Uuid(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["external_resource_id"], ["external_resource.id"]),
        sa.ForeignKeyConstraint(["resource_id"], ["resource.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "user_id", "origin", "type", "knowledge_point", "favorite", "status",
        "resource_id", "external_resource_id",
    ):
        op.create_index(
            f"ix_personalized_resource_recommendation_{column}",
            "personalized_resource_recommendation",
            [column],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("personalized_resource_recommendation"):
        return
    for column in (
        "external_resource_id", "resource_id", "status", "favorite",
        "knowledge_point", "type", "origin", "user_id",
    ):
        op.drop_index(
            f"ix_personalized_resource_recommendation_{column}",
            table_name="personalized_resource_recommendation",
        )
    op.drop_table("personalized_resource_recommendation")
