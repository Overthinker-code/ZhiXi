from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


class KnowledgeGraph(SQLModel, table=True):
    __tablename__ = "knowledge_graph"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    resource_id: UUID | None = Field(default=None, foreign_key="resource.id", index=True)
    course: str = Field(default="", max_length=120, index=True)
    knowledge_point: str = Field(default="", max_length=160, index=True)
    title: str = Field(max_length=200)
    root: str = Field(max_length=160)
    graph_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
