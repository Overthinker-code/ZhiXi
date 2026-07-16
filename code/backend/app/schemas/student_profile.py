from typing import Any

from pydantic import BaseModel, Field


class ProfileAnalysisRequest(BaseModel):
    session_id: str
    user_message: str
    assistant_message: str = ""


class ProfileSignalUpdateRequest(BaseModel):
    session_id: str | None = None
    source_type: str = "feedback"
    alpha: float = Field(default=0.1, gt=0, le=1)
    knowledge_point: str | None = None
    observed_mastery: float | None = Field(default=None, ge=0, le=1)
    weak_point: str | None = None
    preference_signals: dict[str, float] = Field(default_factory=dict)
    learning_goal: str | None = None
    cognitive_style: str | None = None
    behavior_signals: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class ProfileUpdateResponse(BaseModel):
    status: str = "success"
    analysis: dict[str, Any] = Field(default_factory=dict)
    profile: dict[str, Any] = Field(default_factory=dict)
    update_event_id: int | None = None
