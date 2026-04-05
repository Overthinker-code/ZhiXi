from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.models.chat_thread import ChatThread as ChatThreadORM
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat_thread import ChatThread, ChatThreadCreate, ChatThreadUpdate

router = APIRouter()


def _thread_to_api(row: ChatThreadORM) -> ChatThread:
    """ORM → Pydantic，避免 FastAPI 默认解析在 Pydantic v2 下失败导致 500。"""
    if hasattr(ChatThread, "model_validate"):
        return ChatThread.model_validate(row, from_attributes=True)
    return ChatThread.from_orm(row)


@router.post("/threads", response_model=ChatThread)
def create_thread(
    *,
    db: Session = Depends(deps.get_db),
    thread_in: ChatThreadCreate,
    current_user: CurrentUser,
) -> Any:
    user_id = str(current_user.id) if current_user else None
    thread = chat_thread_provider.create_with_defaults(db, obj_in=thread_in, user_id=user_id)
    return _thread_to_api(thread)


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
    rows = chat_thread_provider.get_multi_by_user(db, user_id=user_id, skip=skip, limit=limit)
    return [_thread_to_api(r) for r in rows]


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
    return _thread_to_api(thread)


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
    updated = chat_thread_provider.update(db, db_obj=thread, obj_in=thread_in)
    return _thread_to_api(updated)


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
    return _thread_to_api(thread)
