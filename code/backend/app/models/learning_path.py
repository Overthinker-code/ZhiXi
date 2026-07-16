from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class LearningPathNode(SQLModel):
    title: str
    status: str = "pending"  # pending | in_progress | done
    order: int = 0
    topic: str = ""
    action: str = ""


class LearningPath(SQLModel, table=True):
    __tablename__ = "learning_path"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", unique=True, index=True)
    subject: str = Field(default="", max_length=80)
    summary: str = Field(default="", max_length=500)
    nodes: list[dict] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
