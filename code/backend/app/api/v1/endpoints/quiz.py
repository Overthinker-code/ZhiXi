from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.schemas.quiz import (
    QuizAttemptDetail,
    QuizAttemptSummary,
    QuizResourcePublic,
    QuizSubmitRequest,
    QuizSubmitResponse,
    WrongBookSubmitResponse,
    WrongBookPracticeRequest,
    WrongQuestionBookResponse,
    WrongQuestionFavoriteRequest,
)
from app.services.quiz_service import QuizGenerationError, quiz_service


router = APIRouter()


@router.get("/quizzes/{resource_id}", response_model=QuizResourcePublic)
def get_quiz(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    resource_id: UUID,
) -> Any:
    try:
        return quiz_service.get(session, resource_id=resource_id, user_id=current_user.id)
    except QuizGenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/quizzes/{resource_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    resource_id: UUID,
    request: QuizSubmitRequest,
) -> Any:
    try:
        return quiz_service.submit(
            session,
            resource_id=resource_id,
            user_id=current_user.id,
            answers=request.answers,
        )
    except QuizGenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/quizzes/{resource_id}/attempts", response_model=list[QuizAttemptSummary])
def list_quiz_attempts(
    *, session: SessionDep, current_user: CurrentUser, resource_id: UUID
) -> Any:
    try:
        return quiz_service.list_attempts(
            session, resource_id=resource_id, user_id=current_user.id
        )
    except QuizGenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/quiz-attempts/{attempt_id}", response_model=QuizAttemptDetail)
def get_quiz_attempt(
    *, session: SessionDep, current_user: CurrentUser, attempt_id: UUID
) -> Any:
    try:
        return quiz_service.get_attempt(session, attempt_id=attempt_id, user_id=current_user.id)
    except QuizGenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/wrong-book", response_model=WrongQuestionBookResponse)
def get_wrong_question_book(*, session: SessionDep, current_user: CurrentUser) -> Any:
    return quiz_service.list_wrong_book(session, user_id=current_user.id)


@router.post("/wrong-book/practice", response_model=QuizResourcePublic)
def generate_wrong_question_practice(
    *, session: SessionDep, current_user: CurrentUser, request: WrongBookPracticeRequest
) -> Any:
    try:
        return quiz_service.generate_wrong_book_practice(
            session,
            user_id=current_user.id,
            subject=request.subject,
            question_ids=request.question_ids,
            count=request.count,
            difficulty=request.difficulty,
        )
    except QuizGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/wrong-book/{question_id}")
def set_wrong_question_favorite(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    question_id: UUID,
    request: WrongQuestionFavoriteRequest,
) -> Any:
    try:
        return quiz_service.set_wrong_question_favorite(
            session,
            question_id=question_id,
            user_id=current_user.id,
            favorite=request.favorite,
        )
    except QuizGenerationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/wrong-book/submit", response_model=WrongBookSubmitResponse)
def submit_wrong_question_book(
    *, session: SessionDep, current_user: CurrentUser, request: QuizSubmitRequest
) -> Any:
    try:
        return quiz_service.submit_wrong_book(
            session, user_id=current_user.id, answers=request.answers
        )
    except QuizGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
