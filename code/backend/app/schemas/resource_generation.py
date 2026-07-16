from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


ResourceKind = Literal[
    "lecture_markdown",
    "lecture_docx",
    "lecture_pdf",
    "practice_markdown",
    "practice_docx",
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
    resource_id: UUID | None = None
    knowledge_point: str | None = None
    difficulty: str | None = None
    generated_at: datetime | None = None
    course_id: UUID | None = None


class ResourceRunStepPublic(BaseModel):
    id: UUID
    step_key: str
    agent_role: str
    status: str
    provider: str
    model: str
    input_digest: str
    output_digest: str | None = None
    input_summary: str = ""
    output_summary: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None


class ResourceRunPublic(BaseModel):
    run_id: str
    package_id: str | None = None
    result_url: str | None = None
    course_id: UUID | None = None
    status: Literal["requested", "running", "cancelled", "failed", "partial_success", "completed"]
    current_step: str
    cancel_requested: bool = False
    attempt_sequence: int = 0
    lease_expires_at: datetime | None = None
    requested: dict[str, Any] = Field(default_factory=dict)
    shared_state: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    steps: list[ResourceRunStepPublic] = Field(default_factory=list)


class ResourceGenerationResponse(BaseModel):
    run_id: str | None = None
    run_status: Literal["requested", "running", "cancelled", "failed", "partial_success", "completed"] | None = None
    stage_status: dict[str, str] = Field(default_factory=dict)
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
