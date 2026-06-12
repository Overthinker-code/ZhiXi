from __future__ import annotations

from pydantic import BaseModel, Field


class StudentNotificationPublic(BaseModel):
    id: str
    title: str
    body: str
    category: str
    is_read: bool
    link: str | None = None
    created_at: str


class StudentNotificationsPublic(BaseModel):
    data: list[StudentNotificationPublic]
    count: int
    unread_count: int


class StudyGroupMemberPublic(BaseModel):
    student_id: str
    student_name: str
    role: str


class StudyGroupPublic(BaseModel):
    id: str
    name: str
    description: str
    tc_id: str | None = None
    course_name: str | None = None
    member_count: int
    my_role: str
    members: list[StudyGroupMemberPublic] = Field(default_factory=list)
    updated_at: str


class StudyGroupsPublic(BaseModel):
    data: list[StudyGroupPublic]
    count: int


class PracticeTopicSummary(BaseModel):
    subject: str
    topic: str
    sessions: int
    total_questions: int
    correct_count: int
    avg_score: float
    last_practiced_at: str | None = None


class PracticeSummaryPublic(BaseModel):
    total_sessions: int
    total_questions: int
    correct_rate: float
    subjects: list[str] = Field(default_factory=list)
    topics: list[PracticeTopicSummary] = Field(default_factory=list)
    assignment_completed: int
    assignment_total: int


class AchievementPublic(BaseModel):
    id: str
    code: str
    title: str
    description: str
    icon: str
    points_awarded: int
    earned_at: str


class AchievementsPublic(BaseModel):
    total_points: int
    level: int
    next_level_points: int
    data: list[AchievementPublic]
    count: int
