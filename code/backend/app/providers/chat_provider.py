import logging
from typing import List
from sqlalchemy.orm import Session

from app.providers.base_provider import BaseProvider
from app.models.chat import Chat
from app.models import User
from app.schemas.chat import ChatCreate, ChatUpdate
from app.ai.chat_service import (
    chat_service as ai_chat_service,
    ChatRequest,
    resolve_system_prompt,
)
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat_thread import ChatThreadCreate
from app.services.background_tasks import schedule_memory_profile_refresh
from app.services.chat_artifact_service import upsert_chat_artifact, attach_chat_artifact
from app.services.content_safety_service import (
    content_safety_service,
    stable_block_message,
)


logger = logging.getLogger(__name__)


_ALLOWED_TOOL_MODES = {
    "chat",
    "exercise_grading",
    "image_tutoring",
    "digital_human_explain",
}


def _normalize_tool_mode(tool_mode: str | None) -> str:
    normalized = (tool_mode or "chat").strip()
    return normalized if normalized in _ALLOWED_TOOL_MODES else "chat"


class ChatProvider(BaseProvider[Chat, ChatCreate, ChatUpdate]):
    def get_by_thread_id(self, db: Session, *, thread_id: str) -> List[Chat]:
        """获取指定thread_id的所有对话记录"""
        return db.query(Chat).filter(Chat.thread_id == thread_id).all()

    def create_with_ai_response(
        self, db: Session, *, obj_in: ChatCreate, current_user: User | None = None
    ) -> Chat:
        """创建新的对话记录并获取AI响应"""
        input_safety = content_safety_service.ensure_safe(
            obj_in.user_input,
            direction="input",
        )
        user_id = str(current_user.id) if current_user else None
        thread_id = obj_in.thread_id
        if not thread_id:
            thread = chat_thread_provider.create_with_defaults(
                db, obj_in=ChatThreadCreate(), user_id=user_id
            )
            thread_id = thread.thread_id
        else:
            existing = chat_thread_provider.get_by_thread_id(db, thread_id=thread_id)
            if not existing:
                chat_thread_provider.create_with_defaults(
                    db, obj_in=ChatThreadCreate(thread_id=thread_id), user_id=user_id
                )

        ai_request = ChatRequest(
            system_prompt=obj_in.system_prompt or "",
            prompt_key=obj_in.prompt_key or "tutor",
            rag_k=obj_in.rag_k if obj_in.rag_k in (3, 4, 5) else 4,
            strict_mode=bool(obj_in.strict_mode),
            active_tools=obj_in.active_tools,
            max_tokens=obj_in.max_tokens,
            temperature=obj_in.temperature,
            top_p=obj_in.top_p,
            top_k=obj_in.top_k,
            user_input=obj_in.user_input,
            thread_id=thread_id,
            user_id=user_id,
            is_admin=bool(getattr(current_user, "is_superuser", False)) if current_user else False,
            current_file_id=obj_in.current_file_id,
            file_name=obj_in.file_name,
            route_context=obj_in.route_context,
            context_refs=obj_in.context_refs,
            image_base64_list=obj_in.image_base64_list,
            tool_mode=_normalize_tool_mode(obj_in.tool_mode),
            force_agent=obj_in.force_agent,
            force_cache=bool(obj_in.force_cache),
            debug_mode=bool(obj_in.debug_mode),
        )
        ai_response = ai_chat_service(ai_request)
        output_safety = content_safety_service.review(
            ai_response.response,
            direction="output",
        )
        metrics = dict(ai_response.metrics or {})
        metrics["content_safety"] = {
            "input": input_safety.public_dict(),
            "output": output_safety.public_dict(),
        }
        ai_response.metrics = metrics
        if output_safety.blocked:
            ai_response.response = stable_block_message("output")
            ai_response.citations = []
            ai_response.suggestions = []
            ai_response.confidence = "low"
            ai_response.grounding_mode = "safety_blocked"
        effective_system_prompt = resolve_system_prompt(
            obj_in.prompt_key or "tutor", obj_in.system_prompt or ""
        )

        chat_data = {
            "thread_id": thread_id,
            "user_input": obj_in.user_input,
            "system_prompt": effective_system_prompt,
            "response": ai_response.response,
        }
        db_obj = Chat(**chat_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        schedule_memory_profile_refresh(user_id)

        setattr(db_obj, "tool_calls", ai_response.tool_calls)
        artifact = upsert_chat_artifact(
            db,
            chat_id=db_obj.id,
            agent=ai_response.agent,
            intent=ai_response.intent,
            routing_reason=ai_response.routing_reason,
            citations=ai_response.citations,
            confidence=ai_response.confidence,
            grounding_mode=ai_response.grounding_mode,
            suggestions=ai_response.suggestions,
            metrics=ai_response.metrics,
        )
        attach_chat_artifact(db_obj, artifact)
        return db_obj

    def get_chat_history(
        self, db: Session, *, thread_id: str, skip: int = 0, limit: int = 100
    ) -> List[Chat]:
        """获取指定thread_id的对话历史"""
        return (
            db.query(Chat)
            .filter(Chat.thread_id == thread_id)
            .order_by(Chat.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def save_stream_turn(
        self,
        db: Session,
        *,
        thread_id: str,
        user_input: str,
        response: str,
        system_prompt: str | None = None,
        agent: str | None = None,
        intent: str | None = None,
        routing_reason: str | None = None,
        citations: list[dict] | None = None,
        confidence: str | None = None,
        grounding_mode: str | None = None,
        suggestions: list[str] | None = None,
        metrics: dict | None = None,
    ) -> Chat:
        """持久化一轮流式/非流式对话，供历史接口与 prior_turns 注入使用。"""
        chat_data = {
            "thread_id": thread_id,
            "user_input": user_input,
            "system_prompt": system_prompt or "",
            "response": response,
        }
        db_obj = Chat(**chat_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        if any(
            value
            for value in (
                agent,
                intent,
                routing_reason,
                citations,
                confidence,
                grounding_mode,
                suggestions,
                metrics,
            )
        ):
            artifact = upsert_chat_artifact(
                db,
                chat_id=db_obj.id,
                agent=agent,
                intent=intent,
                routing_reason=routing_reason,
                citations=citations,
                confidence=confidence,
                grounding_mode=grounding_mode,
                suggestions=suggestions,
                metrics=metrics,
            )
            attach_chat_artifact(db_obj, artifact)
        try:
            thread = chat_thread_provider.get_by_thread_id(db, thread_id=thread_id)
            thread_user_id = getattr(thread, "user_id", None)
            if thread_user_id:
                from uuid import UUID

                from sqlalchemy import or_
                from sqlmodel import select

                from app.models import Course
                from app.services.conversation_context_service import (
                    conversation_context_service,
                )
                from app.services.learning_report_service import learning_report_service

                conversation_context_service.append_turn(
                    db,
                    session_id=thread_id,
                    user_id=str(thread_user_id),
                    user_content=user_input,
                    assistant_content=response,
                    legacy_chat_id=db_obj.id,
                    assistant_metadata={
                        "agent": agent,
                        "intent": intent,
                        "citations": citations or [],
                        "confidence": confidence,
                        "grounding_mode": grounding_mode,
                        "suggestions": suggestions or [],
                    },
                )
                course_id = None
                course_ref = str(getattr(thread, "course", None) or "").strip()
                if course_ref:
                    try:
                        candidate_id = UUID(course_ref)
                        if db.get(Course, candidate_id):
                            course_id = candidate_id
                    except ValueError:
                        course = db.exec(
                            select(Course).where(
                                or_(Course.name == course_ref, Course.identifier == course_ref)
                            )
                        ).first()
                        course_id = course.id if course else None
                safe_citations = [
                    {
                        key: item.get(key)
                        for key in ("title", "document", "source", "source_type", "chunk_id")
                        if item.get(key) is not None
                    }
                    for item in (citations or [])[:12]
                    if isinstance(item, dict)
                ]
                topic = str(
                    getattr(thread, "knowledge_point", None)
                    or next(
                        (
                            item.get("knowledge_point")
                            or item.get("title")
                            or item.get("document")
                            for item in (citations or [])
                            if isinstance(item, dict)
                        ),
                        "学习对话",
                    )
                )[:160]
                learning_report_service.record_evidence(
                    db,
                    user_id=UUID(str(thread_user_id)),
                    course_id=course_id,
                    knowledge_point=topic,
                    source_type="knowledge_base" if safe_citations else "agent_chat",
                    source_id=str(db_obj.id),
                    event_type="grounded_response" if safe_citations else "chat_turn",
                    weight=0.15,
                    score=None,
                    payload={
                        "agent": agent,
                        "intent": intent,
                        "grounding_mode": grounding_mode,
                        "resource_type": "knowledge_base" if safe_citations else "dialogue",
                        "citations": safe_citations,
                    },
                )
                db.commit()
            schedule_memory_profile_refresh(thread_user_id)
        except Exception as exc:
            logger.warning(
                "chat turn saved but memory profile refresh could not be scheduled: %s",
                exc,
            )
        return db_obj

chat_provider = ChatProvider(Chat)
