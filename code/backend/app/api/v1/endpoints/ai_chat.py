from __future__ import annotations

import base64
import json
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session

from app.ai.chat_engine import (
    resolve_stream_user_text_for_storage,
    stream_chat_events,
)
from app.ai.chat_models import ChatRequest
from app.ai.chat_service import resolve_system_prompt
from app.api import deps
from app.api.deps import CurrentUser
from app.core.config import settings
from app.providers.chat_provider import chat_provider
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat_thread import ChatThreadCreate
from app.schemas.resource_generation import ResourceGenerationRequest, ResourceKind
from app.services.background_tasks import schedule_memory_profile_refresh
from app.services.rag_service import RAGService
from app.services.resource_generation_service import resource_generation_service

router = APIRouter()
rag_service = RAGService()

_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

ATTACHMENT_DIR = Path(settings.BASE_PATH) / "uploads" / "chat_attachments"
ATTACHMENT_INDEX = ATTACHMENT_DIR / "index.json"

COURSES = [
    {
        "courseId": "c1111111-1111-4111-9111-111111111101",
        "title": "数据库系统原理",
        "chapters": [
            {
                "chapterId": "ch1",
                "title": "第1章 关系数据模型",
                "knowledgePointIds": ["relation-model", "relational-algebra", "sql-basic"],
            },
            {
                "chapterId": "ch2",
                "title": "第2章 完整性与约束",
                "knowledgePointIds": ["entity-integrity", "referential-integrity"],
            },
            {
                "chapterId": "ch3",
                "title": "第3章 ER 模型",
                "knowledgePointIds": ["er-model", "entity", "relationship"],
            },
            {
                "chapterId": "ch4",
                "title": "第4章 规范化与恢复",
                "knowledgePointIds": ["functional-dependency", "normal-form", "recovery"],
            },
        ],
    },
    {
        "courseId": "c1111111-1111-4111-9111-111111111102",
        "title": "数据结构",
        "chapters": [
            {"chapterId": "ch1", "title": "第1章 线性结构", "knowledgePointIds": ["list", "stack", "queue"]},
            {"chapterId": "ch2", "title": "第2章 树结构", "knowledgePointIds": ["tree", "heap", "bst"]},
        ],
    },
]


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class CourseContext(CamelModel):
    course_id: str | None = Field(default=None, alias="courseId")
    chapter_id: str | None = Field(default=None, alias="chapterId")
    knowledge_point_ids: list[str] = Field(default_factory=list, alias="knowledgePointIds")
    use_course_rag: bool = Field(default=True, alias="useCourseRag")


class ToolOptions(CamelModel):
    web_search: bool = Field(default=False, alias="webSearch")
    deep_research: bool = Field(default=False, alias="deepResearch")
    homework_review: bool = Field(default=False, alias="homeworkReview")
    resource_generation: bool = Field(default=False, alias="resourceGeneration")
    citation_required: bool = Field(default=True, alias="citationRequired")


class ReasoningOptions(CamelModel):
    level: Literal["fast", "balanced", "deep"] = "balanced"
    show_summary: bool = Field(default=True, alias="showSummary")


class AttachmentRef(CamelModel):
    file_id: str = Field(alias="fileId")
    type: Literal["image", "pdf", "doc", "ppt", "code", "other"] = "other"
    name: str | None = None


class ResourceRequest(CamelModel):
    types: list[str] = Field(default_factory=list)
    difficulty: Literal["basic", "normal", "advanced"] = "normal"
    target: str = ""


class AIChatStreamRequest(CamelModel):
    session_id: str | None = Field(default=None, alias="sessionId")
    message: str = ""
    mode: Literal["tutor", "homework_review", "resource_generation", "deep_research"] = "tutor"
    action_id: str | None = Field(default=None, alias="actionId")
    course_context: CourseContext = Field(default_factory=CourseContext, alias="courseContext")
    tools: ToolOptions = Field(default_factory=ToolOptions)
    reasoning: ReasoningOptions = Field(default_factory=ReasoningOptions)
    attachments: list[AttachmentRef] = Field(default_factory=list)
    resource_request: ResourceRequest = Field(default_factory=ResourceRequest, alias="resourceRequest")


def _sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _read_attachment_index() -> dict[str, Any]:
    if not ATTACHMENT_INDEX.exists():
        return {}
    try:
        return json.loads(ATTACHMENT_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_attachment_index(index: dict[str, Any]) -> None:
    ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _attachment_type(filename: str, content_type: str | None) -> str:
    name = filename.lower()
    if (content_type or "").startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "image"
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith((".doc", ".docx", ".txt", ".md", ".markdown")):
        return "doc"
    if name.endswith((".ppt", ".pptx")):
        return "ppt"
    if name.endswith((".py", ".js", ".ts", ".java", ".cpp", ".c", ".sql")):
        return "code"
    return "other"


def _course_title(course_id: str | None) -> str:
    for course in COURSES:
        if course["courseId"] == course_id:
            return str(course["title"])
    return "数据库系统原理"


def _chapter_title(course_id: str | None, chapter_id: str | None) -> str:
    for course in COURSES:
        if course["courseId"] == course_id:
            for chapter in course.get("chapters", []):
                if chapter.get("chapterId") == chapter_id:
                    return str(chapter.get("title") or "")
    return ""


def _prior_turns(db: Session, thread_id: str, user_id: str | None) -> list[dict[str, str]]:
    if user_id:
        thread = chat_thread_provider.get_by_thread_id_and_user(db, thread_id=thread_id, user_id=user_id)
        if not thread:
            return []
    rows = chat_provider.get_chat_history(db, thread_id=thread_id, skip=0, limit=48)
    turns: list[dict[str, str]] = []
    for row in reversed(rows):
        turns.append({"user": row.user_input or "", "assistant": row.response or ""})
    return turns


def _ensure_session(db: Session, user_id: str | None, session_id: str | None) -> tuple[str, bool]:
    if session_id and user_id:
        thread = chat_thread_provider.get_by_thread_id_and_user(db, thread_id=session_id, user_id=user_id)
        if thread:
            return thread.thread_id, False
    if session_id:
        thread = chat_thread_provider.get_by_thread_id(db, thread_id=session_id)
        if thread and (not user_id or thread.user_id == user_id):
            return thread.thread_id, False
    thread = chat_thread_provider.create_with_defaults(db, obj_in=ChatThreadCreate(), user_id=user_id)
    return thread.thread_id, True


def _active_tools(req: AIChatStreamRequest) -> list[str]:
    tools = ["knowledge_base"] if req.course_context.use_course_rag else []
    if req.tools.web_search or req.mode == "deep_research":
        tools.append("web_search")
    if req.attachments:
        tools.append("search_uploaded_document")
    return list(dict.fromkeys(tools))


def _tool_mode(req: AIChatStreamRequest) -> str:
    if req.mode == "homework_review" or req.tools.homework_review:
        return "exercise_grading"
    if any(item.type == "image" for item in req.attachments):
        return "image_tutoring"
    return "chat"


def _force_agent(req: AIChatStreamRequest) -> str | None:
    if req.mode == "homework_review":
        return "grading_agent"
    if req.mode == "deep_research":
        return "web_research_agent"
    return None


def _system_prompt(req: AIChatStreamRequest) -> str:
    course = _course_title(req.course_context.course_id)
    chapter = _chapter_title(req.course_context.course_id, req.course_context.chapter_id)
    parts = [
        "你是智屿 AI 学习助手。所有回答必须面向学生，先给结论，再解释，再给例子、常见错误和下一步建议。",
        f"当前模式：{req.mode}；actionId：{req.action_id or 'none'}。",
        f"课程上下文：{course}{(' / ' + chapter) if chapter else ''}。",
    ]
    if req.course_context.use_course_rag:
        parts.append("已启用课程 RAG：优先引用课程资料或上传资料，证据不足时要明确说明。")
    if req.mode == "homework_review":
        parts.append("作业批改必须输出：评分、错因、正确解法、同类练习和掌握度反馈。")
    if req.mode == "deep_research":
        parts.append("深度研究必须输出：研究计划、检索摘要、分析结论、证据边界和可继续验证的问题。")
    if req.mode == "resource_generation":
        parts.append("资料生成模式必须先说明资源规划，随后后端会生成可下载资源包。")
    return "\n".join(parts)


def _message_for_model(req: AIChatStreamRequest) -> str:
    message = (req.message or "").strip()
    if req.mode == "homework_review" and not message and not req.attachments:
        return "学生进入作业批改模式，但还没有提供题目、答案或附件。请要求学生上传材料，不要假装已批改。"
    if req.mode == "resource_generation" and not message:
        return f"请围绕{_course_title(req.course_context.course_id)}生成学习资料规划。"
    if req.mode == "deep_research" and message:
        return f"请按深度研究流程处理以下问题：{message}"
    return message or "请基于当前课程上下文给出学习建议。"


def _legacy_event_to_ai_events(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    kind = payload.get("type")
    if kind == "phase":
        status = str(payload.get("status") or "running")
        event = "agent_finished" if status in {"done", "finished", "success"} else "agent_started"
        return [(event, {"agent": payload.get("agent") or payload.get("phase") or "agent", "label": payload.get("summary") or ""})]
    if kind == "thought":
        text = str(payload.get("content") or "")
        if "检索" in text or "知识库" in text:
            return [("retrieval_started", {"source": "course", "label": text[:120]})]
        return [("agent_started", {"agent": payload.get("stage") or "orchestrator", "label": text[:160]})]
    if kind == "reasoning_token":
        return [("reasoning_summary_delta", {"text": payload.get("content") or ""})]
    if kind == "token":
        return [("answer_delta", {"text": payload.get("content") or ""})]
    if kind == "citations":
        citations = list(payload.get("citations") or payload.get("data") or [])
        events: list[tuple[str, dict[str, Any]]] = [
            ("retrieval_result", {"source": "course", "items": citations[:6]})
        ]
        for item in citations:
            events.append(("citation", item if isinstance(item, dict) else {"title": str(item)}))
        return events
    if kind == "error":
        return [("error", {"code": "MODEL_PROVIDER_ERROR", "message": payload.get("content") or "后端生成失败"})]
    return []


def _resource_kinds(types: list[str]) -> list[ResourceKind]:
    mapping: dict[str, ResourceKind] = {
        "lecture_note": "lecture_markdown",
        "mind_map": "mind_map",
        "quiz": "practice_markdown",
        "reading": "reading_list",
        "code_case": "case_project",
        "video_script": "video_script",
    }
    values = [mapping[item] for item in types if item in mapping]
    return values or ["lecture_markdown", "practice_markdown", "mind_map", "case_project", "video_script"]


def _generate_resource_package(req: AIChatStreamRequest) -> dict[str, Any]:
    difficulty = {
        "basic": "foundation",
        "normal": "standard",
        "advanced": "challenge",
    }.get(req.resource_request.difficulty, "standard")
    request = ResourceGenerationRequest(
        course_id=UUID(req.course_context.course_id) if req.course_context.course_id else None,
        node_id=(req.course_context.knowledge_point_ids or [""])[0] or None,
        node_label=(req.resource_request.target or req.message or "课程重点")[:120],
        source="tutor-chat",
        subject=_course_title(req.course_context.course_id),
        topic=(req.resource_request.target or req.message or "课程重点")[:120],
        learning_goal=req.message[:240] if req.message else "围绕当前薄弱点生成个性化学习资源",
        difficulty=difficulty,  # type: ignore[arg-type]
        target_minutes=45,
        resource_types=_resource_kinds(req.resource_request.types),
        use_web_search=bool(req.tools.web_search),
    )
    return resource_generation_service.generate(request).model_dump(mode="json")


@router.post("/sessions")
def create_ai_session(*, db: Session = Depends(deps.get_db), current_user: CurrentUser) -> Any:
    user_id = str(current_user.id) if current_user else None
    thread = chat_thread_provider.create_with_defaults(db, obj_in=ChatThreadCreate(), user_id=user_id)
    return {"sessionId": thread.thread_id, "title": thread.title, "createdAt": thread.created_at}


@router.get("/sessions")
def list_ai_sessions(*, db: Session = Depends(deps.get_db), current_user: CurrentUser) -> Any:
    user_id = str(current_user.id) if current_user else None
    rows = chat_thread_provider.get_multi_by_user(db, user_id=user_id, skip=0, limit=100) if user_id else []
    return [
        {"sessionId": row.thread_id, "title": row.title, "createdAt": row.created_at, "updatedAt": row.updated_at}
        for row in rows
    ]


@router.get("/sessions/{session_id}")
def get_ai_session(*, db: Session = Depends(deps.get_db), session_id: str, current_user: CurrentUser) -> Any:
    user_id = str(current_user.id) if current_user else None
    row = chat_thread_provider.get_by_thread_id_and_user(db, thread_id=session_id, user_id=user_id) if user_id else None
    if not row:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"sessionId": row.thread_id, "title": row.title, "createdAt": row.created_at, "updatedAt": row.updated_at}


@router.delete("/sessions/{session_id}")
def delete_ai_session(*, db: Session = Depends(deps.get_db), session_id: str, current_user: CurrentUser) -> Any:
    user_id = str(current_user.id) if current_user else None
    row = chat_thread_provider.remove_by_thread_id_and_user(db, thread_id=session_id, user_id=user_id) if user_id else None
    if not row:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"sessionId": row.thread_id, "deleted": True}


@router.get("/sessions/{session_id}/messages")
def get_ai_messages(*, db: Session = Depends(deps.get_db), session_id: str, current_user: CurrentUser) -> Any:
    user_id = str(current_user.id) if current_user else None
    if user_id and not chat_thread_provider.get_by_thread_id_and_user(db, thread_id=session_id, user_id=user_id):
        raise HTTPException(status_code=404, detail="Chat session not found")
    rows = chat_provider.get_chat_history(db, thread_id=session_id, skip=0, limit=100)
    messages: list[dict[str, Any]] = []
    for row in reversed(rows):
        messages.append({"role": "user", "content": row.user_input, "createdAt": row.created_at})
        messages.append({"role": "assistant", "content": row.response, "createdAt": row.created_at})
    return messages


@router.post("/attachments")
async def upload_ai_attachment(
    *,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
) -> Any:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    kind = _attachment_type(file.filename, file.content_type)
    if kind == "image":
        ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
        file_id = uuid4().hex
        suffix = Path(file.filename).suffix.lower() or mimetypes.guess_extension(file.content_type or "") or ".img"
        target = ATTACHMENT_DIR / f"{file_id}{suffix}"
        content = await file.read()
        target.write_bytes(content)
        index = _read_attachment_index()
        index[file_id] = {
            "fileId": file_id,
            "name": file.filename,
            "type": "image",
            "path": str(target),
            "contentType": file.content_type or "image/png",
            "sessionId": session_id,
            "ownerId": str(current_user.id),
            "createdAt": datetime.utcnow().isoformat(),
        }
        _write_attachment_index(index)
        return index[file_id]
    try:
        result = await rag_service.process_uploaded_file(
            file,
            scope="thread",
            owner_id=str(current_user.id),
            thread_id=session_id or "draft",
        )
        return {
            "fileId": result.get("file_id"),
            "name": file.filename,
            "type": kind,
            "chunks": result.get("chunks", 0),
            "preview": result.get("preview_snippet", ""),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "ATTACHMENT_PARSE_FAILED", "message": str(exc)})


@router.get("/attachments/{file_id}")
def get_ai_attachment(*, file_id: str, current_user: CurrentUser) -> Any:
    _ = current_user
    item = _read_attachment_index().get(file_id)
    if not item:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return item


@router.get("/context/courses")
def list_context_courses(current_user: CurrentUser) -> Any:
    _ = current_user
    return COURSES


@router.get("/context/course/{course_id}")
def get_context_course(course_id: str, current_user: CurrentUser) -> Any:
    _ = current_user
    for course in COURSES:
        if course["courseId"] == course_id:
            return course
    raise HTTPException(status_code=404, detail="Course context not found")


@router.post("/resources/from-chat")
def generate_resources_from_chat(*, request: AIChatStreamRequest, current_user: CurrentUser) -> Any:
    _ = current_user
    return _generate_resource_package(request)


@router.post("/profile/update-from-chat")
def update_profile_from_chat(*, current_user: CurrentUser) -> Any:
    schedule_memory_profile_refresh(str(current_user.id) if current_user else None)
    return {"status": "queued"}


@router.post("/chat/stream")
def ai_chat_stream(
    *,
    db: Session = Depends(deps.get_db),
    request: AIChatStreamRequest,
    current_user: CurrentUser,
):
    user_id = str(current_user.id) if current_user else None
    session_id, created = _ensure_session(db, user_id, request.session_id)

    def event_stream():
        final_text = ""
        final_payload: dict[str, Any] = {}
        try:
            yield _sse("session_created", {"sessionId": session_id, "created": created})
            yield _sse("message_started", {"sessionId": session_id, "mode": request.mode, "actionId": request.action_id})
            if request.mode == "homework_review" and not request.message.strip() and not request.attachments:
                yield _sse(
                    "error",
                    {
                        "code": "ATTACHMENT_PARSE_FAILED",
                        "message": "作业批改需要先上传题目/答案，或在输入框粘贴题目文本。",
                    },
                )
                return

            image_base64_list: list[str] = []
            current_file_id: str | None = None
            file_name: str | None = None
            index = _read_attachment_index()
            for item in request.attachments:
                if item.type == "image":
                    meta = index.get(item.file_id)
                    if not meta:
                        yield _sse("error", {"code": "ATTACHMENT_PARSE_FAILED", "message": f"图片附件 {item.file_id} 不存在"})
                        return
                    path = Path(str(meta.get("path") or ""))
                    if not path.exists():
                        yield _sse("error", {"code": "ATTACHMENT_PARSE_FAILED", "message": f"图片附件 {item.file_id} 已丢失"})
                        return
                    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                    image_base64_list.append(f"data:{meta.get('contentType') or 'image/png'};base64,{encoded}")
                elif not current_file_id:
                    current_file_id = item.file_id
                    file_name = item.name or item.file_id

            yield _sse("agent_started", {"agent": "intent_classifier", "label": "正在识别学习任务"})
            yield _sse("agent_finished", {"agent": "intent_classifier", "label": request.mode})
            yield _sse("agent_started", {"agent": "course_context", "label": "正在读取课程上下文与学习画像"})
            yield _sse("agent_finished", {"agent": "course_context", "label": _course_title(request.course_context.course_id)})
            if request.course_context.use_course_rag:
                yield _sse("retrieval_started", {"source": "course", "label": "正在检索课程资料"})

            if request.mode == "resource_generation" or request.tools.resource_generation:
                yield _sse("agent_started", {"agent": "resource_planner", "label": "正在规划资源类型与难度"})
                yield _sse(
                    "agent_finished",
                    {
                        "agent": "resource_planner",
                        "label": "、".join(request.resource_request.types or ["lecture_note", "mind_map", "quiz"]),
                    },
                )
                yield _sse("artifact_started", {"label": "正在生成资源包"})
                try:
                    package = _generate_resource_package(request)
                    yield _sse("artifact_finished", package)
                    final_text = (
                        f"已围绕“{request.resource_request.target or request.message or '当前主题'}”生成资源包 "
                        f"`{package.get('package_id')}`，包含 {len(package.get('artifacts') or [])} 类学习资源。"
                        "你可以先查看讲义和练习题，再把薄弱知识点同步到课程图谱。"
                    )
                    yield _sse("answer_delta", {"text": final_text})
                    final_payload = {
                        "agent": "resource_generator",
                        "content": final_text,
                        "citations": [],
                        "confidence": "medium",
                        "grounding_mode": "tool",
                        "suggestions": ["查看资源包", "同步知识图谱", "生成 20 分钟练习"],
                        "metrics": {"route_trace": ["resource_planner", "resource_generator"]},
                    }
                    yield _sse("safety_check", {"status": "passed", "citationRequired": request.tools.citation_required})
                    yield _sse("profile_update", {"status": "queued"})
                    if user_id:
                        try:
                            chat_provider.save_stream_turn(
                                db,
                                thread_id=session_id,
                                user_input=request.message or "资料生成",
                                response=final_text,
                                system_prompt=_system_prompt(request),
                                agent="resource_generator",
                                intent=request.mode,
                                routing_reason=f"mode={request.mode}; actionId={request.action_id or 'none'}",
                                citations=[],
                                confidence="medium",
                                grounding_mode="tool",
                                suggestions=final_payload["suggestions"],
                                metrics=final_payload["metrics"],
                            )
                            schedule_memory_profile_refresh(user_id)
                        except Exception:
                            pass
                    yield _sse(
                        "done",
                        {
                            "sessionId": session_id,
                            "messageId": uuid4().hex,
                            "usage": final_payload["metrics"],
                        },
                    )
                except Exception as exc:
                    yield _sse("error", {"code": "RESOURCE_GENERATION_FAILED", "message": str(exc)})
                return

            chat_request = ChatRequest(
                user_input=_message_for_model(request),
                thread_id=session_id,
                system_prompt=_system_prompt(request),
                prompt_key="tutor",
                rag_k=4,
                strict_mode=bool(request.tools.citation_required),
                active_tools=_active_tools(request),
                max_tokens=20000 if request.reasoning.level == "deep" else 14000,
                temperature=0.35,
                user_id=user_id,
                is_admin=bool(getattr(current_user, "is_superuser", False)) if current_user else False,
                prior_turns=_prior_turns(db, session_id, user_id) or None,
                current_file_id=current_file_id,
                file_name=file_name,
                route_context={
                    "mode": request.mode,
                    "actionId": request.action_id,
                    "courseContext": request.course_context.model_dump(by_alias=True),
                    "tools": request.tools.model_dump(by_alias=True),
                    "reasoning": request.reasoning.model_dump(by_alias=True),
                },
                context_refs=request.course_context.model_dump(by_alias=True),
                image_base64_list=image_base64_list,
                tool_mode=_tool_mode(request),  # type: ignore[arg-type]
                force_agent=_force_agent(request),  # type: ignore[arg-type]
                reasoning_enabled=request.reasoning.level in {"balanced", "deep"},
                debug_mode=False,
            )
            log_user = resolve_stream_user_text_for_storage(chat_request)
            for payload in stream_chat_events(chat_request):
                if isinstance(payload, dict):
                    if payload.get("type") == "final":
                        final_payload = payload
                        final_text = str(payload.get("content") or final_text)
                    for event_name, event_payload in _legacy_event_to_ai_events(payload):
                        yield _sse(event_name, event_payload)
            yield _sse("safety_check", {"status": "passed", "citationRequired": request.tools.citation_required})
            yield _sse("profile_update", {"status": "queued"})
            if final_text and user_id:
                try:
                    chat_provider.save_stream_turn(
                        db,
                        thread_id=session_id,
                        user_input=log_user,
                        response=final_text,
                        system_prompt=resolve_system_prompt("tutor", chat_request.system_prompt),
                        agent=str(final_payload.get("agent") or _force_agent(request) or "supervisor"),
                        intent=request.mode,
                        routing_reason=f"mode={request.mode}; actionId={request.action_id or 'none'}",
                        citations=list(final_payload.get("citations") or []),
                        confidence=str(final_payload.get("confidence") or "medium"),
                        grounding_mode=str(final_payload.get("grounding_mode") or "mixed"),
                        suggestions=list(final_payload.get("suggestions") or []),
                        metrics=final_payload.get("metrics") or {},
                    )
                    schedule_memory_profile_refresh(user_id)
                except Exception:
                    pass
            yield _sse(
                "done",
                {
                    "sessionId": session_id,
                    "messageId": uuid4().hex,
                    "usage": (final_payload.get("metrics") or {}),
                },
            )
        except Exception as exc:
            yield _sse("error", {"code": "MODEL_PROVIDER_ERROR", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)
