from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.schemas.student_hub import (
    AchievementsPublic,
    PracticeSummaryPublic,
    StudentNotificationsPublic,
    StudyGroupsPublic,
)
from app.services.student_hub_service import student_hub_service

router = APIRouter()


@router.get("/messages", response_model=StudentNotificationsPublic)
def list_messages(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> Any:
    return student_hub_service.get_messages(db, str(current_user.id), limit=limit)


@router.get("/groups", response_model=StudyGroupsPublic)
def list_groups(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> Any:
    return student_hub_service.get_groups(db, str(current_user.id))


@router.get("/practice/summary", response_model=PracticeSummaryPublic)
def practice_summary(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> Any:
    return student_hub_service.get_practice_summary(db, str(current_user.id))


@router.get("/achievements", response_model=AchievementsPublic)
def list_achievements(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> Any:
    return student_hub_service.get_achievements(db, str(current_user.id))
