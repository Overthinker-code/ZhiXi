from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class QuizOption(BaseModel):
    key: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=500)


class QuizQuestionDraft(BaseModel):
    knowledge_point: str = Field(min_length=1, max_length=160)
    question_type: Literal["single_choice"] = "single_choice"
    content: str = Field(min_length=1, max_length=2000)
    options: list[QuizOption] = Field(min_length=2, max_length=6)
    answer: str = Field(min_length=1, max_length=8)
    analysis: str = Field(min_length=1, max_length=3000)
    difficulty: Literal["foundation", "standard", "challenge"] = "standard"


class QuizDraft(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    questions: list[QuizQuestionDraft] = Field(min_length=1, max_length=30)


class QuizQuestionPublic(BaseModel):
    id: UUID
    knowledge_point: str
    question_type: str
    content: str
    options: list[QuizOption]
    difficulty: str
    order: int


class QuizResourcePublic(BaseModel):
    resource_id: UUID
    title: str
    subject: str = "未分类"
    knowledge_point: str
    difficulty: str
    file_name: str = ""
    download_url: str = ""
    questions: list[QuizQuestionPublic]


class QuizSubmitRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class QuizQuestionResult(BaseModel):
    question_id: UUID
    selected_answer: str = ""
    correct_answer: str
    is_correct: bool
    analysis: str
    knowledge_point: str
    saved_to_wrong_book: bool = False


class QuizSubmitResponse(BaseModel):
    attempt_id: UUID
    total_questions: int
    correct_count: int
    score: float
    wrong_knowledge_points: list[str]
    results: list[QuizQuestionResult]
    profile_updated: bool = True
    learning_path_updated: bool = True
    recommendation_refresh: bool = True


class QuizAttemptSummary(BaseModel):
    attempt_id: UUID
    resource_id: UUID
    total_questions: int
    correct_count: int
    score: float
    wrong_knowledge_points: list[str]
    created_time: datetime


class QuizAttemptDetail(QuizSubmitResponse):
    resource_id: UUID
    created_time: datetime


class WrongQuestionFavoriteRequest(BaseModel):
    favorite: bool = True


class WrongQuestionPublic(BaseModel):
    id: UUID
    question: QuizQuestionPublic
    resource_id: UUID
    resource_title: str
    subject: str = "未分类"
    wrong_count: int
    mastered: bool
    created_time: datetime
    updated_time: datetime


class WrongQuestionBookResponse(BaseModel):
    items: list[WrongQuestionPublic]
    count: int


class WrongBookSubmitResponse(BaseModel):
    total_questions: int
    correct_count: int
    score: float
    wrong_knowledge_points: list[str]
    results: list[QuizQuestionResult]
    attempt_ids: list[UUID]
    profile_updated: bool = True
