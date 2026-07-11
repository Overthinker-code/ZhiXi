from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


ResourceKind = Literal[
    "lecture_markdown",
    "lecture_pdf",
    "practice_markdown",
    "practice_pdf",
    "mind_map",
    "reading_list",
    "case_project",
    "video_script",
    "quality_checklist",
]


class ResourceGenerationRequest(BaseModel):
    course_id: UUID | None = None
    resource_id: str | None = Field(default=None, max_length=120)
    node_id: str | None = Field(default=None, max_length=120)
    node_label: str | None = Field(default=None, max_length=120)
    map_type: str | None = Field(default=None, max_length=40)
    source: str | None = Field(default=None, max_length=80)
    subject: str = Field(..., min_length=1, max_length=80)
    topic: str = Field(..., min_length=1, max_length=120)
    learning_goal: str | None = Field(default=None, max_length=240)
    difficulty: Literal["foundation", "standard", "challenge"] = "standard"
    target_minutes: int = Field(default=45, ge=10, le=180)
    resource_types: list[ResourceKind] = Field(default_factory=list)
    use_web_search: bool = False


class GeneratedResourceArtifact(BaseModel):
    kind: ResourceKind
    title: str
    file_name: str
    download_url: str
    content_type: str
    file_size: int
    preview: str = ""


class ResourceGenerationResponse(BaseModel):
    package_id: str
    course_id: UUID | None = None
    resource_id: str | None = None
    node_id: str | None = None
    node_label: str | None = None
    map_type: str | None = None
    source: str | None = None
    subject: str
    topic: str
    generated_at: datetime
    local_model_profile: dict[str, Any] = Field(default_factory=dict)
    agent_trace: list[str] = Field(default_factory=list)
    quality_notes: list[str] = Field(default_factory=list)
    persistence_status: Literal[
        "file_only",
        "package_persisted",
        "resources_persisted",
    ] = "file_only"
    persisted_resource_ids: list[UUID] = Field(default_factory=list)
    artifacts: list[GeneratedResourceArtifact]
