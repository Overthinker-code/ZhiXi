from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.student_profile import (
    ProfileAnalysisRequest,
    ProfileSignalUpdateRequest,
    ProfileUpdateResponse,
)
from app.services.profile_update_service import profile_update_service
from app.services.user_memory_profile_service import user_memory_profile_service

router = APIRouter()


def _owned_thread(db: Session, session_id: str, user_id: str):
    thread = chat_thread_provider.get_by_thread_id_and_user(
        db, thread_id=session_id, user_id=user_id
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return thread


@router.get("/me")
def read_my_profile(
    *, db: Session = Depends(deps.get_db), current_user: CurrentUser
) -> dict[str, Any]:
    return user_memory_profile_service.get_profile_dict(db, current_user.id) or {}


@router.post("/analyze", response_model=ProfileUpdateResponse)
def analyze_chat_profile(
    *,
    request: ProfileAnalysisRequest,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> ProfileUpdateResponse:
    user_id = str(current_user.id)
    thread = _owned_thread(db, request.session_id, user_id)
    analysis, profile, event = profile_update_service.analyze_and_update_turn(
        db,
        user_id=user_id,
        session_id=request.session_id,
        user_message=request.user_message,
        assistant_message=request.assistant_message,
        course=thread.course,
        knowledge_point=thread.knowledge_point,
    )
    return ProfileUpdateResponse(
        analysis=analysis, profile=profile, update_event_id=event.id
    )


@router.post("/update", response_model=ProfileUpdateResponse)
def update_profile_signals(
    *,
    request: ProfileSignalUpdateRequest,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> ProfileUpdateResponse:
    user_id = str(current_user.id)
    if request.session_id:
        _owned_thread(db, request.session_id, user_id)
    analysis = {
        "knowledge_point": request.knowledge_point,
        "observed_mastery": request.observed_mastery,
        "weakness": request.weak_point,
        "difficulty": "high" if request.weak_point else "",
        "preference_signals": request.preference_signals,
        "learning_goal": request.learning_goal,
        "cognitive_style": request.cognitive_style,
        "behavior_signals": request.behavior_signals,
    }
    profile, event = profile_update_service.apply_incremental_update(
        db,
        user_id=user_id,
        analysis=analysis,
        session_id=request.session_id,
        source_type=request.source_type,
        alpha=request.alpha,
        evidence=request.evidence,
    )
    return ProfileUpdateResponse(
        analysis=analysis, profile=profile, update_event_id=event.id
    )
