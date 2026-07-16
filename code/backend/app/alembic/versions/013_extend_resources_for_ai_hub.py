"""Extend resources for the Agent-driven resource hub.

Revision ID: 013
Revises: 012
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("resource"):
        columns = {column["name"] for column in inspector.get_columns("resource")}
        additions = {
            "content": sa.Column("content", sa.JSON(), nullable=True),
            "url": sa.Column("url", sa.String(length=500), nullable=True),
            "knowledge_point": sa.Column("knowledge_point", sa.String(length=160), nullable=True),
            "difficulty": sa.Column("difficulty", sa.String(length=32), nullable=True),
            "source": sa.Column("source", sa.String(length=80), nullable=True),
        }
        for name, column in additions.items():
            if name not in columns:
                op.add_column("resource", column)
        with op.batch_alter_table("resource") as batch:
            batch.alter_column("course_id", existing_type=sa.Uuid(), nullable=True)
        refreshed = {column["name"] for column in sa.inspect(bind).get_columns("resource")}
        for name in ("knowledge_point", "difficulty", "source"):
            index_name = f"ix_resource_{name}"
            if name in refreshed and index_name not in {item["name"] for item in sa.inspect(bind).get_indexes("resource")}:
                op.create_index(index_name, "resource", [name])

    if inspector.has_table("knowledge_graph"):
        columns = {column["name"] for column in inspector.get_columns("knowledge_graph")}
        if "resource_id" not in columns:
            op.add_column("knowledge_graph", sa.Column("resource_id", sa.Uuid(), nullable=True))
            op.create_index("ix_knowledge_graph_resource_id", "knowledge_graph", ["resource_id"])
            op.create_foreign_key(
                "fk_knowledge_graph_resource_id_resource",
                "knowledge_graph",
                "resource",
                ["resource_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("knowledge_graph"):
        columns = {column["name"] for column in inspector.get_columns("knowledge_graph")}
        if "resource_id" in columns:
            op.drop_constraint(
                "fk_knowledge_graph_resource_id_resource",
                "knowledge_graph",
                type_="foreignkey",
            )
            op.drop_index("ix_knowledge_graph_resource_id", table_name="knowledge_graph")
            op.drop_column("knowledge_graph", "resource_id")

    if inspector.has_table("resource"):
        indexes = {item["name"] for item in inspector.get_indexes("resource")}
        for name in ("knowledge_point", "difficulty", "source"):
            index_name = f"ix_resource_{name}"
            if index_name in indexes:
                op.drop_index(index_name, table_name="resource")
        columns = {column["name"] for column in inspector.get_columns("resource")}
        for name in ("source", "difficulty", "knowledge_point", "url", "content"):
            if name in columns:
                op.drop_column("resource", name)
        with op.batch_alter_table("resource") as batch:
            batch.alter_column("course_id", existing_type=sa.Uuid(), nullable=False)
