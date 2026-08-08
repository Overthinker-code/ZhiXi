"""Repair external-resource provenance columns on drifted databases.

Revision ID: 028
Revises: 027
Create Date: 2026-07-20

Some local databases were stamped through revision 026 while the
``external_resource`` table did not yet contain the provenance columns.  This
idempotent migration reconciles the physical schema with the model.
"""

from alembic import op
import sqlalchemy as sa


revision = "028"
down_revision = "027"
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
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

    op.execute(
        "UPDATE external_resource SET "
        "provider = COALESCE(provider, 'manual'), "
        "provider_kind = COALESCE(provider_kind, type), "
        "summary = COALESCE(summary, ''), "
        "authors = COALESCE(authors, '[]'), "
        "source_metadata = COALESCE(source_metadata, '{}')"
    )

    indexes = {row["name"] for row in sa.inspect(bind).get_indexes("external_resource")}
    for name in ("provider", "provider_kind"):
        index_name = f"ix_external_resource_{name}"
        if index_name not in indexes:
            op.create_index(index_name, "external_resource", [name])


def downgrade() -> None:
    # This is a repair migration. Revision 026 owns the provenance columns, so
    # downgrading 028 must not remove data or break a schema that 026 expects.
    pass
