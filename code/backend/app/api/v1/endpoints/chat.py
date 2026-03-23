from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_provider import chat_provider
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat import Chat, ChatCreate, ChatUpdate
from app.schemas.chat_feedback import ChatFeedback, ChatFeedbackCreate
from app.ai.chat_service import get_chat_runtime_settings
from app.models.chat_feedback import ChatFeedback as ChatFeedbackModel

router = APIRouter()


@router.get("/settings")
def read_chat_settings(current_user: CurrentUser) -> Any:
    """Return runtime chat settings for frontend display and controls."""
    return get_chat_runtime_settings()


@router.post("/feedback", response_model=ChatFeedback)
def submit_feedback(
    *,
    db: Session = Depends(deps.get_db),
    feedback_in: ChatFeedbackCreate,
    current_user: CurrentUser,
) -> Any:
    """
    Submit feedback for a chat response.
    """
    chat = chat_provider.get(db, id=feedback_in.record_id)
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat record not found"
        )
    
    feedback = ChatFeedbackModel(
        record_id=feedback_in.record_id,
        user_id=str(current_user.id) if current_user else None,
        rating=feedback_in.rating,
        prompt_key=feedback_in.prompt_key,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.post("/", response_model=Chat)
def create_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_in: ChatCreate,
    current_user: CurrentUser,
) -> Any:
    """
    创建新的对话并获取AI响应。
    """
    try:
        chat = chat_provider.create_with_ai_response(
            db, obj_in=chat_in, current_user=current_user
        )
        return chat
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{thread_id}", response_model=List[Chat])
def read_chat_history(
    *,
    db: Session = Depends(deps.get_db),
    thread_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: CurrentUser,
) -> Any:
    """
    获取指定thread_id的对话历史。
    用户只能访问自己的对话历史。
    """
    user_id = str(current_user.id) if current_user else None
    if user_id:
        thread = chat_thread_provider.get_by_thread_id_and_user(
            db, thread_id=thread_id, user_id=user_id
        )
        if not thread:
            raise HTTPException(
                status_code=404,
                detail="Chat thread not found or access denied"
            )
    chats = chat_provider.get_chat_history(
        db, thread_id=thread_id, skip=skip, limit=limit
    )
    return chats


@router.get("/by-id/{chat_id}", response_model=Chat)
def read_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    current_user: CurrentUser,
) -> Any:
    """
    通过ID获取特定的对话。
    """
    chat = chat_provider.get(db, id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )
    user_id = str(current_user.id) if current_user else None
    if user_id:
        thread = chat_thread_provider.get_by_thread_id_and_user(
            db, thread_id=chat.thread_id, user_id=user_id
        )
        if not thread:
            raise HTTPException(
                status_code=404,
                detail="Chat not found or access denied"
            )
    return chat


@router.delete("/by-id/{chat_id}", response_model=Chat)
def delete_chat(
    *,
    db: Session = Depends(deps.get_db),
    chat_id: int,
    current_user: CurrentUser,
) -> Any:
    """
    删除特定的对话记录。
    用户只能删除自己的对话记录。
    """
    chat = chat_provider.get(db, id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=404,
            detail="Chat not found"
        )
    user_id = str(current_user.id) if current_user else None
    if user_id:
        thread = chat_thread_provider.get_by_thread_id_and_user(
            db, thread_id=chat.thread_id, user_id=user_id
        )
        if not thread:
            raise HTTPException(
                status_code=404,
                detail="Chat not found or access denied"
            )
    chat = chat_provider.remove(db, id=chat_id)
    return chat 
