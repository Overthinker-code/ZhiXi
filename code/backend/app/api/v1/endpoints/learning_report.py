from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.schemas.learning_report import LearningReport, ReviewPlan, MistakeDigest
from app.services.learning_report_service import learning_report_service

router = APIRouter()


@router.get("/me", response_model=LearningReport)
def get_my_learning_report(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    refresh: bool = Query(default=False),
) -> Any:
    user_id = str(current_user.id)
    return learning_report_service.build_report(db, user_id, refresh_profile=refresh)


@router.post("/actions/diagnose", response_model=LearningReport)
def run_learning_diagnosis(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    refresh: bool = Query(default=True),
) -> Any:
    user_id = str(current_user.id)
    return learning_report_service.build_report(db, user_id, refresh_profile=refresh)


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
