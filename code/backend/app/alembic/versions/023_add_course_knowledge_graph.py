"""Add persistent, course-scoped knowledge graph nodes and edges.

Revision ID: 023
Revises: 022
Create Date: 2026-07-13
"""

from alembic import op
import sqlalchemy as sa


revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("course_knowledge_node"):
        return
    op.create_table(
        "course_knowledge_node",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("map_type", sa.String(32), nullable=False),
        sa.Column("normalized_key", sa.String(180), nullable=False),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("node_type", sa.String(32), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "course_id", "map_type", "normalized_key",
            name="uq_course_knowledge_node_scope_key",
        ),
    )
    for name in ("course_id", "map_type", "normalized_key", "label", "node_type"):
        op.create_index(f"ix_course_knowledge_node_{name}", "course_knowledge_node", [name])

    op.create_table(
        "course_knowledge_edge",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("map_type", sa.String(32), nullable=False),
        sa.Column("source_node_id", sa.Uuid(), sa.ForeignKey("course_knowledge_node.id"), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), sa.ForeignKey("course_knowledge_node.id"), nullable=False),
        sa.Column("relation_type", sa.String(32), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("resource_generation_run.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "course_id", "map_type", "source_node_id", "target_node_id", "relation_type",
            name="uq_course_knowledge_edge_relation",
        ),
    )
    for name in ("course_id", "map_type", "source_node_id", "target_node_id", "relation_type", "run_id"):
        op.create_index(f"ix_course_knowledge_edge_{name}", "course_knowledge_edge", [name])

    op.add_column("resource_knowledge_link", sa.Column("knowledge_node_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_resource_knowledge_link_node",
        "resource_knowledge_link",
        "course_knowledge_node",
        ["knowledge_node_id"],
        ["id"],
    )
    op.create_index(
        "ix_resource_knowledge_link_knowledge_node_id",
        "resource_knowledge_link",
        ["knowledge_node_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_resource_knowledge_link_knowledge_node_id", table_name="resource_knowledge_link")
    op.drop_constraint("fk_resource_knowledge_link_node", "resource_knowledge_link", type_="foreignkey")
    op.drop_column("resource_knowledge_link", "knowledge_node_id")
    op.drop_table("course_knowledge_edge")
    op.drop_table("course_knowledge_node")
