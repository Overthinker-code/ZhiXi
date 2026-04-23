from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.services.ai_usage_logger import summarize_recent_metrics

router = APIRouter()


@router.get("/overview")
def read_ai_metrics_overview(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    days: int = Query(default=7, ge=1, le=30),
) -> Any:
    _ = current_user
    return summarize_recent_metrics(db, days=days)
