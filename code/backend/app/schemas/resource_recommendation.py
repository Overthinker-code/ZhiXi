from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class ExternalResourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source: str = Field(min_length=1, max_length=80)
    url: HttpUrl
    type: str = Field(min_length=1, max_length=50)
    subject: str = Field(default="未分类", max_length=80)
    knowledge_point: str = Field(default="", max_length=160)
    difficulty: str = Field(default="standard", max_length=32)
    recommend_reason: str = Field(default="", max_length=500)


class RecommendationItem(BaseModel):
    id: str
    origin: Literal["generated", "external"]
    title: str
    type: str
    subject: str = "未分类"
    knowledge_point: str = ""
    difficulty: str = ""
    source: str = ""
    url: str | None = None
    reason: str
    score: float
    evidence: list[str] = Field(default_factory=list)
    preview: str = ""
    favorite: bool = False
    status: str = "active"
    generation: int = 1
    resource: dict[str, Any] | None = None


class ResourceRecommendationResponse(BaseModel):
    generated_at: datetime
    profile_signals: list[str] = Field(default_factory=list)
    agent_trace: list[str] = Field(
        default_factory=lambda: ["student_profile_agent", "resource_agent"]
    )
    items: list[RecommendationItem] = Field(default_factory=list)


class RecommendationFavoriteRequest(BaseModel):
    favorite: bool = True


class RecommendationActionResponse(BaseModel):
    recommendation: RecommendationItem
    resource_id: UUID | None = None
    message: str
