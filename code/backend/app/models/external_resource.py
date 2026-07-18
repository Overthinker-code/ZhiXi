from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime
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
    # Provider-returned metadata is deliberately bounded by the discovery
    # service.  It is display metadata, never arbitrary page content.
    provider: str = Field(default="manual", max_length=40, index=True)
    provider_kind: str = Field(default="resource", max_length=32, index=True)
    summary: str = Field(default="", max_length=1200)
    authors: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    published_year: int | None = Field(default=None)
    language: str | None = Field(default=None, max_length=32)
    license_status: str | None = Field(default=None, max_length=160)
    cover_url: str | None = Field(default=None, max_length=1000)
    source_metadata: dict[str, object] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    discovered_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    verified_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    created_by: UUID | None = Field(default=None, foreign_key="user.id", index=True)
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
