from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.schemas.learning_path import LearningPathPublic
from app.services.learning_path_service import learning_path_service

router = APIRouter()


@router.get("/me", response_model=LearningPathPublic | None)
def get_my_learning_path(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
) -> Any:
    return learning_path_service.get_for_user(db, str(current_user.id))
