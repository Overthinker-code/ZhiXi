from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat_thread import ChatThread, ChatThreadCreate, ChatThreadUpdate

router = APIRouter()


@router.post("/threads", response_model=ChatThread)
def create_thread(
    *,
    db: Session = Depends(deps.get_db),
    thread_in: ChatThreadCreate,
    current_user: CurrentUser,
) -> Any:
    user_id = str(current_user.id) if current_user else None
    thread = chat_thread_provider.create_with_defaults(db, obj_in=thread_in, user_id=user_id)
    return thread


@router.get("/threads", response_model=List[ChatThread])
def read_threads(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentUser,
) -> Any:
    user_id = str(current_user.id) if current_user else None
    if not user_id:
        return []
    return chat_thread_provider.get_multi_by_user(db, user_id=user_id, skip=skip, limit=limit)


@router.get("/threads/{thread_id}", response_model=ChatThread)
def read_thread(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: str,
    current_user: CurrentUser,
) -> Any:
    user_id = str(current_user.id) if current_user else None
    thread = chat_thread_provider.get_by_thread_id_and_user(db, thread_id=thread_id, user_id=user_id) if user_id else None
    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found")
    return thread


@router.put("/threads/{thread_id}", response_model=ChatThread)
def update_thread(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: str,
    thread_in: ChatThreadUpdate,
    current_user: CurrentUser,
) -> Any:
    user_id = str(current_user.id) if current_user else None
    thread = chat_thread_provider.get_by_thread_id_and_user(db, thread_id=thread_id, user_id=user_id) if user_id else None
    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found")
    return chat_thread_provider.update(db, db_obj=thread, obj_in=thread_in)


@router.delete("/threads/{thread_id}", response_model=ChatThread)
def delete_thread(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: str,
    current_user: CurrentUser,
) -> Any:
    user_id = str(current_user.id) if current_user else None
    if not user_id:
        raise HTTPException(status_code=404, detail="Chat thread not found")
    thread = chat_thread_provider.remove_by_thread_id_and_user(db, thread_id=thread_id, user_id=user_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Chat thread not found")
    return thread
