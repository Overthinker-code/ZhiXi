from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.schemas.learning_task import LearningTaskPublic, LearningTaskUpdate
from app.services.learning_task_service import learning_task_service

router = APIRouter()


@router.get("/learning/current-task", response_model=LearningTaskPublic | None)
def get_current_learning_task(
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
):
    user_id = str(current_user.id)
    task = learning_task_service.get_current(db, user_id=user_id)
    return task or learning_task_service.recover_from_recent_history(
        db, user_id=user_id
    )


@router.patch("/learning/current-task", response_model=LearningTaskPublic)
def update_current_learning_task(
    request: LearningTaskUpdate,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
):
    task = learning_task_service.update_current(
        db,
        user_id=str(current_user.id),
        changes=request.model_dump(exclude_unset=True),
    )
    if not task:
        raise HTTPException(status_code=404, detail="Current learning task not found")
    return task
