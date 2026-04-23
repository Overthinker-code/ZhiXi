from __future__ import annotations

from pydantic import BaseModel, Field


class LearningReportSection(BaseModel):
    title: str
    content: str


class LearningReport(BaseModel):
    learner_id: str
    generated_at: str
    summary: str = ""
    current_goal: str = ""
    learning_style: str = ""
    risk_level: str = "medium"
    weak_points: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    recommended_resources: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    sections: list[LearningReportSection] = Field(default_factory=list)


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
