from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class PersonalizedResourceRecommendation(SQLModel, table=True):
    __tablename__ = "personalized_resource_recommendation"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    origin: str = Field(max_length=20, index=True)  # generated | external
    title: str = Field(max_length=255)
    type: str = Field(max_length=50, index=True)
    subject: str = Field(default="未分类", max_length=80, index=True)
    knowledge_point: str = Field(default="", max_length=160, index=True)
    difficulty: str = Field(default="standard", max_length=32)
    source: str = Field(default="profile-agent", max_length=80)
    url: str | None = Field(default=None, max_length=1000)
    reason: str = Field(default="", max_length=500)
    evidence: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    content_spec: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    favorite: bool = Field(default=False, index=True)
    status: str = Field(default="active", max_length=20, index=True)  # active | dismissed | added
    resource_id: UUID | None = Field(default=None, foreign_key="resource.id", index=True)
    external_resource_id: UUID | None = Field(default=None, foreign_key="external_resource.id", index=True)
    generation: int = Field(default=1)
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
