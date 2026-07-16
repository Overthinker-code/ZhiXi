from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LearningEvidence(SQLModel, table=True):
    __tablename__ = "learning_evidence"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_learning_evidence_user_idempotency"),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    course_id: UUID | None = Field(default=None, foreign_key="course.id", index=True)
    run_id: str | None = Field(default=None, foreign_key="resource_generation_run.id", index=True, max_length=64)
    knowledge_point: str = Field(max_length=160, index=True)
    display_name: str = Field(max_length=160)
    knowledge_point_id: str | None = Field(default=None, max_length=160, index=True)
    idempotency_key: str = Field(max_length=64, index=True)
    source_type: str = Field(max_length=48, index=True)
    source_id: str = Field(max_length=160)
    event_type: str = Field(max_length=48)
    observed_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    weight: float = Field(default=1.0, ge=0.0, le=5.0)
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


class ProfileUpdateEvent(SQLModel, table=True):
    __tablename__ = "profile_update_event"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: str = Field(foreign_key="resource_generation_run.id", index=True, max_length=64)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    course_id: UUID | None = Field(default=None, foreign_key="course.id", index=True)
    status: str = Field(default="completed", max_length=32)
    before_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    after_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    evidence_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))


class LearningPathUpdateEvent(SQLModel, table=True):
    __tablename__ = "learning_path_update_event"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    run_id: str = Field(foreign_key="resource_generation_run.id", index=True, max_length=64)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    course_id: UUID | None = Field(default=None, foreign_key="course.id", index=True)
    learning_path_id: UUID | None = Field(default=None, foreign_key="learning_path.id")
    status: str = Field(default="completed", max_length=32)
    before_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    after_state: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    summary: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, sa_column=Column(DateTime(timezone=True), nullable=False))
