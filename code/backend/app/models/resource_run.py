from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Index, Text, UniqueConstraint, text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResourceGenerationRun(SQLModel, table=True):
    __tablename__ = "resource_generation_run"
    __table_args__ = (
        Index(
            "uq_resource_generation_run_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('requested', 'running')"),
        ),
        Index(
            "uq_resource_generation_run_user_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: str = Field(primary_key=True, max_length=64)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    course_id: UUID | None = Field(default=None, foreign_key="course.id", index=True)
    package_id: str | None = Field(default=None, max_length=64, index=True)
    status: str = Field(default="requested", max_length=32, index=True)
    current_step: str = Field(default="requested", max_length=48)
    cancel_requested: bool = Field(default=False)
    active_attempt_id: str | None = Field(default=None, max_length=64, index=True)
    attempt_sequence: int = Field(default=0)
    lease_expires_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    idempotency_key: str | None = Field(default=None, max_length=128)
    request_digest: str = Field(default="", max_length=64)
    requested: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    shared_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    started_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    finished_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))


class ResourceGenerationStep(SQLModel, table=True):
    __tablename__ = "resource_generation_step"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: str = Field(foreign_key="resource_generation_run.id", index=True, max_length=64)
    step_key: str = Field(max_length=48, index=True)
    agent_role: str = Field(max_length=80)
    status: str = Field(default="running", max_length=32)
    provider: str = Field(default="local", max_length=48)
    model: str = Field(default="deterministic", max_length=120)
    input_digest: str = Field(max_length=64)
    output_digest: str | None = Field(default=None, max_length=64)
    input_summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    output_summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    citations: list[dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    retry_count: int = Field(default=0)
    started_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
    finished_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    duration_ms: int | None = Field(default=None)


class CourseKnowledgeNode(SQLModel, table=True):
    """Canonical node whose identity is stable within one course and map."""

    __tablename__ = "course_knowledge_node"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "map_type", "normalized_key",
            name="uq_course_knowledge_node_scope_key",
        ),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    course_id: UUID = Field(foreign_key="course.id", index=True)
    map_type: str = Field(default="knowledge", max_length=32, index=True)
    normalized_key: str = Field(max_length=180, index=True)
    label: str = Field(max_length=180, index=True)
    node_type: str = Field(default="concept", max_length=32, index=True)
    detail: str = Field(default="", sa_column=Column(Text, nullable=False))
    position_x: float = Field(default=0.0)
    position_y: float = Field(default=0.0)
    weight: float = Field(default=1.0)
    attributes: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CourseKnowledgeEdge(SQLModel, table=True):
    """Persisted relation between two nodes in the same course and map."""

    __tablename__ = "course_knowledge_edge"
    __table_args__ = (
        UniqueConstraint(
            "course_id", "map_type", "source_node_id", "target_node_id", "relation_type",
            name="uq_course_knowledge_edge_relation",
        ),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    course_id: UUID = Field(foreign_key="course.id", index=True)
    map_type: str = Field(default="knowledge", max_length=32, index=True)
    source_node_id: UUID = Field(foreign_key="course_knowledge_node.id", index=True)
    target_node_id: UUID = Field(foreign_key="course_knowledge_node.id", index=True)
    relation_type: str = Field(default="关联关系", max_length=32, index=True)
    strength: float = Field(default=1.0)
    source_type: str = Field(default="curriculum", max_length=32)
    run_id: str | None = Field(
        default=None,
        foreign_key="resource_generation_run.id",
        max_length=64,
        index=True,
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CourseKnowledgeNodeAction(SQLModel, table=True):
    """A student's explicit workflow action on one graph node.

    These rows are operational state only. In particular, ``evidence_read`` is
    an acknowledgement that the learner opened/read the supplied material; it
    must never be included in mastery or learning-evidence calculations.
    """

    __tablename__ = "course_knowledge_node_action"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "node_id", "action_type",
            name="uq_course_knowledge_node_action_user_node_type",
        ),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    course_id: UUID = Field(foreign_key="course.id", index=True)
    node_id: UUID = Field(foreign_key="course_knowledge_node.id", index=True)
    action_type: str = Field(max_length=32, index=True)
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class ResourceKnowledgeLink(SQLModel, table=True):
    __tablename__ = "resource_knowledge_link"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: str = Field(foreign_key="resource_generation_run.id", index=True, max_length=64)
    package_id: str = Field(foreign_key="generated_resource_package.id", index=True, max_length=64)
    resource_id: UUID = Field(foreign_key="resource.id", index=True)
    course_id: UUID = Field(foreign_key="course.id", index=True)
    knowledge_node_id: UUID | None = Field(
        default=None, foreign_key="course_knowledge_node.id", index=True
    )
    knowledge_point: str = Field(max_length=160, index=True)
    relation_type: str = Field(default="supports", max_length=32)
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
