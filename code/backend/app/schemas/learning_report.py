from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class LearningReportSection(BaseModel):
    title: str
    content: str


class ProcessStep(BaseModel):
    key: str
    label: str
    message: str = ""
    status: str = "done"


class PortraitDimensionAssessment(BaseModel):
    """A server-computed, auditable portrait dimension.

    ``value`` stays empty until the minimum evidence requirement for the
    dimension is met.  The UI can therefore degrade to a semantic "待积累"
    state instead of inventing a percentage from the current page snapshot.
    """

    key: str
    label: str
    value: float | None = None
    state: str = "insufficient"
    sample_size: int = 0
    sources: list[str] = Field(default_factory=list)
    method_version: str = "portrait_v1"
    updated_at: str | None = None


class DynamicProfileDimension(BaseModel):
    """Backend audit view of a longitudinal profile dimension.

    The student UI is not expected to render source/version metadata. It is
    exposed for tests, diagnostics and competition evidence material.
    """

    key: str
    label: str
    value: Any | None = None
    source_type: str = "insufficient"
    source_ref: str | None = None
    updated_at: str | None = None
    version: int = Field(default=1, ge=1)
    method_version: str = "dynamic_profile_v2"


class PortraitAnalyticsSeries(BaseModel):
    key: str
    label: str
    values: list[float | None] = Field(default_factory=list)


class PortraitAnalyticsCapability(BaseModel):
    key: str
    label: str
    value: float | None = None
    previous: float | None = None
    evidence_count: int = 0


class PortraitAnalyticsRhythm(BaseModel):
    week_labels: list[str] = Field(default_factory=list)
    day_labels: list[str] = Field(default_factory=list)
    activity: list[list[float]] = Field(default_factory=list)
    hour_labels: list[str] = Field(default_factory=list)
    focus_hours: list[float] = Field(default_factory=list)
    method_version: str = "activity_session_gap_45m_v1"


class PortraitAnalyticsResourcePreference(BaseModel):
    key: str
    label: str
    value: float
    count: int


class PortraitAnalyticsCourse(BaseModel):
    id: UUID
    name: str
    score: float | None = None
    trend: float | None = None
    focus: str = ""
    evidence_count: int = 0


class PortraitAnalytics(BaseModel):
    profile_version: int = 1
    generated_at: str
    evidence_count: int = 0
    confidence: float | None = None
    overall_score: float | None = None
    growth_30d: float | None = None
    engagement: float | None = None
    attention_count: int = 0
    trend_labels: list[str] = Field(default_factory=list)
    trend_series: list[PortraitAnalyticsSeries] = Field(default_factory=list)
    capabilities: list[PortraitAnalyticsCapability] = Field(default_factory=list)
    rhythm: PortraitAnalyticsRhythm = Field(default_factory=PortraitAnalyticsRhythm)
    resource_preferences: list[PortraitAnalyticsResourcePreference] = Field(default_factory=list)
    courses: list[PortraitAnalyticsCourse] = Field(default_factory=list)
    method_version: str = "portrait_analytics_v1"


class LearningReport(BaseModel):
    learner_id: str
    generated_at: str
    summary: str = ""
    current_goal: str = ""
    learning_style: str = ""
    risk_level: str = "medium"
    weak_points: list[str] = Field(default_factory=list)
    mastery_map: dict[str, float] = Field(default_factory=dict)
    mastery_insights: list[str] = Field(default_factory=list)
    mastery_formula: str = ""
    strengths: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    recommended_resources: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    sections: list[LearningReportSection] = Field(default_factory=list)
    # 教育学参数联动：课堂行为摘要
    classroom_behavior_summary: Optional[dict] = None
    # 诊断过程步骤（供前端 Timeline 展示）
    process_steps: list[ProcessStep] = Field(default_factory=list)
    evidence_confidence: dict[str, dict[str, Any]] = Field(default_factory=dict)
    portrait_dimensions: list[PortraitDimensionAssessment] = Field(default_factory=list)
    profile_schema_version: str = "dynamic_profile_v2"
    dynamic_profile_dimensions: list[DynamicProfileDimension] = Field(default_factory=list)


class LearningEvidenceCreate(BaseModel):
    course_id: UUID | None = None
    knowledge_point: str = Field(min_length=1, max_length=160)
    knowledge_point_id: str | None = Field(default=None, max_length=160)
    idempotency_key: str | None = Field(default=None, max_length=64)
    source_type: str = Field(min_length=1, max_length=48)
    source_id: str = Field(min_length=1, max_length=160)
    event_type: str = Field(min_length=1, max_length=48)
    observed_at: datetime | None = None
    weight: float = Field(default=1.0, ge=0.0, le=5.0)
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    payload: dict[str, Any] = Field(default_factory=dict)


class LearningEvidencePublic(LearningEvidenceCreate):
    id: UUID
    user_id: UUID
    run_id: str | None = None
    observed_at: datetime
    display_name: str


class ReviewPlanDay(BaseModel):
    day_label: str
    focus: str
    tasks: list[str] = Field(default_factory=list)


class ReviewPlan(BaseModel):
    learner_id: str
    generated_at: str
    summary: str = ""
    focus_topics: list[str] = Field(default_factory=list)
    daily_plan: list[ReviewPlanDay] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)


class MistakeDigestItem(BaseModel):
    title: str
    symptom: str = ""
    evidence: str = ""
    fix_strategy: str = ""


class MistakeDigest(BaseModel):
    learner_id: str
    generated_at: str
    summary: str = ""
    mistakes: list[MistakeDigestItem] = Field(default_factory=list)
    flashcards: list[str] = Field(default_factory=list)
