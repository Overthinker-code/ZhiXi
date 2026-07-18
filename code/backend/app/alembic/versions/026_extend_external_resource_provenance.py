"""Persist bounded catalog provenance for external learning resources.

Revision ID: 026
Revises: 025
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("provider", sa.String(length=40), "manual"),
    ("provider_kind", sa.String(length=32), "resource"),
    ("summary", sa.String(length=1200), ""),
    ("authors", sa.JSON(), "[]"),
    ("published_year", sa.Integer(), None),
    ("language", sa.String(length=32), None),
    ("license_status", sa.String(length=160), None),
    ("cover_url", sa.String(length=1000), None),
    ("source_metadata", sa.JSON(), "{}"),
    ("discovered_at", sa.DateTime(timezone=True), None),
    ("verified_at", sa.DateTime(timezone=True), None),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("external_resource"):
        return
    existing = {column["name"] for column in inspector.get_columns("external_resource")}
    for name, column_type, default in _COLUMNS:
        if name in existing:
            continue
        kwargs: dict[str, object] = {"nullable": True}
        if default is not None:
            kwargs["server_default"] = sa.text(f"'{default}'")
        op.add_column("external_resource", sa.Column(name, column_type, **kwargs))
    op.execute("UPDATE external_resource SET provider = COALESCE(provider, 'manual'), provider_kind = COALESCE(provider_kind, type), summary = COALESCE(summary, ''), authors = COALESCE(authors, '[]'), source_metadata = COALESCE(source_metadata, '{}')")
    for name in ("provider", "provider_kind"):
        index = f"ix_external_resource_{name}"
        if index not in {row["name"] for row in sa.inspect(op.get_bind()).get_indexes("external_resource")}:
            op.create_index(index, "external_resource", [name])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("external_resource"):
        return
    existing = {column["name"] for column in inspector.get_columns("external_resource")}
    for name in ("provider", "provider_kind"):
        index = f"ix_external_resource_{name}"
        if name in existing and index in {row["name"] for row in sa.inspect(op.get_bind()).get_indexes("external_resource")}:
            op.drop_index(index, table_name="external_resource")
    for name, _, _ in reversed(_COLUMNS):
        if name in existing:
            op.drop_column("external_resource", name)
