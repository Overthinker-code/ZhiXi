from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.schemas.learning_report import (
    LearningEvidenceCreate,
    LearningEvidencePublic,
    LearningReport,
    PortraitAnalytics,
    ReviewPlan,
    MistakeDigest,
)
from app.services.learning_report_service import learning_report_service

router = APIRouter()


@router.post("/evidence", response_model=LearningEvidencePublic, status_code=201)
def create_learning_evidence(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    payload: LearningEvidenceCreate,
) -> Any:
    evidence = learning_report_service.record_evidence(
        db,
        user_id=current_user.id,
        course_id=payload.course_id,
        knowledge_point=payload.knowledge_point,
        knowledge_point_id=payload.knowledge_point_id,
        idempotency_key=payload.idempotency_key,
        source_type=payload.source_type,
        source_id=payload.source_id,
        event_type=payload.event_type,
        observed_at=payload.observed_at,
        weight=payload.weight,
        score=payload.score,
        payload=payload.payload,
    )
    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/evidence/confidence")
def get_learning_evidence_confidence(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> Any:
    return {"knowledge_points": learning_report_service.evidence_confidence(db, current_user.id)}


@router.get("/me", response_model=LearningReport)
def get_my_learning_report(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    refresh: bool = Query(default=False),
) -> Any:
    user_id = str(current_user.id)
    return learning_report_service.build_report(db, user_id, refresh_profile=refresh)


@router.get("/portrait/analytics", response_model=PortraitAnalytics)
def get_portrait_analytics(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> Any:
    return learning_report_service.build_portrait_analytics(db, current_user.id)


@router.post("/actions/diagnose", response_model=LearningReport)
def run_learning_diagnosis(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    refresh: bool = Query(default=True),
) -> Any:
    user_id = str(current_user.id)
    return learning_report_service.build_report_and_sync_path(db, user_id, refresh_profile=refresh)


@router.post("/actions/review-plan", response_model=ReviewPlan)
def generate_review_plan(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    refresh: bool = Query(default=True),
) -> Any:
    user_id = str(current_user.id)
    return learning_report_service.build_review_plan(db, user_id, refresh_profile=refresh)


@router.post("/actions/mistake-digest", response_model=MistakeDigest)
def generate_mistake_digest(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    refresh: bool = Query(default=True),
) -> Any:
    user_id = str(current_user.id)
    return learning_report_service.build_mistake_digest(db, user_id, refresh_profile=refresh)
