from typing import Any

from pydantic import BaseModel, Field


class ProfileAnalysisRequest(BaseModel):
    session_id: str
    user_message: str
    assistant_message: str = ""


class ProfileSignalUpdateRequest(BaseModel):
    user_id: str | None = None
    interaction_type: str | None = None
    interaction_data: dict[str, Any] = Field(default_factory=dict)
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


class DigitalTwinDimension(BaseModel):
    key: str
    label: str
    score: int = Field(ge=0, le=100)


class KnowledgeGraphNode(BaseModel):
    id: str
    name: str
    mastery: float = Field(ge=0, le=1)


class KnowledgeGraphEdge(BaseModel):
    source: str
    target: str


class DigitalTwinResponse(BaseModel):
    id: str
    user_id: str
    learning_stage: str
    learning_goal: str = ""
    learning_style: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    knowledge_state: dict[str, float] = Field(default_factory=dict)
    learning_behavior: dict[str, Any] = Field(default_factory=dict)
    learning_preference: dict[str, float] = Field(default_factory=dict)
    cognitive_style: str
    knowledge_graph: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    dimensions: list[DigitalTwinDimension] = Field(default_factory=list)
    overall_score: int = 0
    ai_summary: str
    last_updates: list[str] = Field(default_factory=list)
    profile_version: int = 1
    updated_time: Any
    agent_links: dict[str, str] = Field(default_factory=dict)
