from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.agent_task import AgentTaskPublic
from app.services.agent_task_service import agent_task_service

router = APIRouter()


@router.get("/agent/tasks/{session_id}", response_model=list[AgentTaskPublic])
def read_agent_tasks(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
):
    user_id = str(current_user.id)
    thread = chat_thread_provider.get_by_thread_id_and_user(
        db, thread_id=session_id, user_id=user_id
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return agent_task_service.list_latest(db, session_id=session_id, user_id=user_id)
