from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LearningTaskPublic(BaseModel):
    id: int
    title: str
    goal: str
    deadline: datetime | None = None
    current_stage: str
    progress: int
    status: str
    session_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LearningTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = Field(default=None, max_length=500)
    deadline: datetime | None = None
