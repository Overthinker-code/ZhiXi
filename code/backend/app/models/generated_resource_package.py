from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class GeneratedResourcePackage(SQLModel, table=True):
    __tablename__ = "generated_resource_package"

    id: str = Field(primary_key=True, max_length=64)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    course_id: UUID | None = Field(default=None, foreign_key="course.id", index=True)
    subject: str = Field(max_length=80)
    topic: str = Field(max_length=120)
    source: str | None = Field(default=None, max_length=80)
    resource_id: str | None = Field(default=None, max_length=120)
    node_id: str | None = Field(default=None, max_length=120)
    node_label: str | None = Field(default=None, max_length=120)
    map_type: str | None = Field(default=None, max_length=40)
    status: str = Field(default="completed", max_length=32)
    persistence_status: str = Field(default="package_persisted", max_length=32)
    model_profile: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    agent_trace: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    quality_notes: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
