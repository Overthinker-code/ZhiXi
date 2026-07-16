"""Add structured knowledge graphs.

Revision ID: 012
Revises: 011
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("knowledge_graph"):
        return
    op.create_table(
        "knowledge_graph",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course", sa.String(length=120), nullable=False),
        sa.Column("knowledge_point", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("root", sa.String(length=160), nullable=False),
        sa.Column("graph_json", sa.JSON(), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "course", "knowledge_point"):
        op.create_index(f"ix_knowledge_graph_{column}", "knowledge_graph", [column])


def downgrade() -> None:
    for column in ("knowledge_point", "course", "user_id"):
        op.drop_index(f"ix_knowledge_graph_{column}", table_name="knowledge_graph")
    op.drop_table("knowledge_graph")
