from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class StudentProfile(SQLModel, table=True):
    """Materialized learner digital-twin snapshot owned by one user."""

    __tablename__ = "student_profile"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", unique=True, index=True)
    learning_stage: str = Field(default="画像形成期", max_length=80)
    learning_goal: str = Field(default="", max_length=500)
    learning_style: str = Field(default="持续观察型", max_length=160)
    strengths: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    weaknesses: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    knowledge_state: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    learning_behavior: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    learning_preference: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    cognitive_style: str = Field(default="持续观察中", max_length=160)
    knowledge_graph: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    dimension_scores: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    ai_summary: str = Field(default="", max_length=4000)
    last_updates: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    evidence_cursor: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    profile_version: int = Field(default=1)
    updated_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
