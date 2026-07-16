from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class ExternalResource(SQLModel, table=True):
    __tablename__ = "external_resource"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=255)
    source: str = Field(max_length=80, index=True)
    url: str = Field(max_length=1000, unique=True)
    type: str = Field(max_length=50, index=True)
    subject: str = Field(default="未分类", max_length=80, index=True)
    knowledge_point: str = Field(default="", max_length=160, index=True)
    difficulty: str = Field(default="standard", max_length=32, index=True)
    recommend_reason: str = Field(default="", max_length=500)
    created_by: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
