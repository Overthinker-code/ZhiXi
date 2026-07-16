"""Reconcile the Agent and ResourceRun branches without losing existing data.

Revision ID: 021
Revises: 020
Create Date: 2026-07-12
"""

import importlib.util
from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def _load_upgrade(filename: str):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"zhixi_reconcile_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load compatibility migration: {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.upgrade


def _split_legacy_agent_profile_table() -> None:
    """Disambiguate the two historical tables that once shared one name."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("profile_update_event"):
        return
    columns = {column["name"] for column in inspector.get_columns("profile_update_event")}
    if "run_id" in columns or "session_id" not in columns:
        return
    if inspector.has_table("agent_profile_update_event"):
        op.rename_table("profile_update_event", "agent_profile_update_event_legacy")
        return
    for column in ("user_id", "session_id", "message_id"):
        op.execute(
            "ALTER INDEX IF EXISTS "
            f"ix_profile_update_event_{column} "
            f"RENAME TO ix_agent_profile_update_event_{column}"
        )
    op.rename_table("profile_update_event", "agent_profile_update_event")


def _ensure_remote_agent_branch() -> None:
    # Databases produced by the pre-merge local 007-011 branch are stamped at
    # 011 but do not contain the remote Agent tables. All remote migrations are
    # idempotent, so replay their upgrade functions at the reconciliation head.
    _split_legacy_agent_profile_table()
    for filename in (
        "007_add_agent_workspace_context.py",
        "008_upgrade_learning_sessions.py",
        "009_add_profile_update_events.py",
        "010_add_agent_tasks.py",
        "011_add_learning_tasks.py",
    ):
        _load_upgrade(filename)()


def upgrade() -> None:
    _ensure_remote_agent_branch()
    if sa.inspect(op.get_bind()).has_table("resource_generation_run"):
        return
    op.create_table(
        "resource_generation_run",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=True),
        sa.Column("package_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_step", sa.String(48), nullable=False),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("requested", sa.JSON(), nullable=False),
        sa.Column("shared_state", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    for name in ("user_id", "course_id", "package_id", "status"):
        op.create_index(f"ix_resource_generation_run_{name}", "resource_generation_run", [name])

    op.create_table(
        "resource_generation_step",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("resource_generation_run.id"), nullable=False),
        sa.Column("step_key", sa.String(48), nullable=False),
        sa.Column("agent_role", sa.String(80), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(48), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("input_digest", sa.String(64), nullable=False),
        sa.Column("output_digest", sa.String(64), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.create_index("ix_resource_generation_step_run_id", "resource_generation_step", ["run_id"])
    op.create_index("ix_resource_generation_step_step_key", "resource_generation_step", ["step_key"])

    op.create_table(
        "learning_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("resource_generation_run.id"), nullable=True),
        sa.Column("knowledge_point", sa.String(160), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("knowledge_point_id", sa.String(160), nullable=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(48), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_unique_constraint("uq_learning_evidence_user_idempotency", "learning_evidence", ["user_id", "idempotency_key"])
    for name in ("user_id", "course_id", "run_id", "knowledge_point", "knowledge_point_id", "idempotency_key", "source_type", "observed_at"):
        op.create_index(f"ix_learning_evidence_{name}", "learning_evidence", [name])

    op.create_table(
        "profile_update_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("resource_generation_run.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("evidence_ids", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("run_id", "user_id", "course_id"):
        op.create_index(f"ix_profile_update_event_{name}", "profile_update_event", [name])

    op.create_table(
        "learning_path_update_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("resource_generation_run.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=True),
        sa.Column("learning_path_id", sa.Uuid(), sa.ForeignKey("learning_path.id"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("run_id", "user_id", "course_id"):
        op.create_index(f"ix_learning_path_update_event_{name}", "learning_path_update_event", [name])

    op.create_table(
        "resource_knowledge_link",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("resource_generation_run.id"), nullable=False),
        sa.Column("package_id", sa.String(64), sa.ForeignKey("generated_resource_package.id"), nullable=False),
        sa.Column("resource_id", sa.Uuid(), sa.ForeignKey("resource.id"), nullable=False),
        sa.Column("course_id", sa.Uuid(), sa.ForeignKey("course.id"), nullable=False),
        sa.Column("knowledge_point", sa.String(160), nullable=False),
        sa.Column("relation_type", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("run_id", "package_id", "resource_id", "course_id", "knowledge_point"):
        op.create_index(f"ix_resource_knowledge_link_{name}", "resource_knowledge_link", [name])


def downgrade() -> None:
    op.drop_table("resource_knowledge_link")
    op.drop_table("learning_path_update_event")
    op.drop_table("profile_update_event")
    op.drop_table("learning_evidence")
    op.drop_table("resource_generation_step")
    op.drop_table("resource_generation_run")
