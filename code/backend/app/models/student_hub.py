"""Student hub domain models: notifications, study groups, practice, achievements."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel


class StudentNotification(SQLModel, table=True):
    __tablename__ = "student_notification"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    title: str = Field(max_length=255)
    body: str = Field(default="", max_length=2000)
    category: str = Field(default="system", max_length=50)
    is_read: bool = Field(default=False)
    link: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StudyGroup(SQLModel, table=True):
    __tablename__ = "study_group"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=255)
    description: str = Field(default="", max_length=1000)
    tc_id: UUID | None = Field(default=None, foreign_key="tc.id", index=True)
    owner_student_id: UUID | None = Field(default=None, foreign_key="student.id")
    member_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class StudyGroupMember(SQLModel, table=True):
    __tablename__ = "study_group_member"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    group_id: UUID = Field(foreign_key="study_group.id", index=True)
    student_id: UUID = Field(foreign_key="student.id", index=True)
    role: str = Field(default="member", max_length=20)
    joined_at: datetime = Field(default_factory=datetime.utcnow)


class PracticeRecord(SQLModel, table=True):
    __tablename__ = "practice_record"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    student_id: UUID | None = Field(default=None, foreign_key="student.id", index=True)
    subject: str = Field(max_length=120)
    topic: str = Field(max_length=120)
    total_questions: int = Field(default=0)
    correct_count: int = Field(default=0)
    score: float = Field(default=0.0)
    duration_seconds: int = Field(default=0)
    practiced_at: datetime = Field(default_factory=datetime.utcnow)


class StudentAchievement(SQLModel, table=True):
    __tablename__ = "student_achievement"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    code: str = Field(max_length=80)
    title: str = Field(max_length=255)
    description: str = Field(default="", max_length=500)
    icon: str = Field(default="trophy", max_length=50)
    points_awarded: int = Field(default=0)
    earned_at: datetime = Field(default_factory=datetime.utcnow)


class StudentPoints(SQLModel, table=True):
    __tablename__ = "student_points"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", unique=True, index=True)
    total_points: int = Field(default=0)
    level: int = Field(default=1)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
