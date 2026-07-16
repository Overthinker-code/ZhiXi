from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessagePublic(BaseModel):
    id: int
    session_id: str
    role: Literal["user", "assistant", "system"]
    content: str
    status: str = "completed"
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class LearningContextUpdate(BaseModel):
    current_course: str | None = None
    current_knowledge_point: str | None = None
    user_goal: str | None = None
    weak_points: list[str] | None = None
    generated_resources: list[Any] | None = None
    historical_tasks: list[Any] | None = None
    context_data: dict[str, Any] | None = None


class LearningContextPublic(BaseModel):
    session_id: str
    current_course: str | None = None
    current_knowledge_point: str | None = None
    user_goal: str | None = None
    weak_points: list[str] = Field(default_factory=list)
    generated_resources: list[Any] = Field(default_factory=list)
    historical_tasks: list[Any] = Field(default_factory=list)
    context_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
