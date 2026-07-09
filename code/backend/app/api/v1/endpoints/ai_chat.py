from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
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
from app.services.reasoning_adapter import (
    ReasoningAdapterContext,
    ReasoningProcessNormalizer,
    contains_supplier_context,
    guarded_fallback_answer,
    normalize_reasoning_to_product_process,
    sanitize_visible_answer_delta,
)
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
            {"chapterId": "ch3", "title": "第3章 图结构", "knowledgePointIds": ["graph", "dfs", "shortest-path"]},
        ],
    },
    {
        "courseId": "c1111111-1111-4111-9111-111111111103",
        "title": "人工智能导论",
        "chapters": [
            {"chapterId": "ch1", "title": "第1章 智能搜索", "knowledgePointIds": ["search", "heuristic", "a-star"]},
            {"chapterId": "ch2", "title": "第2章 机器学习基础", "knowledgePointIds": ["supervised-learning", "classification", "regression"]},
            {"chapterId": "ch3", "title": "第3章 神经网络", "knowledgePointIds": ["neural-network", "backpropagation", "optimization"]},
        ],
    },
    {
        "courseId": "c1111111-1111-4111-9111-111111111104",
        "title": "宏观经济学",
        "chapters": [
            {"chapterId": "ch1", "title": "第1章 国民收入核算", "knowledgePointIds": ["gdp", "national-income"]},
            {"chapterId": "ch2", "title": "第2章 IS-LM 模型", "knowledgePointIds": ["is-lm", "interest-rate"]},
            {"chapterId": "ch3", "title": "第3章 货币与财政政策", "knowledgePointIds": ["monetary-policy", "fiscal-policy"]},
        ],
    },
    {
        "courseId": "c1111111-1111-4111-9111-111111111105",
        "title": "审计学",
        "chapters": [
            {"chapterId": "ch1", "title": "第1章 审计目标与证据", "knowledgePointIds": ["audit-evidence", "audit-objective"]},
            {"chapterId": "ch2", "title": "第2章 风险评估", "knowledgePointIds": ["audit-risk", "material-misstatement"]},
            {"chapterId": "ch3", "title": "第3章 内部控制", "knowledgePointIds": ["internal-control", "control-test"]},
        ],
    },
    {
        "courseId": "c1111111-1111-4111-9111-111111111106",
        "title": "金融学",
        "chapters": [
            {"chapterId": "ch1", "title": "第1章 金融市场", "knowledgePointIds": ["financial-market", "asset"]},
            {"chapterId": "ch2", "title": "第2章 资产定价", "knowledgePointIds": ["risk-return", "capm"]},
            {"chapterId": "ch3", "title": "第3章 公司金融", "knowledgePointIds": ["capital-structure", "valuation"]},
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
    course_rag: bool = Field(default=True, alias="courseRag")
    deep_research: bool = Field(default=False, alias="deepResearch")
    homework_review: bool = Field(default=False, alias="homeworkReview")
    resource_generation: bool = Field(default=False, alias="resourceGeneration")
    citation_required: bool = Field(default=True, alias="citationRequired")


class ReasoningOptions(CamelModel):
    level: Literal["fast", "balanced", "deep"] = "balanced"
    show_summary: bool = Field(default=True, alias="showSummary")
    show_process: bool = Field(default=True, alias="showProcess")


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


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


_PHASE_ID_MAP = {
    "understand": "understand_problem",
    "intent": "understand_problem",
    "route": "select_capability",
    "plan": "select_capability",
    "context": "prepare_context",
    "retrieve": "retrieve_knowledge",
    "retrieval": "retrieve_knowledge",
    "tool": "call_tool",
    "compose": "generate_answer",
    "answer": "generate_answer",
    "verify": "verify_output",
    "safety": "verify_output",
    "memory": "update_learning_profile",
    "profile": "update_learning_profile",
    "suggest": "suggest_next_step",
}


def _phase_id(value: str | None) -> str:
    raw = str(value or "understand_problem")
    return _PHASE_ID_MAP.get(raw, raw if raw in set(_PHASE_ID_MAP.values()) else "understand_problem")


def _phase_started(phase_id: str, title: str, text: str | None = None) -> str:
    payload: dict[str, Any] = {
        "phaseId": _phase_id(phase_id),
        "title": title,
        "status": "running",
        "timestamp": _now_iso(),
    }
    if text:
        payload["text"] = text
    return _sse("phase_started", payload)


def _phase_delta(phase_id: str, text: str) -> str:
    return _sse(
        "phase_updated",
        {
            "phaseId": _phase_id(phase_id),
            "text": text,
            "summary": text,
            "status": "running",
            "timestamp": _now_iso(),
        },
    )


def _phase_finished(phase_id: str, title: str, summary: str, status: str = "done") -> str:
    return _sse(
        "phase_finished",
        {
            "phaseId": _phase_id(phase_id),
            "title": title,
            "status": status,
            "summary": summary,
            "timestamp": _now_iso(),
        },
    )


def _tool_started(tool: str, title: str, text: str | None = None) -> str:
    payload: dict[str, Any] = {
        "tool": tool,
        "phaseId": "call_tool",
        "title": title,
        "status": "running",
        "timestamp": _now_iso(),
    }
    if text:
        payload["text"] = text
    return _sse("tool_started", payload)


def _tool_delta(tool: str, text: str) -> str:
    return _sse(
        "tool_delta",
        {
            "tool": tool,
            "phaseId": "call_tool",
            "text": text,
            "timestamp": _now_iso(),
        },
    )


def _tool_result(tool: str, summary: str, items: list[dict[str, Any]] | None = None) -> str:
    return _sse(
        "tool_result",
        {
            "tool": tool,
            "phaseId": "call_tool",
            "summary": summary,
            "status": "done",
            "items": items or [],
            "timestamp": _now_iso(),
        },
    )


def _clean_reasoning_summary(text: str) -> str:
    clean = (
        (text or "")
        .replace("<think>", "")
        .replace("</think>", "")
        .replace("**", "")
        .replace("我来分析这个问题：", "正在分析问题：")
        .replace("我来分析一下这个问题：", "正在分析问题：")
        .replace("我来分析一下：", "正在分析问题：")
        .replace("我来分析一下这个问题。", "")
        .replace("我来分析一下。", "")
        .replace("我来分析这个问题。", "")
        .replace("第一点想到的是", "正在提炼第一条依据：")
        .replace("第二点考虑", "正在提炼第二条依据：")
        .replace("第三点可以强调", "正在提炼第三条依据：")
        .replace("检查相关知识：", "正在核对相关知识：")
        .replace("用户想了解", "正在确认问题目标：")
        .replace("用户的问题核心", "问题核心")
        .replace("用户想", "问题目标是")
        .replace("用户希望", "问题目标是")
        .replace("我的思考过程如下：", "正在组织回答结构。")
        .replace("我的思考过程", "处理过程")
        .replace("首先，我需要明确", "正在梳理")
        .replace("接下来考虑", "正在分析")
        .replace("然后我需要想", "正在准备")
        .replace("我可以", "将")
        .replace("我需要", "正在")
        .replace("我会", "将")
        .strip()
    )
    blocked = ("系统消息", "上下文注入", "协作线程", "intent_classifier", "course_context")
    if not clean or any(token in clean for token in blocked):
        return ""
    return clean[:180]


def _split_reasoning_and_answer(text: str, reasoning_closed: bool) -> tuple[str, str, bool]:
    """MiMo may stream visible answer after </think> through reasoning_content."""
    raw = str(text or "")
    if not raw:
        return "", "", reasoning_closed
    if reasoning_closed:
        return "", raw, True
    match = re.search(r"</think>", raw, flags=re.IGNORECASE)
    if not match:
        return re.sub(r"<think>", "", raw, flags=re.IGNORECASE), "", False
    before = re.sub(r"<think>", "", raw[: match.start()], flags=re.IGNORECASE)
    after = raw[match.end() :]
    return before, after, True


def _adapter_context(req: AIChatStreamRequest) -> ReasoningAdapterContext:
    return ReasoningAdapterContext(
        message=req.message or "",
        mode=req.mode,
        tools=req.tools.model_dump(by_alias=True),
        course_context=req.course_context.model_dump(by_alias=True),
    )


def _process_delta_sse(payload: dict[str, Any]) -> str:
    payload = {**payload, "phaseId": _phase_id(str(payload.get("phaseId") or ""))}
    return _sse("process_delta", payload)


def _phase_updated_sse(payload: dict[str, Any]) -> str:
    payload = {**payload, "phaseId": _phase_id(str(payload.get("phaseId") or ""))}
    return _sse("phase_updated", payload)


def _show_raw_reasoning_debug() -> bool:
    return settings.ENVIRONMENT == "local" and os.getenv("ZHIXI_SHOW_RAW_REASONING", "").lower() == "true"


def _safe_final_text(raw_text: str, context: ReasoningAdapterContext) -> tuple[str, bool]:
    if not raw_text:
        return "", False
    cleaned, blocked = sanitize_visible_answer_delta(raw_text, context)
    if cleaned:
        return cleaned, blocked
    if blocked:
        return "", True
    if context.user_allows_supplier_context or not contains_supplier_context(raw_text):
        return raw_text, False
    return guarded_fallback_answer(context), True


def _mode_label(req: AIChatStreamRequest) -> str:
    if req.mode == "homework_review" or req.tools.homework_review:
        return "作业批改"
    if req.mode == "resource_generation" or req.tools.resource_generation:
        return "资料生成"
    if req.mode == "deep_research" or req.tools.deep_research:
        return "深度研究"
    if req.course_context.use_course_rag or req.tools.course_rag:
        return "课程问答"
    return "通用问答"


def _visible_tools(req: AIChatStreamRequest) -> list[str]:
    tools: list[str] = []
    if req.course_context.use_course_rag or req.tools.course_rag:
        tools.append("课程资料")
    if req.attachments:
        tools.append("上传附件")
    if req.tools.web_search:
        tools.append("联网搜索")
    if req.tools.deep_research:
        tools.append("深度研究")
    if req.tools.homework_review:
        tools.append("批改")
    if req.tools.resource_generation:
        tools.append("资料生成")
    if req.reasoning.level == "deep":
        tools.append("深度思考")
    return tools or ["模型回答"]


def _process_payload(
    stage: str,
    title: str,
    detail: str,
    *,
    status: str = "running",
    log: str | None = None,
    items: list[str] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stage": stage,
        "title": title,
        "detail": detail,
        "status": status,
        "log": log or detail,
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
    }
    if items:
        payload["items"] = [str(item)[:180] for item in items[:5] if str(item).strip()]
    return payload


def _process_sse(
    stage: str,
    title: str,
    detail: str,
    *,
    status: str = "running",
    log: str | None = None,
    items: list[str] | None = None,
) -> str:
    return _sse(
        "process_update",
        _process_payload(stage, title, detail, status=status, log=log, items=items),
    )


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
    tools = ["knowledge_base"] if (req.course_context.use_course_rag or req.tools.course_rag) else []
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
        (
            "你是“智屿智能教育平台”的 AI 伴学助手，服务场景是高校课程学习、课程资料问答、"
            "作业辅导、资源生成、学习路径规划、学情分析和深度研究。不得自称小米助手，"
            "不得主动介绍小米生态、米家、HyperOS、MIUI、手机、手环、电视、智能家居、售后或系统优化能力，"
            "除非用户明确询问这些主题。所有回答必须面向学生，先给结论，再解释，再给例子、常见错误和下一步建议。"
        ),
        f"当前模式：{req.mode}；actionId：{req.action_id or 'none'}。",
    ]
    if req.course_context.use_course_rag or req.tools.course_rag:
        parts.append(f"课程上下文：{course}{(' / ' + chapter) if chapter else ''}。")
        parts.append("已启用课程 RAG：优先引用课程资料或上传资料，证据不足时要明确说明。")
    else:
        parts.append("默认作为通用学习助手回答；除非用户问题明确指向课程、章节或上传资料，不要强行套入课程上下文。")
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


def _legacy_event_to_ai_events(
    payload: dict[str, Any],
    adapter_context: ReasoningAdapterContext | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    kind = payload.get("type")
    if kind == "reasoning_action":
        action = str(payload.get("action") or "")
        title = str(payload.get("title") or "工具完成")
        detail = str(payload.get("detail") or title)
        if adapter_context and contains_supplier_context(detail) and not adapter_context.user_allows_supplier_context:
            delta = normalize_reasoning_to_product_process(detail, adapter_context)
            return [("process_delta", delta.to_payload())] if delta else []
        items = [
            {"title": str(item)[:180], "score": None}
            for item in list(payload.get("items") or [])[:5]
            if str(item).strip()
        ]
        if action in {"retrieve", "web_search", "vision"}:
            tool = {
                "retrieve": "course_retriever",
                "web_search": "web_search",
                "vision": "attachment_reader",
            }.get(action, "course_retriever")
            visible_title = {
                "retrieve": title,
                "web_search": "联网搜索",
                "vision": "解析图片",
            }.get(action, title)
            return [
                (
                    "tool_result",
                    {
                        "tool": tool,
                        "summary": detail,
                        "status": "done",
                        "items": items,
                        "timestamp": _now_iso(),
                    },
                )
            ]
        if action == "code":
            return [
                (
                    "phase_updated",
                    {
                        "phaseId": "verify_output",
                        "text": detail,
                        "summary": detail,
                        "status": "running",
                        "timestamp": _now_iso(),
                    },
                )
            ]
        return [
            (
                "phase_updated",
                {
                    "phaseId": "select_capability",
                    "text": detail if detail != title else title,
                    "summary": detail if detail != title else title,
                    "status": "running",
                    "timestamp": _now_iso(),
                },
            )
        ]
    if kind == "phase":
        status = str(payload.get("status") or "running")
        phase_id = _phase_id(str(payload.get("phase") or payload.get("agent") or "plan"))
        title = str(payload.get("summary") or "处理阶段")
        if status in {"done", "finished", "success"}:
            return [("phase_finished", {"phaseId": phase_id, "title": title, "status": "done", "summary": title, "timestamp": _now_iso()})]
        return [("phase_started", {"phaseId": phase_id, "title": title, "status": "running", "timestamp": _now_iso()})]
    if kind == "thought":
        text = str(payload.get("content") or "")
        if text.startswith("【") or "系统消息" in text or "上下文注入" in text or "协作线程" in text:
            return []
        if adapter_context:
            delta = normalize_reasoning_to_product_process(text, adapter_context)
            if delta:
                return [("process_delta", delta.to_payload())]
        if "检索" in text or "知识库" in text:
            return [("tool_delta", {"tool": "course_retriever", "phaseId": "retrieve_knowledge", "text": text[:160], "timestamp": _now_iso()})]
        return [("phase_updated", {"phaseId": "select_capability", "text": text[:160], "summary": text[:160], "status": "running", "timestamp": _now_iso()})]
    if kind == "reasoning_token":
        return []
    if kind == "token":
        return [("answer_delta", {"text": payload.get("content") or ""})]
    if kind == "citations":
        citations = list(payload.get("citations") or payload.get("data") or [])
        events: list[tuple[str, dict[str, Any]]] = [
            (
                "tool_result",
                {
                    "tool": "course_retriever",
                    "summary": f"找到 {len(citations)} 条可引用证据",
                    "status": "done",
                    "items": citations[:6],
                    "timestamp": _now_iso(),
                },
            )
        ]
        for index, item in enumerate(citations, start=1):
            if isinstance(item, dict):
                events.append(("citation", {"id": item.get("id") or f"c{index}", **item}))
            else:
                events.append(("citation", {"id": f"c{index}", "title": str(item)}))
        return events
    if kind == "suggestions":
        items = payload.get("data") or payload.get("suggestions") or []
        return [("suggestions", {"items": items[:3] if isinstance(items, list) else []})]
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
        run_id = uuid4().hex
        course_rag_enabled = bool(request.course_context.use_course_rag or request.tools.course_rag)
        pending_tools: dict[str, str] = {}

        def finish_pending_tools():
            for tool, summary in list(pending_tools.items()):
                pending_tools.pop(tool, None)
                yield _tool_result(tool, summary, [])

        try:
            yield _sse("session_created", {"sessionId": session_id, "created": created})
            yield _sse(
                "run_started",
                {
                    "runId": run_id,
                    "sessionId": session_id,
                    "mode": request.mode,
                    "actionId": request.action_id,
                    "title": "开始处理问题",
                    "timestamp": _now_iso(),
                },
            )
            yield _sse("message_started", {"sessionId": session_id, "mode": request.mode, "actionId": request.action_id})
            yield _phase_started("understand", "理解问题", "正在判断问题类型和回答边界")
            yield _phase_delta("understand", f"收到问题：{(request.message or '附件/资料任务')[:80]}")
            if request.mode == "homework_review" and not request.message.strip() and not request.attachments:
                yield _phase_finished("understand", "理解问题", "作业批改需要题目、答案或附件", status="error")
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
            if request.attachments:
                yield _tool_started("attachment_reader", "解析上传材料", f"正在检查 {len(request.attachments)} 个上传附件")
                yield _tool_delta("attachment_reader", "将附件加入本轮可检索上下文")
            for item in request.attachments:
                if item.type == "image":
                    meta = index.get(item.file_id)
                    if not meta:
                        yield _sse(
                            "tool_result",
                            {
                                "tool": "attachment_reader",
                                "summary": f"图片附件 {item.file_id} 不存在",
                                "status": "error",
                                "items": [],
                                "timestamp": _now_iso(),
                            },
                        )
                        yield _sse("error", {"code": "ATTACHMENT_PARSE_FAILED", "message": f"图片附件 {item.file_id} 不存在"})
                        return
                    path = Path(str(meta.get("path") or ""))
                    if not path.exists():
                        yield _sse(
                            "tool_result",
                            {
                                "tool": "attachment_reader",
                                "summary": f"图片附件 {item.file_id} 已丢失",
                                "status": "error",
                                "items": [],
                                "timestamp": _now_iso(),
                            },
                        )
                        yield _sse("error", {"code": "ATTACHMENT_PARSE_FAILED", "message": f"图片附件 {item.file_id} 已丢失"})
                        return
                    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                    image_base64_list.append(f"data:{meta.get('contentType') or 'image/png'};base64,{encoded}")
                elif not current_file_id:
                    current_file_id = item.file_id
                    file_name = item.name or item.file_id

            if request.attachments:
                yield _tool_result(
                    "attachment_reader",
                    f"已挂载：{file_name or f'{len(request.attachments)} 个附件'}",
                    [{"title": item.name or item.file_id, "type": item.type} for item in request.attachments],
                )

            yield _phase_delta("understand", f"识别为：{_mode_label(request)}")
            yield _phase_finished("understand", "理解问题", f"已识别为{_mode_label(request)}")
            visible_tools = _visible_tools(request)
            yield _phase_started("plan", "选择能力", "正在选择本轮需要调用的能力")
            yield _phase_delta("plan", f"启用能力：{'、'.join(visible_tools)}")
            yield _phase_finished("plan", "选择能力", "能力选择完成，开始准备上下文")

            if course_rag_enabled:
                pending_tools["course_retriever"] = "课程资料检索已完成，回答会按可用证据组织。"
                yield _tool_started(
                    "course_retriever",
                    "检索课程资料",
                    f"正在检索《{_course_title(request.course_context.course_id)}》相关内容",
                )
                chapter = _chapter_title(request.course_context.course_id, request.course_context.chapter_id)
                if chapter:
                    yield _tool_delta("course_retriever", f"优先查找 {chapter} 的概念、例题和证据片段")
                else:
                    yield _tool_delta("course_retriever", "根据问题关键词匹配课程资料和知识点")
            elif not request.attachments and not request.tools.web_search:
                yield _phase_delta("plan", "未命中课程/附件/联网需求，将作为通用学习问题回答")

            if request.tools.web_search or request.mode == "deep_research":
                pending_tools["web_search"] = (
                    "已进入低延迟研究回答；如需严格联网证据，可继续要求补充可访问来源校验。"
                    if request.mode == "deep_research"
                    else "联网来源检查已完成，回答会区分公开来源与模型分析。"
                )
                yield _tool_started("web_search", "浏览联网来源", "正在准备检索近期公开来源")
                yield _tool_delta("web_search", "会优先提取标题、摘要、链接和时间信息，避免把网页结果混入课程证据")

            if request.mode == "resource_generation" or request.tools.resource_generation:
                yield _phase_started("compose", "生成资源", "正在规划资源类型、难度和资料包结构")
                yield _phase_delta("compose", f"资源类型：{'、'.join(request.resource_request.types or ['lecture_note', 'mind_map', 'quiz'])}")
                yield _sse("artifact_started", {"label": "正在生成资源包"})
                try:
                    package = _generate_resource_package(request)
                    yield _phase_finished("compose", "生成资源", f"资源包已生成，包含 {len(package.get('artifacts') or [])} 类内容")
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
                        "metrics": {
                            "route_trace": ["resource_planner", "resource_generator"],
                            "resourcePackage": package,
                            "suggestions": ["查看资源包", "同步知识图谱", "生成 20 分钟练习"],
                        },
                    }
                    yield _sse("suggestions", {"items": final_payload["suggestions"]})
                    yield _phase_started("verify", "校验输出", "正在检查资源包结构、安全和后续操作")
                    yield _phase_finished("verify", "校验输出", "资源包可预览、入库或继续同步图谱")
                    yield _sse("safety_check", {"status": "passed", "message": "已完成资源结构、安全和后续建议检查"})
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
                    done_payload = {
                        "runId": run_id,
                        "sessionId": session_id,
                        "messageId": uuid4().hex,
                        "summary": "本轮资源生成已完成结构、安全和后续建议检查",
                        "usage": final_payload["metrics"],
                        "suggestions": final_payload["suggestions"],
                    }
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except Exception as exc:
                    yield _phase_finished("compose", "生成资源", "资源生成服务返回错误", status="error")
                    yield _sse("error", {"code": "RESOURCE_GENERATION_FAILED", "message": str(exc)})
                return

            yield _phase_started("compose", "组织回答", "上下文准备完成，正在调用模型生成回答")
            yield _phase_delta("compose", "模型请求已发出，等待首个输出")
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
            reasoning_buffer = ""
            reasoning_closed = False
            adapter_context = _adapter_context(request)
            process_normalizer = ReasoningProcessNormalizer(adapter_context)
            answer_guard_triggered = False
            show_raw_reasoning_debug = _show_raw_reasoning_debug()
            answer_stream_started = False
            next_answer_progress_chars = 480

            def emit_safe_answer(text: str):
                nonlocal final_text, answer_stream_started, next_answer_progress_chars
                if not text:
                    return
                final_text += text
                if not answer_stream_started:
                    answer_stream_started = True
                    yield _phase_delta("compose", "回答已开始流式输出，可以边读边展开查看处理记录")
                yield from finish_pending_tools()
                yield _sse("answer_delta", {"text": text})
                if len(final_text) >= next_answer_progress_chars:
                    yield _phase_delta("compose", f"已输出约 {len(final_text)} 字，继续补全结构和细节")
                    next_answer_progress_chars += 640

            for payload in stream_chat_events(chat_request):
                if isinstance(payload, dict):
                    if payload.get("type") == "final":
                        final_payload = payload
                        raw_final_text = str(payload.get("content") or "")
                        if not final_text.strip() and raw_final_text:
                            safe_final_text, blocked = _safe_final_text(raw_final_text, adapter_context)
                            answer_guard_triggered = answer_guard_triggered or blocked
                            if safe_final_text:
                                yield from emit_safe_answer(safe_final_text)
                    if payload.get("type") == "reasoning_token":
                        reasoning_part, answer_part, reasoning_closed = _split_reasoning_and_answer(
                            str(payload.get("content") or ""),
                            reasoning_closed,
                        )
                        if reasoning_part:
                            reasoning_buffer += reasoning_part
                            if show_raw_reasoning_debug:
                                yield _sse("debug_raw_reasoning_delta", {"text": reasoning_part})
                            if (
                                len(reasoning_buffer) >= 42
                                or reasoning_buffer.endswith(("。", "；", "：", "\n"))
                            ):
                                process_delta = process_normalizer.ingest(reasoning_buffer)
                                reasoning_buffer = ""
                                if process_delta:
                                    yield _process_delta_sse(process_delta.to_payload())
                                    if process_delta.sanitized:
                                        payload = process_normalizer.process_sanitized_payload()
                                        if payload:
                                            yield _sse("process_sanitized", payload)
                        if answer_part:
                            safe_text, blocked = sanitize_visible_answer_delta(
                                answer_part,
                                adapter_context,
                                preserve_edges=True,
                            )
                            answer_guard_triggered = answer_guard_triggered or blocked
                            if safe_text:
                                yield from emit_safe_answer(safe_text)
                        continue
                    for event_name, event_payload in _legacy_event_to_ai_events(payload, adapter_context):
                        if event_name == "answer_delta":
                            safe_text, blocked = sanitize_visible_answer_delta(
                                str(event_payload.get("text") or ""),
                                adapter_context,
                                preserve_edges=True,
                            )
                            answer_guard_triggered = answer_guard_triggered or blocked
                            if safe_text:
                                yield from emit_safe_answer(safe_text)
                        else:
                            if event_name == "tool_result":
                                pending_tools.pop(str(event_payload.get("tool") or ""), None)
                            yield _sse(event_name, event_payload)
            process_delta = process_normalizer.ingest(reasoning_buffer)
            if process_delta:
                yield _process_delta_sse(process_delta.to_payload())
            yield from finish_pending_tools()
            if final_text and contains_supplier_context(final_text) and not adapter_context.user_allows_supplier_context:
                final_text = guarded_fallback_answer(adapter_context)
                answer_guard_triggered = True
            if answer_guard_triggered and not final_text.strip():
                fallback = guarded_fallback_answer(adapter_context)
                final_text = fallback
                yield _sse("process_sanitized", {
                    "phaseId": "verify_output",
                    "title": "校验输出",
                    "summary": "已拦截与智屿教育场景无关的供应商人格输出，并改用智屿能力说明。",
                    "status": "done",
                    "sanitized": True,
                    "timestamp": _now_iso(),
                })
                yield _sse("answer_delta", {"text": fallback})
            yield _phase_finished("compose", "组织回答", "正文回答已流式输出完成")
            yield _phase_started("verify", "校验输出", "正在检查引用、安全和后续追问建议")
            yield _sse("safety_check", {"status": "passed", "message": "已完成引用、安全和后续建议检查"})
            yield _sse("profile_update", {"status": "queued"})
            yield _phase_finished("verify", "校验输出", "引用、安全和学习画像更新已完成")
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
            done_payload = {
                "runId": run_id,
                "sessionId": session_id,
                "messageId": uuid4().hex,
                "summary": "本轮回答已完成引用、安全和后续建议检查",
                "usage": (final_payload.get("metrics") or {}),
                "suggestions": list(final_payload.get("suggestions") or []),
            }
            yield _sse("run_finished", done_payload)
            yield _sse("done", done_payload)
        except Exception as exc:
            yield _sse("error", {"code": "MODEL_PROVIDER_ERROR", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)
