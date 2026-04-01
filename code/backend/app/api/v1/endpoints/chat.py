from typing import Any, List
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_provider import chat_provider
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat import Chat, ChatCreate, ChatUpdate
from app.schemas.chat_feedback import ChatFeedback, ChatFeedbackCreate
from app.ai.chat_service import get_chat_runtime_settings, ChatRequest
from app.ai.chat_engine import stream_chat_events, chat_service
from app.models.chat_feedback import ChatFeedback as ChatFeedbackModel
from app.services.pending_actions import pending_action_store
from app.services.realtime_event_bus import realtime_event_bus
from app.services.chat_semantic_cache import chat_semantic_cache

router = APIRouter()


class ChatStreamRequest(BaseModel):
    user_input: str
    thread_id: str = "default"
    system_prompt: str = ""
    prompt_key: str = "tutor"
    rag_k: int = 4
    strict_mode: bool = False
    active_tools: list[str] | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    selected_text: str | None = None
    surrounding_context: str | None = None
    video_time: str | None = None
    course_module: str | None = None


class ChatResumeRequest(BaseModel):
    pending_action_id: str
    approve: bool = True


class EventTriggerRequest(BaseModel):
    thread_id: str = "default"
    event_type: str = "intervention"
    content: str
    payload: dict[str, Any] | None = None


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


@router.post("/stream")
def stream_chat(
    *,
    request: ChatStreamRequest,
    current_user: CurrentUser,
):
    def event_stream():
        try:
            chat_request = ChatRequest(
                user_input=request.user_input,
                thread_id=request.thread_id,
                system_prompt=request.system_prompt,
                prompt_key=request.prompt_key,
                rag_k=request.rag_k if request.rag_k in (3, 4, 5) else 4,
                strict_mode=bool(request.strict_mode),
                active_tools=request.active_tools,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                top_k=request.top_k,
                selected_text=request.selected_text,
                surrounding_context=request.surrounding_context,
                video_time=request.video_time,
                course_module=request.course_module,
                user_id=str(current_user.id) if current_user else None,
                is_admin=bool(getattr(current_user, "is_superuser", False))
                if current_user
                else False,
            )
            for payload in stream_chat_events(chat_request):
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as exc:
            error_payload = {"type": "error", "content": str(exc)}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/selection-query")
def selection_query(
    *,
    request: ChatStreamRequest,
    current_user: CurrentUser,
) -> Any:
    try:
        chat_request = ChatRequest(
            user_input=request.user_input,
            thread_id=request.thread_id,
            system_prompt=request.system_prompt,
            prompt_key=request.prompt_key,
            rag_k=request.rag_k if request.rag_k in (3, 4, 5) else 4,
            strict_mode=bool(request.strict_mode),
            active_tools=request.active_tools,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            selected_text=request.selected_text,
            surrounding_context=request.surrounding_context,
            video_time=request.video_time,
            course_module=request.course_module,
            user_id=str(current_user.id) if current_user else None,
            is_admin=bool(getattr(current_user, "is_superuser", False))
            if current_user
            else False,
        )
        return chat_service(chat_request).model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
def resume_chat(
    *,
    request: ChatResumeRequest,
    current_user: CurrentUser,
) -> Any:
    action = pending_action_store.get(request.pending_action_id)
    user_id = str(current_user.id) if current_user else "anonymous"
    if not action or action.user_id != user_id:
        raise HTTPException(status_code=404, detail="Pending action not found")
    if request.approve:
        confirmed = pending_action_store.confirm(request.pending_action_id)
        return {
            "status": "confirmed",
            "message": "计划已确认并写入日历（演示模式）。",
            "action": pending_action_store.as_dict(confirmed),  # type: ignore[arg-type]
        }
    rejected = pending_action_store.reject(request.pending_action_id)
    return {
        "status": "rejected",
        "message": "已取消写入日历。",
        "action": pending_action_store.as_dict(rejected),  # type: ignore[arg-type]
    }


@router.get("/cache/hotspots")
def cache_hotspots(current_user: CurrentUser, top_k: int = 10):
    return {"items": chat_semantic_cache.hotspots(top_k)}


@router.post("/event-trigger")
def event_trigger(
    *,
    request: EventTriggerRequest,
    current_user: CurrentUser,
):
    user_id = str(current_user.id) if current_user else "anonymous"
    realtime_event_bus.publish(
        user_id=user_id,
        event_type=request.event_type,
        content=request.content,
        payload=request.payload or {"thread_id": request.thread_id},
    )
    return {"status": "queued"}


@router.get("/events/stream")
def stream_events(current_user: CurrentUser):
    user_id = str(current_user.id) if current_user else "anonymous"

    async def event_stream():
        while True:
            events = realtime_event_bus.pop_all(user_id)
            if events:
                for event in events:
                    payload = {
                        "type": "intervention",
                        "event_type": event.event_type,
                        "content": event.content,
                        "payload": event.payload,
                        "created_at": event.created_at,
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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
