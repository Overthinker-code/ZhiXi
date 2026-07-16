from __future__ import annotations

from pydantic import BaseModel, Field


class LearningPathNodePublic(BaseModel):
    title: str
    status: str = "pending"
    order: int = 0
    topic: str = ""
    action: str = ""


class LearningPathPublic(BaseModel):
    user_id: str
    subject: str = ""
    summary: str = ""
    nodes: list[LearningPathNodePublic] = Field(default_factory=list)
    updated_at: str = ""
