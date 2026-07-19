from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.student_profile import (
    DigitalTwinResponse,
    ProfileAnalysisRequest,
    ProfileSignalUpdateRequest,
    ProfileUpdateResponse,
)
from app.services.profile_update_service import profile_update_service
from app.services.student_profile_agent import student_profile_agent
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


@router.get("/digital-twin", response_model=DigitalTwinResponse)
def read_digital_twin(
    *, db: Session = Depends(deps.get_db), current_user: CurrentUser
) -> dict[str, Any]:
    """Return a server-built, current learner digital twin."""
    row = student_profile_agent.synchronize(db, current_user.id)
    return student_profile_agent.public_dict(row)


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
    student_profile_agent.synchronize(db, current_user.id)
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
    if request.user_id and request.user_id != user_id:
        raise HTTPException(status_code=403, detail="Cannot update another learner profile")
    if request.session_id:
        _owned_thread(db, request.session_id, user_id)
    interaction = dict(request.interaction_data or {})
    interaction_type = str(request.interaction_type or request.source_type or "feedback")
    if interaction_type == "chat":
        message = str(interaction.get("message") or interaction.get("user_message") or "")
        semantic = profile_update_service.analyze_chat_turn(
            user_message=message,
            assistant_message=str(interaction.get("assistant_message") or ""),
            course=interaction.get("course"),
            knowledge_point=interaction.get("knowledge_point"),
        )
    elif interaction_type in {"answer", "quiz", "practice"}:
        is_correct = interaction.get("is_correct")
        result = interaction.get("score", 1 if is_correct is True else 0 if is_correct is False else None)
        semantic = {
            "knowledge_point": interaction.get("knowledge_point"),
            "observed_mastery": result,
            "weakness": interaction.get("knowledge_point") if result is not None and float(result) < 0.6 else "",
            "difficulty": "high" if result is not None and float(result) < 0.6 else "low",
            "behavior_signals": {"answer_events": 1},
        }
    elif interaction_type in {"resource", "resource_view", "resource_download", "resource_favorite"}:
        resource_type = str(interaction.get("resource_type") or interaction.get("type") or "document")
        strength = float(interaction.get("completion_rate") or interaction.get("engagement") or 1)
        semantic = {
            "preference_signals": {resource_type: max(-1, min(1, strength))},
            "behavior_signals": {interaction_type: 1},
            "knowledge_point": interaction.get("knowledge_point"),
        }
    else:
        semantic = {}
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
    analysis.update({key: value for key, value in semantic.items() if value not in (None, "", {}, [])})
    profile, event = profile_update_service.apply_incremental_update(
        db,
        user_id=user_id,
        analysis=analysis,
        session_id=request.session_id,
        source_type=interaction_type,
        alpha=request.alpha,
        evidence=request.evidence or interaction,
    )
    student_profile_agent.synchronize(db, current_user.id)
    return ProfileUpdateResponse(
        analysis=analysis, profile=profile, update_event_id=event.id
    )
