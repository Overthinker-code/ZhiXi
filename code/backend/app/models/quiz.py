from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, Column, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


class Question(SQLModel, table=True):
    __tablename__ = "question"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    resource_id: UUID = Field(foreign_key="resource.id", index=True)
    knowledge_point: str = Field(default="", max_length=160, index=True)
    question_type: str = Field(default="single_choice", max_length=32)
    content: str = Field(max_length=2000)
    options: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    answer: str = Field(max_length=500)
    analysis: str = Field(default="", max_length=3000)
    difficulty: str = Field(default="standard", max_length=32, index=True)
    order: int = Field(default=0)


class QuizAttempt(SQLModel, table=True):
    __tablename__ = "quiz_attempt"

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    resource_id: UUID = Field(foreign_key="resource.id", index=True)
    answers: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    total_questions: int = Field(default=0)
    correct_count: int = Field(default=0)
    score: float = Field(default=0.0)
    wrong_knowledge_points: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class WrongQuestion(SQLModel, table=True):
    __tablename__ = "wrong_question"
    __table_args__ = (
        UniqueConstraint("user_id", "question_id", name="uq_wrong_question_user_question"),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    question_id: UUID = Field(foreign_key="question.id", index=True)
    source_attempt_id: UUID | None = Field(default=None, foreign_key="quiz_attempt.id", index=True)
    wrong_count: int = Field(default=1)
    is_favorite: bool = Field(default=False, index=True)
    mastered: bool = Field(default=False, index=True)
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
