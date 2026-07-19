from __future__ import annotations

import asyncio
import base64
import contextvars
import json
import logging
import mimetypes
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlmodel import Session, select

from app.ai.chat_tools import get_llm, message_text
from app.ai.chat_engine import (
    resolve_stream_user_text_for_storage,
    stream_chat_events,
)
from app.ai.course_agent_registry import (
    CourseAgentContract,
    get_course_agent_contract,
    list_course_agent_contracts,
)
from app.ai.chat_models import ChatRequest
from app.ai.chat_service import resolve_system_prompt
from app.api import deps
from app.api.deps import CurrentUser
from app.core.config import settings
from app.core.upload_security import read_upload_limited, validate_upload
from app.models import Course, Resource
from app.providers.chat_provider import chat_provider
from app.providers.chat_thread_provider import chat_thread_provider
from app.schemas.chat_thread import ChatThreadCreate
from app.schemas.resource_generation import ResourceGenerationRequest, ResourceKind
from app.services.background_tasks import schedule_memory_profile_refresh
from app.services.course_agent_output_guard import (
    CourseAgentOutputGuard,
    is_initial_quiz_request,
)
from app.services.content_safety_service import (
    ContentSafetyBlockedError,
    ContentSafetyStreamGuard,
    content_safety_service,
    stable_block_message,
)
from app.services.rag_service import RAGService
from app.services import knowledge_graph_service
from app.services.agent_task_service import agent_task_service
from app.services.learning_task_service import learning_task_service
from app.services.generated_knowledge_graph_service import (
    KnowledgeGraphGenerationError,
    knowledge_graph_service as generated_knowledge_graph_service,
)
from app.services.quiz_service import QuizGenerationError, quiz_service
from app.services.reasoning_adapter import (
    ReasoningAdapterContext,
    ReasoningProcessNormalizer,
    contains_supplier_context,
    guarded_fallback_answer,
    normalize_reasoning_to_product_process,
    sanitize_visible_answer_delta,
)
from app.services.resource_package_service import (
    ResourcePackagePersistenceError,
    resource_package_service,
)
from app.services.chat_artifact_service import hydrate_chat_artifacts
from app.services.bailian_service import BailianImageRequest, bailian_service
from app.services.teaching_artifact_service import teaching_artifact_service
from app.services.media_generation_service import (
    GeneratedMedia,
    MediaGenerationError,
    is_seedance_credit_error,
    media_generation_service,
)
from app.services.vision_client import build_chat_image_context

router = APIRouter()
rag_service = RAGService()
logger = logging.getLogger(__name__)

_SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

ATTACHMENT_DIR = Path(settings.BASE_PATH) / "uploads" / "chat_attachments"
ATTACHMENT_INDEX = ATTACHMENT_DIR / "index.json"
GENERATED_IMAGE_DIR = Path(settings.BASE_PATH) / "uploads" / "generated_images"
GENERATED_ARTIFACT_DIR = Path(settings.BASE_PATH) / "uploads" / "generated_artifacts"


def _persist_chat_media(
    db: Session,
    *,
    owner_id: UUID,
    source_path: Path,
    content_type: str,
    provider: str,
    title: str,
    kind: str,
    topic: str,
    course_id: UUID | None,
    revised_prompt: str | None = None,
) -> dict[str, Any]:
    """Move a generated local file into the authenticated resource library."""
    course = db.get(Course, course_id) if course_id else None
    persisted = media_generation_service.persist_resource(
        db,
        owner_id=owner_id,
        media=GeneratedMedia(
            path=source_path,
            content_type=content_type,
            provider=provider,
            revised_prompt=revised_prompt,
        ),
        title=title,
        kind=kind,
        subject=course.name if course else "AI生成",
        knowledge_point=topic,
        course_id=getattr(course, "id", course_id) if course else None,
    )
    return {
        "resource_id": str(persisted.resource.id),
        "preview_url": persisted.preview_url,
        "download_url": persisted.download_url,
        "image_url": persisted.preview_url if kind == "image" else None,
        "provider": provider,
        "file_name": persisted.resource.file_name,
        "file_size": persisted.resource.file_size,
        "revised_prompt": revised_prompt or "",
    }

COURSES = [
    {
        "courseId": "c1111111-1111-4111-9111-111111111107",
        "title": "软件工程导论",
        "chapters": [
            {"chapterId": "ch01", "title": "第1章 软件工程学概述", "knowledgePointIds": ["software-crisis", "software-engineering", "software-characteristics"]},
            {"chapterId": "ch02", "title": "第2章 可行性研究", "knowledgePointIds": ["feasibility-study", "cost-benefit", "system-flowchart"]},
            {"chapterId": "ch03", "title": "第3章 需求分析", "knowledgePointIds": ["requirements-analysis", "srs", "dfd", "data-dictionary"]},
            {"chapterId": "ch04", "title": "第4章 形式化说明技术", "knowledgePointIds": ["formal-specification", "z-language", "state-machine"]},
            {"chapterId": "ch05", "title": "第5章 总体设计", "knowledgePointIds": ["architecture-design", "module-structure", "coupling-cohesion"]},
            {"chapterId": "ch06", "title": "第6章 详细设计", "knowledgePointIds": ["detailed-design", "process-design", "decision-table"]},
            {"chapterId": "ch07", "title": "第7章 实现", "knowledgePointIds": ["coding-style", "implementation", "white-box-testing", "black-box-testing"]},
            {"chapterId": "ch08", "title": "第8章 维护", "knowledgePointIds": ["software-maintenance", "maintainability", "reverse-engineering"]},
            {"chapterId": "ch09", "title": "第9章 面向对象方法学引论", "knowledgePointIds": ["object-oriented", "class", "object", "inheritance"]},
            {"chapterId": "ch10", "title": "第10章 面向对象分析", "knowledgePointIds": ["ooa", "use-case", "object-model", "dynamic-model"]},
            {"chapterId": "ch11", "title": "第11章 面向对象设计", "knowledgePointIds": ["ood", "class-diagram", "sequence-diagram", "interface-design"]},
            {"chapterId": "ch12", "title": "第12章 面向对象实现", "knowledgePointIds": ["oo-implementation", "programming-language", "reuse"]},
            {"chapterId": "ch13", "title": "第13章 软件项目管理", "knowledgePointIds": ["project-management", "risk-management", "schedule", "quality-management"]},
        ],
    },
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
    use_course_rag: bool = Field(default=False, alias="useCourseRag")


class ToolOptions(CamelModel):
    web_search: bool = Field(default=False, alias="webSearch")
    course_rag: bool = Field(default=False, alias="courseRag")
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
    message: str = Field(default="", max_length=8000)
    mode: Literal["tutor", "homework_review", "resource_generation", "deep_research"] = "tutor"
    action_id: str | None = Field(default=None, alias="actionId")
    agent_key: str | None = Field(default=None, alias="agentKey")
    course_context: CourseContext = Field(default_factory=CourseContext, alias="courseContext")
    tools: ToolOptions = Field(default_factory=ToolOptions)
    reasoning: ReasoningOptions = Field(default_factory=ReasoningOptions)
    attachments: list[AttachmentRef] = Field(default_factory=list)
    resource_request: ResourceRequest = Field(default_factory=ResourceRequest, alias="resourceRequest")

    @model_validator(mode="after")
    def require_user_input(self) -> "AIChatStreamRequest":
        has_message = bool(self.message.strip())
        has_attachment = bool(self.attachments)
        has_resource_target = bool(self.resource_request.target.strip())
        if not has_message and not has_attachment and not (
            self.mode == "resource_generation" and has_resource_target
        ):
            raise ValueError("message, attachment, or resource target is required")
        self.message = self.message.strip()
        return self


_TRACE_VERSION = "1.0"


class _ChatTraceRecorder:
    """Add auditable timing metadata without exposing prompts or model CoT."""

    _CATEGORY_BY_PHASE = {
        "understand_problem": "route",
        "select_capability": "plan",
        "prepare_context": "retrieval",
        "retrieve_knowledge": "retrieval",
        "call_tool": "tool",
        "generate_answer": "model",
        "verify_output": "safety",
        "update_learning_profile": "profile",
        "suggest_next_step": "output",
    }

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.sequence = 0
        self._started: dict[str, tuple[float, str]] = {}

    @staticmethod
    def _iso_now() -> str:
        return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"

    @staticmethod
    def _safe_key(value: Any) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip())[:80]

    def _identity(self, event: str, payload: dict[str, Any]) -> tuple[str, str, str]:
        phase_id = _phase_id(str(payload.get("phaseId") or ""))
        if event.startswith("tool_"):
            tool = self._safe_key(payload.get("tool") or "tool")
            return f"tool:{tool}", "call_tool", "tool"
        if event in {"answer_delta", "suggestions", "citation", "artifact_finished"}:
            return "output:answer", "generate_answer", "output"
        if event in {"run_started", "message_started", "session_created"}:
            return "run:lifecycle", phase_id, "route"
        if event in {"run_finished", "done"}:
            return "run:lifecycle", phase_id, "output"
        if event in {"safety_check", "process_sanitized"}:
            return "phase:verify_output", "verify_output", "safety"
        if event == "profile_update":
            return "phase:update_learning_profile", "update_learning_profile", "profile"
        safe_phase = self._safe_key(phase_id or event)
        return (
            f"phase:{safe_phase}",
            phase_id,
            self._CATEGORY_BY_PHASE.get(phase_id, "output"),
        )

    def enrich(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(payload)
        self.sequence += 1
        now_mono = time.perf_counter()
        now_iso = self._iso_now()
        step_id, phase_id, category = self._identity(event, enriched)
        enriched.setdefault("runId", self.run_id)
        enriched.setdefault("traceVersion", _TRACE_VERSION)
        enriched.setdefault("sequence", self.sequence)
        enriched.setdefault("stepId", step_id)
        enriched.setdefault("phaseId", phase_id)
        enriched.setdefault("category", category)
        enriched.setdefault("timestamp", now_iso)

        is_started = event in {"phase_started", "tool_started", "run_started", "message_started"}
        is_finished = event in {
            "phase_finished",
            "tool_result",
            "run_finished",
            "done",
            "error",
        }
        if is_started:
            self._started.setdefault(step_id, (now_mono, now_iso))
            enriched.setdefault("startedAt", self._started[step_id][1])
            enriched.setdefault("status", "running")
        elif step_id in self._started:
            enriched.setdefault("startedAt", self._started[step_id][1])

        if is_finished:
            started_mono, started_iso = self._started.pop(step_id, (now_mono, now_iso))
            enriched.setdefault("startedAt", started_iso)
            enriched.setdefault("finishedAt", now_iso)
            enriched.setdefault("durationMs", max(0, round((now_mono - started_mono) * 1000)))
            if event not in {"error"}:
                enriched.setdefault("status", "done")
        return enriched


_trace_recorder: contextvars.ContextVar[_ChatTraceRecorder | None] = contextvars.ContextVar(
    "chat_trace_recorder", default=None
)


def _sse(event: str, payload: dict[str, Any]) -> str:
    recorder = _trace_recorder.get()
    safe_payload = recorder.enrich(event, payload) if recorder is not None else payload
    return f"event: {event}\ndata: {json.dumps(safe_payload, ensure_ascii=False)}\n\n"


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


def _is_resource_generation_intent(message: str) -> bool:
    """Recognize explicit resource-creation requests from natural language.

    Quiz and graph intents are included because they are resource-producing
    agents, but their dedicated branches still run before the generic resource
    package branch.
    """

    text = re.sub(r"\s+", "", message or "")
    if _is_quiz_generation_intent(text) or _is_knowledge_graph_intent(text):
        return True
    resource_word = any(
        word in text
        for word in (
            "学习资料",
            "讲解文档",
            "学习文档",
            "讲义",
            "练习题",
            "习题",
            "题库",
            "专项练习",
            "思维导图",
            "代码案例",
            "视频脚本",
        )
    )
    action_word = any(
        word in text
        for word in ("生成", "创建", "制作", "整理", "给我出", "出一", "出题")
    )
    return resource_word and action_word


def _is_seedance_video_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    video_word = any(
        word in text
        for word in (
            "视频",
            "讲解视频",
            "教学视频",
            "动画",
            "动画短片",
            "演示视频",
            "短片",
        )
    )
    action_word = any(
        word in text
        for word in (
            "生成",
            "创建",
            "制作",
            "做一个",
            "做一段",
            "给我生成",
            "帮我生成",
        )
    )
    return video_word and action_word


def _is_ppt_generation_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    return any(word in text for word in ("PPT", "ppt", "课件", "演示文稿")) and any(
        word in text for word in ("生成", "创建", "制作", "整理", "做一份", "帮我做")
    )


def _is_scientific_chart_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if _is_structured_diagram_intent(message):
        return False
    chart_word = any(
        word in text
        for word in ("函数图像", "函数曲线", "坐标图", "折线图", "柱状图", "散点图", "科学图表", "实验曲线", "数据图表")
    )
    action_word = any(word in text for word in ("生成", "绘制", "画", "制作", "创建"))
    return chart_word and action_word


def _seedance_video_topic(message: str) -> str:
    if _is_stack_visual_topic(message):
        return "栈的后进先出与入栈出栈"
    text = re.sub(r"\s+", " ", message or "").strip()
    text = re.sub(r"^(?:请|请你|帮我|麻烦你|给我|我想要|我要)?", "", text)
    text = re.sub(r"^(?:生成|创建|制作|做)(?:一个|一段|一条|一下)?", "", text)
    text = re.sub(r"(?:的)?(?:讲解视频|教学视频|演示视频|动画短片|动画|视频|短片)$", "", text)
    return text.strip(" ，。！？：:的") or "当前学习主题"


def _is_stack_visual_topic(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "").lower()
    return any(token in text for token in ("栈", "lifo", "入栈", "出栈", "push", "pop"))


def _seedance_video_prompt(message: str) -> tuple[str, str]:
    topic = _seedance_video_topic(message)
    if _is_stack_visual_topic(message):
        return topic, (
            "Wide 16:9 landscape, fixed-camera educational animation of a stack data structure. "
            "Show exactly three unlabelled clean colored square blocks: orange at the bottom, blue in the middle, green at the top. "
            "Demonstrate the green top block entering from above and then leaving upward with clear directional arrows. "
            "Use a plain light background, stable framing, and reserve a clean lower subtitle-safe area. "
            "No text, no letters, no numbers, no symbols, no captions, no watermark, no logos, no extra blocks."
        )
    prompt = (
        f"Generate a clear 16:9 educational animation about: {topic}. "
        "Use simple information-graphics and a stable camera to show the core concept and process. "
        "Leave a clean subtitle-safe lower area for frontend overlays; do not generate Chinese small text, captions, logos, or watermarks."
    )
    return topic, prompt


def _extract_seedance_task_id(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("taskId"),
        payload.get("task_id"),
        payload.get("id"),
        payload.get("videoId"),
        payload.get("video_id"),
    ]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend(
            [
                data.get("taskId"),
                data.get("task_id"),
                data.get("id"),
                data.get("videoId"),
                data.get("video_id"),
            ]
        )
    for item in candidates:
        if item:
            return str(item)
    return ""


def _is_image_generation_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    if _is_structured_diagram_intent(message):
        return False
    image_word = any(
        word in text
        for word in (
            "图片",
            "图像",
            "配图",
            "插图",
            "概念图",
            "示意图",
            "海报",
            "画",
            "画一张",
            "生成图",
        )
    )
    action_word = any(
        word in text
        for word in (
            "生成",
            "创建",
            "制作",
            "画",
            "绘制",
            "给我生成",
            "帮我生成",
        )
    )
    return image_word and action_word and not _is_seedance_video_intent(message)


def _image_generation_topic(message: str) -> str:
    if _is_stack_visual_topic(message):
        return "栈的后进先出与入栈出栈"
    text = re.sub(r"\s+", " ", message or "").strip()
    text = re.sub(r"^#{1,6}\s*\d*[.、]?\s*", "", text)
    text = re.sub(r"^(?:请|请你|帮我|麻烦你|给我|我想要|我要)?", "", text)
    text = re.sub(r"^(?:生成|创建|制作|画|绘制)(?:一张|一个|一幅|一下)?", "", text)
    text = re.sub(r"(?:帮我|请|请你)?(?:生成|创建|制作|画|绘制)(?:一张|一个|一幅|一下)?(?:图片|图像|配图|插图|概念图|示意图|海报)?$", "", text)
    text = re.sub(r"(?:的)?(?:图片|图像|配图|插图|概念图|示意图|海报)$", "", text)
    return text.strip(" ，。！？：:的") or "当前学习主题"


def _is_diagram_image_request(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    return any(
        word in text
        for word in (
            "数据流图",
            "DFD",
            "dfd",
            "实体联系图",
            "实体关系图",
            "E-R图",
            "ER图",
            "ERD",
            "流程图",
            "系统流程",
            "业务流程",
            "数据对象",
        )
    )


def _is_structured_diagram_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    diagram_word = any(
        word in text
        for word in (
            "数据流图",
            "DFD",
            "dfd",
            "实体联系图",
            "实体关系图",
            "E-R图",
            "ER图",
            "ERD",
            "流程图",
            "系统流程",
            "业务流程",
            "类图",
            "时序图",
            "状态图",
            "用例图",
            "UML",
            "uml",
            "TCP拥塞控制",
            "tcp拥塞控制",
            "拥塞控制",
            "慢启动",
            "拥塞避免",
            "快速重传",
            "快速恢复",
            "滑动窗口",
            "窗口变化",
            "机制图",
            "原理图",
            "思维导图",
            "知识点导图",
            "知识导图",
        )
    )
    action_word = any(
        word in text
        for word in ("生成", "创建", "制作", "画", "绘制", "给我生成", "帮我生成", "描绘")
    )
    return diagram_word and action_word


def _structured_diagram_topic(message: str) -> str:
    topic = _image_generation_topic(message)
    return topic or "系统分析图"


def _structured_diagram_mermaid(message: str) -> tuple[str, str]:
    text = re.sub(r"\s+", "", message or "")
    if any(word in text for word in ("TCP拥塞控制", "tcp拥塞控制", "拥塞控制", "慢启动", "拥塞避免", "快速重传", "快速恢复")):
        return (
            "flowchart",
            """flowchart TD
    Start([连接建立]) --> SlowStart[慢启动 Slow Start]
    SlowStart -->|cwnd 指数增长<br/>每个 RTT 约翻倍| CheckThreshold{cwnd >= ssthresh?}
    CheckThreshold -->|否| SlowStart
    CheckThreshold -->|是| CongAvoid[拥塞避免 Congestion Avoidance]
    CongAvoid -->|cwnd 线性增长<br/>每 RTT 约 +1 MSS| Detect{检测到拥塞?}
    Detect -->|超时 Timeout| Timeout[严重拥塞]
    Timeout -->|ssthresh = cwnd / 2<br/>cwnd = 1 MSS| SlowStart
    Detect -->|3 个重复 ACK| FastRetransmit[快速重传 Fast Retransmit]
    FastRetransmit -->|ssthresh = cwnd / 2<br/>cwnd = ssthresh + 3 MSS| FastRecovery[快速恢复 Fast Recovery]
    FastRecovery -->|收到新的 ACK<br/>cwnd = ssthresh| CongAvoid
    Detect -->|未拥塞| CongAvoid

    classDef phase fill:#eef2ff,stroke:#4f46e5,color:#172033;
    classDef warn fill:#fff7ed,stroke:#f97316,color:#172033;
    class SlowStart,CongAvoid,FastRetransmit,FastRecovery phase;
    class Timeout warn;""",
        )
    if any(word in text for word in ("实体联系图", "实体关系图", "E-R图", "ER图", "ERD")) and not any(
        word in text for word in ("数据流图", "DFD", "dfd")
    ):
        return (
            "erDiagram",
            """erDiagram
    CUSTOMER ||--o{ ACCOUNT : owns
    CUSTOMER ||--o{ TRANSACTION_FORM : submits
    ACCOUNT ||--o{ TRANSACTION_FORM : records
    ACCOUNT ||--o{ INTEREST_STATEMENT : produces

    CUSTOMER {
      string customer_id "储户编号"
      string name "姓名"
      string id_no "证件号"
      string contact "联系方式"
    }
    ACCOUNT {
      string account_id "账户号"
      string deposit_type "存款类型"
      date open_date "开户日期"
      date maturity_date "到期日"
      float interest_rate "利率"
      string password_hash "密码凭据"
    }
    TRANSACTION_FORM {
      string form_id "单据号"
      string transaction_type "存取类型"
      float amount "金额"
      date transaction_date "办理日期"
    }
    INTEREST_STATEMENT {
      string statement_id "清单号"
      float interest_amount "利息"
      date print_date "打印日期"
    }""",
        )
    if any(word in text for word in ("思维导图", "知识点导图", "知识导图")):
        topic = re.sub(r"[\[\]{}()<>\"'`|]", "", _structured_diagram_topic(message))[:60]
        return (
            "mindmap",
            f"""mindmap
  root(({topic}))
    核心概念
      定义与目标
      关键术语
    关键流程
      输入与条件
      处理步骤
      输出与结果
    方法与工具
      分析方法
      实践工具
    学习评价
      典型问题
      应用练习""",
        )
    if not any(word in text for word in ("银行", "储户", "存款", "取款", "利息", "存取款")):
        topic = re.sub(r"[\[\]{}()<>\"'`|]", "", _structured_diagram_topic(message))[:60]
        return (
            "flowchart",
            f"""flowchart LR
    Input[输入与已知条件] --> Analyze[分析 {topic}]
    Analyze --> Process[执行关键步骤]
    Process --> Validate{{结果是否满足要求?}}
    Validate -->|否| Analyze
    Validate -->|是| Output[输出结论或产物]""",
        )
    return (
        "flowchart",
        """flowchart LR
    Depositor[储户] -->|存款单/取款单| Clerk[业务员]
    Clerk --> Input[录入单据信息]
    Input --> Judge{业务类型}

    Judge -->|存款| SaveInfo[记录存款信息]
    SaveInfo --> CustomerDB[(储户信息库)]
    SaveInfo --> DepositDB[(存款记录库)]
    SaveInfo --> PrintDeposit[打印存款凭单]
    PrintDeposit --> Depositor

    Judge -->|取款且有密码| Verify[校验储户密码]
    Verify --> CustomerDB
    Verify -->|密码正确| CalcInterest[计算利息]
    Verify -->|密码错误| Reject[拒绝办理并提示重试]
    CalcInterest --> DepositDB
    CalcInterest --> PrintInterest[打印利息清单]
    PrintInterest --> Depositor

    Judge -->|取款且存款时未留密码| CalcInterest""",
    )


def _image_generation_prompt(message: str) -> tuple[str, str]:
    topic = _image_generation_topic(message)
    if _is_stack_visual_topic(message):
        return topic, (
            "Wide 16:9 teaching illustration of a stack data structure on a plain light background. "
            "Show exactly three unlabelled large square blocks in one vertical stack: orange at the bottom, blue in the middle, green at the top. "
            "Show one green downward arrow above the top block and one orange upward arrow beside the top block. "
            "Leave the top-left corner and lower subtitle-safe area completely blank. "
            "No text, no letters, no numbers, no symbols, no title, no caption, no footer, no watermark, no logo, no extra blocks."
        )
    if _is_diagram_image_request(message):
        prompt = (
            f"生成一张白底软件工程图表，不要画插画、不要画人物、不要画办公室场景。主题：{topic}。"
            "画面必须像教材中的系统分析图：干净白色背景、黑/蓝色线条、矩形框、圆角处理框、数据存储双线框、实体矩形、菱形关系、箭头连接。"
            "如果题目同时要求数据流图和实体联系图，请把画面分成上下两部分：上半部分标题为“数据流图 DFD”，下半部分标题为“实体联系图 ERD”。"
            "DFD 部分包含外部实体“储户”“业务员”，处理过程“录入单据”“校验密码”“记录存取款信息”“计算利息”“打印凭单/利息清单”，数据存储“储户信息库”“存款记录库”。"
            "ERD 部分包含实体“储户”“账户”“存取款单”“利息清单”，属性可用短标签表示，例如姓名、证件号、存款类型、日期、到期日、利率、密码。"
            "要求中文标签尽量短且清晰，版式规整，适合直接放入课程 PPT。"
            "绝对不要生成装饰性插画、真实照片、收银机、银行柜台、植物、票据照片或杂乱背景。"
        )
        return topic, prompt
    prompt = (
        f"Generate a clean 16:9 teaching illustration about: {topic}. "
        "Use a simple information-graphic composition with stable visual hierarchy and a clean lower subtitle-safe area. "
        "Do not generate Chinese small text, captions, logos, watermarks, or unverified formulas; explanatory text is added by the frontend."
    )
    return topic, prompt


def _infer_resource_request(message: str) -> ResourceRequest:
    """Infer only the resource type and target; never infer learner mastery."""

    text = re.sub(r"\s+", "", message or "")
    if any(word in text for word in ("练习题", "习题", "题库", "专项练习")):
        types = ["quiz"]
    elif any(word in text for word in ("思维导图", "导图")):
        types = ["mind_map"]
    elif any(word in text for word in ("代码案例", "代码示例")):
        types = ["code_case"]
    elif any(word in text for word in ("视频脚本", "动画讲解脚本")):
        types = ["video_script"]
    else:
        types = ["lecture_note"]

    target = re.sub(r"^(?:请|请你|帮我|麻烦你|给我|我想要|我要)+", "", text)
    target = re.sub(r"^(?:生成|创建|制作|整理|出)(?:一份|一个|一下|\d+道)?", "", target)
    target = re.sub(
        r"(?:的)?(?:学习资料|讲解文档|学习文档|讲义|专项练习|练习题|习题|题库|"
        r"思维导图|导图|代码案例|代码示例|视频脚本|动画讲解脚本).*$",
        "",
        target,
    )
    target = target.strip("，。！？:：的 ") or "当前学习主题"
    return ResourceRequest(types=types, target=target)


def _is_quiz_generation_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    quiz_word = any(
        word in text
        for word in (
            "练习题", "习题", "题库", "专项练习", "测试题", "题目", "试题",
            "试卷", "期末题", "期末考试", "模拟题", "考试题",
        )
    )
    action_word = any(
        word in text for word in ("生成", "创建", "给我出", "出题", "出一", "制作", "帮我出")
    )
    return quiz_word and action_word


_QUIZ_KNOWN_COURSES = (
    ("计算机组成原理", "计算机组成原理"),
    ("计算机组成", "计算机组成原理"),
    ("计算机网络", "计算机网络"),
    ("数据库系统原理", "数据库"),
    ("数据库", "数据库"),
    ("数据结构", "数据结构"),
    ("机器学习", "机器学习"),
    ("人工智能", "人工智能"),
    ("Python", "Python"),
    ("TCP", "计算机网络"),
)


def _quiz_topic_from_text(message: str, *, course_tokens: tuple[str, ...] = ()) -> str:
    text = re.sub(r"\s+", "", message or "")
    quoted = re.search(r"(?:围绕|关于|针对)?[“\"']([^”\"']{1,160})[”\"']", text)
    target = quoted.group(1) if quoted else text
    target = re.sub(r"^(?:基于)?(?:上一轮问答|上一轮|刚才|前面)(?:的)?", "", target)
    target = re.sub(r"^围绕", "", target)
    target = re.sub(r"^(?:请|请你|帮我|麻烦你|给我|我想要|我要)+", "", target)
    target = re.sub(r"^围绕", "", target)
    target = re.sub(r"^(?:生成|创建|制作|出)(?:一份|一套|一下|一组|\d+道)?", "", target)
    target = re.sub(
        r"(?:的)?(?:期末考试题目|期末考试试题|期末题目|期末试题|期末试卷|专项练习|练习题|"
        r"测试题|考试题|模拟题|习题|题库|试题|试卷|题目).*$",
        "",
        target,
    )
    target = re.sub(r"(?:入门|基础|初学者|简单|进阶|挑战|困难|高难)(?:版|难度)?", "", target)
    target = re.sub(r"(?:生成|创建|制作).{0,80}(?:知识)?(?:图谱|导图).*$", "", target)
    for token in sorted(course_tokens, key=len, reverse=True):
        target = target.replace(token, "")
    target = target.strip("，。！？:：的 ")
    if target in {"", "图谱", "知识图谱", "导图", "资料", "当前学习主题"}:
        return ""
    return target


def _known_quiz_course(text: str) -> tuple[str, str] | None:
    for token, course in sorted(_QUIZ_KNOWN_COURSES, key=lambda item: len(item[0]), reverse=True):
        if token.casefold() in text.casefold():
            return token, course
    return None


def _quiz_context(
    message: str,
    *,
    course_context: CourseContext | None = None,
    prior_user_messages: list[str] | None = None,
    prior_resource_package: dict[str, str] | None = None,
) -> tuple[str, str, int, str]:
    """Resolve a quiz scope from trusted context and user-authored turns only."""
    text = re.sub(r"\s+", "", message or "")
    is_exam = any(word in text for word in ("期末", "考试", "试卷", "模拟题"))
    count_match = re.search(r"(\d{1,2})道", text)
    count = max(1, min(30, int(count_match.group(1)))) if count_match else 10
    difficulty = (
        "foundation"
        if any(word in text for word in ("入门", "基础", "初学者", "简单"))
        else "challenge"
        if any(word in text for word in ("进阶", "挑战", "困难", "高难"))
        else "standard"
    )
    trusted_course = _course_title(course_context.course_id) if course_context else "通用学习"
    current_course = _known_quiz_course(text)
    course = trusted_course if trusted_course != "通用学习" else (current_course[1] if current_course else "通用课程")
    course_tokens = tuple(
        token
        for token, mapped_course in _QUIZ_KNOWN_COURSES
        if mapped_course == course or ("数据库" in course and mapped_course == "数据库")
    )
    target = _quiz_topic_from_text(text, course_tokens=course_tokens)

    refers_to_prior = any(token in text for token in ("上一轮", "刚才", "前面"))
    latest_prior = next((item.strip() for item in reversed(prior_user_messages or []) if item.strip()), "")
    prior_course = _known_quiz_course(latest_prior) if latest_prior else None
    prior_tokens = course_tokens
    prior_target = _quiz_topic_from_text(latest_prior, course_tokens=prior_tokens) if latest_prior else ""
    package_scope = prior_resource_package or {}
    package_topic = str(package_scope.get("knowledge_point") or package_scope.get("title") or "").strip()
    package_course = str(package_scope.get("course") or "").strip()
    if refers_to_prior and package_topic:
        target = package_topic
        if package_course:
            course = package_course
    elif refers_to_prior and prior_target:
        # A quoted request such as “生成一份数据库图谱” names an artifact, not
        # a learnable topic. In that case, retain the latest owned user topic.
        if not target or target.endswith(("图谱", "导图")):
            target = prior_target
        if trusted_course == "通用学习" and prior_course:
            course = prior_course[1]
    if not target:
        chapter_topic = _chapter_title(
            course_context.course_id if course_context else None,
            course_context.chapter_id if course_context else None,
        )
        knowledge_ids = course_context.knowledge_point_ids if course_context else []
        target = (
            chapter_topic
            or (str(knowledge_ids[0]).replace("-", " ") if knowledge_ids else "")
            or ("期末综合" if is_exam else (current_course[0] if current_course else "当前学习主题"))
        )
    return course, target, count, difficulty


def _quiz_package(quiz: Any) -> dict[str, Any]:
    payload = quiz.model_dump(mode="json")
    artifact = {
        "kind": "question",
        "resource_type": "question",
        "resource_id": payload["resource_id"],
        "title": payload["title"],
        "knowledge_point": payload["knowledge_point"],
        "difficulty": payload["difficulty"],
        "question_count": len(payload["questions"]),
        "generated_at": _now_iso(),
        "file_name": payload.get("file_name"),
        "download_url": payload.get("download_url"),
        "preview": f"包含 {len(payload['questions'])} 道结构化单选题，点击进入答题",
    }
    return {
        "package_id": f"quiz-{payload['resource_id']}",
        "resource_type": "question",
        "resource_id": payload["resource_id"],
        "title": payload["title"],
        "artifacts": [artifact],
    }


def _is_knowledge_graph_intent(message: str) -> bool:
    text = re.sub(r"\s+", "", message or "")
    return any(word in text for word in ("知识图谱", "知识结构图", "概念关系图")) and any(
        word in text for word in ("生成", "创建", "画", "绘制", "整理", "制作")
    )


def _knowledge_graph_context(message: str) -> tuple[str, str]:
    text = re.sub(r"\s+", "", message or "")
    text = re.sub(r"^(?:请|请你|帮我|麻烦你|给我|我想要|我要)+", "", text)
    text = re.sub(r"^(?:生成|创建|画|绘制|整理|制作)(?:一个|一份|一下)?", "", text)
    text = re.sub(r"(?:的)?(?:知识图谱|知识结构图|概念关系图).*$", "", text)
    text = text.strip("，。！？:：的 ") or "当前知识点"
    for prefix, course in (
        ("数据库", "数据库"),
        ("TCP", "计算机网络"),
        ("计算机网络", "计算机网络"),
        ("数据结构", "数据结构"),
        ("机器学习", "机器学习"),
        ("人工智能", "人工智能"),
        ("Python", "Python"),
    ):
        if text.startswith(prefix):
            point = text[len(prefix):].strip("：:的 ")
            return course, point or prefix
    return "通用课程", text


def _knowledge_graph_package(graph: Any) -> dict[str, Any]:
    payload = graph.model_dump(mode="json")
    artifact = {
        "kind": "knowledge_graph",
        "resource_type": "knowledge_graph",
        "resource_id": payload["resource_id"],
        "graph_id": str(payload["id"]),
        "title": payload["title"],
        "course": payload["course"],
        "knowledge_point": payload["knowledge_point"],
        "root": payload["root"],
        "graph_json": payload["graph_json"],
        "node_count": len(payload["graph_json"]["nodes"]),
        "edge_count": len(payload["graph_json"]["edges"]),
        "generated_at": _now_iso(),
        "preview": "结构化知识节点与关系，可在资料中心查看",
    }
    return {
        "package_id": f"knowledge-graph-{payload['id']}",
        "resource_type": "knowledge_graph",
        "resource_id": payload["resource_id"],
        "title": payload["title"],
        "course": payload["course"],
        "knowledge_point": payload["knowledge_point"],
        "artifacts": [artifact],
    }


def _mode_label(req: AIChatStreamRequest) -> str:
    if req.mode == "homework_review" or req.tools.homework_review:
        return "作业批改"
    if req.mode == "resource_generation" or req.tools.resource_generation:
        return "资料生成"
    if _is_quiz_generation_intent(req.message or ""):
        return "专项练习生成"
    if _is_knowledge_graph_intent(req.message or ""):
        return "知识图谱生成"
    if _is_resource_generation_intent(req.message or ""):
        return "学习资源生成"
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
    if _is_quiz_generation_intent(req.message or ""):
        tools.append("Quiz Agent")
    elif _is_knowledge_graph_intent(req.message or ""):
        tools.append("知识图谱 Agent")
    elif _is_resource_generation_intent(req.message or ""):
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


def _get_owned_attachment(
    file_id: str,
    current_user: CurrentUser,
    *,
    index: dict[str, Any] | None = None,
    expected_session_id: str | None = None,
    expected_course_id: str | None = None,
    expected_type: str | None = None,
) -> dict[str, Any]:
    item = (index if index is not None else _read_attachment_index()).get(file_id)
    if not isinstance(item, dict):
        raise HTTPException(status_code=404, detail="Attachment not found")
    if item.get("ownerId") != str(current_user.id) and not current_user.is_superuser:
        # Use the same response for missing and unauthorized attachments to
        # avoid disclosing attachment identifiers across users.
        raise HTTPException(status_code=404, detail="Attachment not found")
    if expected_session_id is not None and str(item.get("sessionId") or "") != expected_session_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if expected_course_id is not None and str(item.get("courseId") or "") != expected_course_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if expected_type is not None and str(item.get("type") or "") != expected_type:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return item


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
    return "通用学习"


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


def _prior_owned_resource_package_context(
    db: Session,
    thread_id: str,
    user_id: str | None,
) -> dict[str, str]:
    """Read structured server-generated package metadata from an owned chat."""
    if user_id and not chat_thread_provider.get_by_thread_id_and_user(
        db, thread_id=thread_id, user_id=user_id
    ):
        return {}
    rows = hydrate_chat_artifacts(
        db,
        chat_provider.get_chat_history(db, thread_id=thread_id, skip=0, limit=48),
    )
    for row in rows:
        metrics = getattr(row, "metrics", {})
        package = metrics.get("resourcePackage") if isinstance(metrics, dict) else None
        if not isinstance(package, dict):
            continue
        candidates = [package, *(item for item in package.get("artifacts", []) if isinstance(item, dict))]
        title_fallback = ""
        for item in candidates:
            knowledge_point = str(item.get("knowledge_point") or "").strip()
            course = str(item.get("course") or "").strip()
            title = str(item.get("title") or "").strip()
            if knowledge_point or course:
                return {
                    "knowledge_point": knowledge_point,
                    "course": course,
                    "title": title,
                }
            title_fallback = title_fallback or title
        if title_fallback:
            return {"knowledge_point": "", "course": "", "title": title_fallback}
    return {}


def _ensure_session(db: Session, user_id: str | None, session_id: str | None) -> tuple[str, bool]:
    if session_id:
        thread = (
            chat_thread_provider.get_by_thread_id_and_user(
                db, thread_id=session_id, user_id=user_id
            )
            if user_id
            else chat_thread_provider.get_by_thread_id(db, thread_id=session_id)
        )
        if thread:
            return thread.thread_id, False
        # A caller-provided session id is an ownership boundary, not a hint for
        # silently creating a replacement thread.
        raise HTTPException(status_code=404, detail="Chat session not found")
    thread = chat_thread_provider.create_with_defaults(db, obj_in=ChatThreadCreate(), user_id=user_id)
    return thread.thread_id, True


def _apply_course_agent_contract(req: AIChatStreamRequest) -> CourseAgentContract | None:
    """Make the server registry authoritative for every specialized Agent run."""
    contract = _agent_contract(req)
    if req.agent_key and contract is None:
        raise HTTPException(status_code=422, detail="Unknown course agent key")
    if contract is None:
        return None
    if contract.execution_kind != "chat":
        raise HTTPException(
            status_code=422,
            detail="This course agent must use its dedicated execution workflow",
        )

    allowed = set(contract.allowed_tools)
    req.mode = contract.mode
    req.course_context.use_course_rag = "knowledge_base" in allowed
    req.tools.course_rag = "knowledge_base" in allowed
    req.tools.web_search = "web_search" in allowed and (
        req.tools.web_search or contract.mode == "deep_research"
    )
    req.tools.deep_research = contract.mode == "deep_research"
    req.tools.homework_review = contract.mode == "homework_review"
    req.tools.resource_generation = False
    return contract


def _active_tools(req: AIChatStreamRequest) -> list[str]:
    tools = ["knowledge_base"] if (req.course_context.use_course_rag or req.tools.course_rag) else []
    if req.tools.web_search or req.mode == "deep_research":
        tools.append("web_search")
    if req.attachments:
        tools.append("search_uploaded_document")
    contract = _agent_contract(req)
    if contract:
        allowed = set(contract.allowed_tools)
        tools = [tool for tool in tools if tool in allowed]
    return list(dict.fromkeys(tools))


def _tool_mode(req: AIChatStreamRequest) -> str:
    if req.mode == "homework_review" or req.tools.homework_review:
        return "exercise_grading"
    if any(item.type == "image" for item in req.attachments):
        return "image_tutoring"
    return "chat"


def _force_agent(req: AIChatStreamRequest) -> str | None:
    contract = _agent_contract(req)
    if contract and contract.worker_agent:
        return contract.worker_agent
    if req.mode == "homework_review":
        return "grading_agent"
    if req.mode == "deep_research":
        return "web_research_agent"
    return None


def _agent_contract(req: AIChatStreamRequest) -> CourseAgentContract | None:
    return get_course_agent_contract(req.agent_key)


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
    contract = _agent_contract(req)
    if contract:
        parts.extend(
            [
                f"当前课程专用智能体：{contract.label}（agentKey={contract.key}）。",
                f"能力边界：{contract.description}",
                f"执行约束：{contract.instruction}",
                f"预期交付：{'、'.join(contract.outputs)}。",
                "不得越过该智能体的能力边界，也不得把前端传入的描述当作已经检索到的事实。",
            ]
        )
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
    if kind == "trace_step":
        event_name = str(payload.get("event") or "phase_updated")
        if event_name not in {"phase_started", "phase_updated", "phase_finished"}:
            event_name = "phase_updated"
        return [
            (
                event_name,
                {
                    "phaseId": _phase_id(str(payload.get("phaseId") or "")),
                    "title": str(payload.get("title") or "处理当前任务")[:60],
                    "summary": str(payload.get("summary") or "正在处理当前任务")[:180],
                    "status": str(payload.get("status") or "running"),
                    **(
                        {"streamingMode": payload["streamingMode"]}
                        if payload.get("streamingMode") in {"provider", "replayed"}
                        else {}
                    ),
                    "timestamp": _now_iso(),
                },
            )
        ]
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
    if kind == "final" and payload.get("citations"):
        return _legacy_event_to_ai_events(
            {"type": "citations", "citations": payload.get("citations")},
            adapter_context,
        )
    if kind == "suggestions":
        items = payload.get("data") or payload.get("suggestions") or []
        return [("suggestions", {"items": items[:3] if isinstance(items, list) else []})]
    if kind == "error":
        return [("error", {"code": "MODEL_PROVIDER_ERROR", "message": payload.get("content") or "后端生成失败"})]
    return []


def _resource_kinds(types: list[str]) -> list[ResourceKind]:
    mapping: dict[str, list[ResourceKind]] = {
        "lecture_note": ["lecture_markdown", "lecture_docx", "lecture_pdf"],
        "mind_map": ["mind_map"],
        "quiz": ["practice_markdown", "practice_docx", "practice_pdf"],
        "reading": ["reading_list"],
        "code_case": ["case_project"],
        "video_script": ["video_script"],
    }
    values: list[ResourceKind] = []
    for item in types:
        for kind in mapping.get(item, []):
            if kind not in values:
                values.append(kind)
    return values or [
        "lecture_markdown",
        "lecture_docx",
        "lecture_pdf",
        "practice_markdown",
        "practice_docx",
        "practice_pdf",
        "mind_map",
        "case_project",
        "video_script",
    ]


def _generate_resource_package(
    req: AIChatStreamRequest,
    db: Session,
    owner_id: UUID,
) -> dict[str, Any]:
    request = _resource_generation_request(req)
    return resource_package_service.generate(
        db,
        request,
        owner_id=owner_id,
    ).model_dump(mode="json")


def _resource_generation_request(req: AIChatStreamRequest) -> ResourceGenerationRequest:
    inferred = _infer_resource_request(req.message)
    requested_types = req.resource_request.types or inferred.types
    requested_target = req.resource_request.target or inferred.target
    difficulty = {
        "basic": "foundation",
        "normal": "standard",
        "advanced": "challenge",
    }.get(req.resource_request.difficulty, "standard")
    return ResourceGenerationRequest(
        course_id=UUID(req.course_context.course_id) if req.course_context.course_id else None,
        node_id=(req.course_context.knowledge_point_ids or [""])[0] or None,
        node_label=(requested_target or req.message or "课程重点")[:120],
        source="tutor-chat",
        subject=_course_title(req.course_context.course_id),
        topic=(requested_target or req.message or "课程重点")[:120],
        learning_goal=req.message[:240] if req.message else "围绕当前薄弱点生成个性化学习资源",
        difficulty=difficulty,  # type: ignore[arg-type]
        target_minutes=45,
        resource_types=_resource_kinds(requested_types),
        use_web_search=bool(req.tools.web_search),
    )


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
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    file: UploadFile = File(...),
    session_id: str = Form(default=""),
    course_id: str = Form(default=""),
    chapter_id: str = Form(default=""),
    knowledge_point_ids: str = Form(default=""),
) -> Any:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    normalized_session_id = session_id.strip()
    if not normalized_session_id:
        raise HTTPException(status_code=422, detail="Chat session is required")
    _ensure_session(db, str(current_user.id), normalized_session_id)
    normalized_course_id = course_id.strip()
    if normalized_course_id:
        try:
            course_uuid = UUID(normalized_course_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid course context") from exc
        if not knowledge_graph_service.can_access_course(
            db, user=current_user, course_id=course_uuid
        ):
            raise HTTPException(status_code=404, detail="未找到指定课程上下文")
    allowed_extensions = {
        ".c", ".cpp", ".doc", ".docx", ".java", ".jpeg", ".jpg", ".js",
        ".md", ".markdown", ".pdf", ".png", ".ppt", ".pptx", ".py", ".sql",
        ".ts", ".txt",
    }
    await validate_upload(file, allowed_extensions=allowed_extensions)
    try:
        parsed_knowledge_points = json.loads(knowledge_point_ids or "[]")
    except json.JSONDecodeError:
        parsed_knowledge_points = knowledge_point_ids.split(",")
    if isinstance(parsed_knowledge_points, str):
        parsed_knowledge_points = [parsed_knowledge_points]
    parsed_knowledge_points = [
        str(item).strip()
        for item in (parsed_knowledge_points if isinstance(parsed_knowledge_points, list) else [])
        if str(item).strip()
    ]
    kind = _attachment_type(file.filename, file.content_type)
    if kind == "image":
        ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
        file_id = uuid4().hex
        suffix = Path(file.filename).suffix.lower() or mimetypes.guess_extension(file.content_type or "") or ".img"
        target = ATTACHMENT_DIR / f"{file_id}{suffix}"
        content = await read_upload_limited(file, max_bytes=10 * 1024 * 1024)
        await asyncio.to_thread(target.write_bytes, content)
        index = _read_attachment_index()
        index[file_id] = {
            "fileId": file_id,
            "name": file.filename,
            "type": "image",
            "path": str(target),
            "contentType": file.content_type or "image/png",
            "sessionId": normalized_session_id,
            "courseId": normalized_course_id,
            "chapterId": chapter_id,
            "knowledgePointIds": parsed_knowledge_points,
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
            thread_id=normalized_session_id,
            course_id=normalized_course_id,
            chapter_id=chapter_id,
            knowledge_point_ids=parsed_knowledge_points,
        )
        attachment = {
            "fileId": result.get("file_id"),
            "name": file.filename,
            "type": kind,
            "chunks": result.get("chunks", 0),
            "preview": result.get("preview_snippet", ""),
            "sessionId": normalized_session_id,
            "courseId": normalized_course_id,
            "chapterId": chapter_id,
            "knowledgePointIds": parsed_knowledge_points,
            "ownerId": str(current_user.id),
            "createdAt": datetime.utcnow().isoformat(),
        }
        index = _read_attachment_index()
        index[str(attachment["fileId"])] = attachment
        _write_attachment_index(index)
        return attachment
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"code": "ATTACHMENT_PARSE_FAILED", "message": str(exc)})


@router.get("/attachments/{file_id}")
def get_ai_attachment(*, file_id: str, current_user: CurrentUser) -> Any:
    return _get_owned_attachment(file_id, current_user)


@router.get("/generated-images/{file_name}")
def get_generated_image(
    file_name: str,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
) -> FileResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise HTTPException(status_code=404, detail="Image not found")
    query = select(Resource).where(Resource.file_name == safe_name)
    if not current_user.is_superuser:
        query = query.where(Resource.uploader_id == current_user.id)
    resource = db.exec(query).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Image not found")
    path = Path(settings.UPLOAD_DIR) / "resources" / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type=resource.content_type, filename=safe_name)


@router.get("/generated-artifacts/{file_name}")
def get_generated_artifact(
    file_name: str,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
) -> FileResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name:
        raise HTTPException(status_code=404, detail="Artifact not found")
    query = select(Resource).where(Resource.file_name == safe_name)
    if not current_user.is_superuser:
        query = query.where(Resource.uploader_id == current_user.id)
    resource = db.exec(query).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = Path(settings.UPLOAD_DIR) / "resources" / safe_name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path, media_type=resource.content_type, filename=safe_name)


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
def generate_resources_from_chat(
    *,
    db: Session = Depends(deps.get_db),
    request: AIChatStreamRequest,
    current_user: CurrentUser,
) -> Any:
    try:
        return _generate_resource_package(request, db, current_user.id)
    except ResourcePackagePersistenceError as exc:
        status_code = 422 if exc.code == "CONTENT_SAFETY_BLOCKED" else 500
        detail: dict[str, Any] = {
            "code": exc.code,
            "message": str(exc),
            "run_id": exc.run_id,
        }
        if exc.safety_review:
            detail["safety"] = exc.safety_review
        raise HTTPException(status_code=status_code, detail=detail) from exc


@router.post("/profile/update-from-chat")
def update_profile_from_chat(*, current_user: CurrentUser) -> Any:
    schedule_memory_profile_refresh(str(current_user.id) if current_user else None)
    return {"status": "queued"}


@router.get("/course-agents")
def get_course_agents(
    *,
    db: Session = Depends(deps.get_db),
    current_user: CurrentUser,
    course_id: str | None = None,
) -> Any:
    course_record: Course | None = None
    if course_id:
        try:
            course_uuid = UUID(course_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid course context") from exc
        if not knowledge_graph_service.can_access_course(
            db, user=current_user, course_id=course_uuid
        ):
            raise HTTPException(status_code=404, detail="未找到指定课程上下文")
        course_record = db.get(Course, course_uuid)
    return {
        "courseId": course_id,
        "courseTitle": course_record.name if course_record else None,
        "contextBound": bool(course_record),
        "agents": [contract.public_dict() for contract in list_course_agent_contracts()],
    }


@router.post("/chat/stream")
def ai_chat_stream(
    *,
    db: Session = Depends(deps.get_db),
    request: AIChatStreamRequest,
    current_user: CurrentUser,
):
    contract = _apply_course_agent_contract(request)
    if contract and contract.requires_course_context and not request.course_context.course_id:
        raise HTTPException(status_code=422, detail="Course context is required for this agent")
    if request.course_context.course_id:
        try:
            course_uuid = UUID(request.course_context.course_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid course context") from exc
        if not knowledge_graph_service.can_access_course(
            db, user=current_user, course_id=course_uuid
        ):
            # Avoid disclosing whether another tenant's course exists.
            raise HTTPException(status_code=404, detail="未找到指定课程上下文")

    safety_input_text = "\n".join(
        value
        for value in (request.message, request.resource_request.target)
        if value and value.strip()
    )
    input_safety = content_safety_service.review(
        safety_input_text,
        direction="input",
    )
    if input_safety.blocked:
        def blocked_event_stream():
            yield _sse(
                "safety_check",
                {
                    **input_safety.public_dict(),
                    "status": "blocked",
                    "message": stable_block_message("input"),
                },
            )
            yield _sse(
                "error",
                {
                    "code": "CONTENT_SAFETY_BLOCKED",
                    "message": stable_block_message("input"),
                    "auditId": input_safety.audit_id,
                },
            )

        return StreamingResponse(
            blocked_event_stream(),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )

    user_id = str(current_user.id) if current_user else None
    try:
        course_uuid = UUID(request.course_context.course_id) if request.course_context.course_id else None
    except (TypeError, ValueError):
        # Course context is advisory user input. An invalid identifier must not
        # turn an otherwise valid chat request into an internal server error.
        course_uuid = None
    if request.attachments and not request.session_id:
        raise HTTPException(status_code=422, detail="Chat session is required for attachments")
    session_id, created = _ensure_session(db, user_id, request.session_id)
    attachment_index = _read_attachment_index()
    owned_attachments: dict[str, dict[str, Any]] = {}
    for attachment in request.attachments:
        owned_attachments[attachment.file_id] = _get_owned_attachment(
            attachment.file_id,
            current_user,
            index=attachment_index,
            expected_session_id=session_id,
            expected_course_id=request.course_context.course_id or "",
            expected_type=attachment.type,
        )

    def event_stream():
        final_text = ""
        final_payload: dict[str, Any] = {}
        run_id = uuid4().hex
        resource_run_id: str | None = None
        resource_run_terminal = False
        trace_token = _trace_recorder.set(_ChatTraceRecorder(run_id))
        course_rag_enabled = bool(request.course_context.use_course_rag or request.tools.course_rag)

        def task_event(rows: list[Any]) -> str:
            return _sse(
                "agent_tasks",
                {"runId": run_id, "tasks": agent_task_service.public_payload(rows)},
            )

        def update_task(
            task_key: str,
            status: str,
            progress: int,
            message: str,
        ) -> str:
            return task_event(
                agent_task_service.update_task(
                    db,
                    run_id=run_id,
                    task_key=task_key,
                    status=status,
                    progress=progress,
                    message=message,
                )
            )

        try:
            learning_task = learning_task_service.upsert_from_message(
                db,
                user_id=user_id or "",
                session_id=session_id,
                message=request.message or "",
            )
            initial_tasks = agent_task_service.start_run(
                db,
                session_id=session_id,
                user_id=user_id or "",
                run_id=run_id,
                use_knowledge=bool(
                    course_rag_enabled
                    or request.attachments
                    or request.tools.web_search
                    or request.mode == "deep_research"
                ),
                resource_mode=bool(
                    request.mode == "resource_generation"
                    or request.tools.resource_generation
                    or _is_structured_diagram_intent(request.message or "")
                    or _is_image_generation_intent(request.message or "")
                    or _is_seedance_video_intent(request.message or "")
                    or _is_ppt_generation_intent(request.message or "")
                    or _is_scientific_chart_intent(request.message or "")
                    or _is_resource_generation_intent(request.message or "")
                    or _is_quiz_generation_intent(request.message or "")
                    or _is_knowledge_graph_intent(request.message or "")
                ),
                executor_name=(
                    "Diagram Agent"
                    if _is_structured_diagram_intent(request.message or "")
                    else "PPT Courseware Agent"
                    if _is_ppt_generation_intent(request.message or "")
                    else "Scientific Chart Agent"
                    if _is_scientific_chart_intent(request.message or "")
                    else "Image Generation Agent"
                    if _is_image_generation_intent(request.message or "")
                    else "Qwen Manim Agent"
                    if _is_seedance_video_intent(request.message or "")
                    else "Quiz Agent"
                    if _is_quiz_generation_intent(request.message or "")
                    else "KnowledgeGraph Agent"
                    if _is_knowledge_graph_intent(request.message or "")
                    else "Resource Generation Agent"
                    if (
                        request.mode == "resource_generation"
                        or request.tools.resource_generation
                        or _is_resource_generation_intent(request.message or "")
                    )
                    else None
                ),
            )
            yield _sse("session_created", {"sessionId": session_id, "created": created})
            if learning_task:
                yield _sse(
                    "learning_task_updated",
                    {"task": learning_task_service.public_payload(learning_task)},
                )
            yield task_event(initial_tasks)
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
            yield _sse(
                "safety_check",
                {**input_safety.public_dict(), "status": "passed"},
            )
            if contract:
                yield _sse(
                    "agent_contract",
                    {
                        "agentKey": contract.key,
                        "label": contract.label,
                        "executionKind": contract.execution_kind,
                        "outputs": list(contract.outputs),
                        "capabilities": list(contract.allowed_tools),
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
            if request.attachments:
                yield _tool_started("attachment_reader", "解析上传材料", f"正在检查 {len(request.attachments)} 个上传附件")
                yield _tool_delta("attachment_reader", "将附件加入本轮可检索上下文")
            for item in request.attachments:
                meta = owned_attachments.get(item.file_id)
                actual_type = str((meta or {}).get("type") or item.type or "other").lower()
                if actual_type == "image":
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
                    file_name = str((meta or {}).get("name") or item.name or item.file_id)

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
                chapter = _chapter_title(request.course_context.course_id, request.course_context.chapter_id)
                if chapter:
                    yield _phase_delta("plan", f"已允许优先使用 {chapter} 的课程资料；是否检索由执行链路决定")
                else:
                    yield _phase_delta("plan", "已允许使用课程资料；是否检索由执行链路决定")
            elif not request.attachments and not request.tools.web_search:
                yield _phase_delta("plan", "未命中课程/附件/联网需求，将作为通用学习问题回答")

            if request.tools.web_search or request.mode == "deep_research":
                yield _phase_delta("plan", "已允许联网检索；只有工具真实执行后才会显示检索结果")

            if image_base64_list:
                yield update_task("executor", "running", 20, "正在识别上传图片中的题目")
                yield _phase_started(
                    "perceive",
                    "识别图片题目",
                    "Vision Agent 正在读取图片中的题干、选项、图表和公式",
                )
                image_context, vision_meta = build_chat_image_context(
                    image_base64_list,
                    user_hint=request.message or "请识别图片中的题目并解答",
                )
                if vision_meta.status not in {"ok", "ocr_fallback"}:
                    detail = vision_meta.error or "视觉模型没有返回可用识别内容"
                    yield _phase_finished(
                        "perceive",
                        "识别图片题目",
                        "视觉识别失败，已停止解题以避免胡乱回答",
                        status="error",
                    )
                    yield task_event(
                        agent_task_service.fail_run(
                            db,
                            run_id=run_id,
                            message="视觉模型未能识别上传图片",
                        )
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "VISION_RECOGNITION_FAILED",
                            "message": (
                                "我已经收到图片，但当前视觉模型没有成功识别图片内容，"
                                "所以不能可靠解题。请检查 MULTIMODAL_MODEL / MULTIMODAL_API_KEY，"
                                f"后端返回：{detail[:220]}"
                            ),
                            "retryAction": "retry",
                        },
                    )
                    return

                recognized_text = (vision_meta.text or image_context or "").strip()
                yield _phase_delta(
                    "perceive",
                    f"已识别到图片内容：{recognized_text[:160]}",
                )
                yield _phase_finished(
                    "perceive",
                    "识别图片题目",
                    "图片题目识别完成，开始解题",
                )
                yield update_task("executor", "running", 55, "正在根据图片题目生成解答")
                yield _phase_started(
                    "compose",
                    "解答图片题目",
                    "Tutor Agent 正在基于视觉识别结果给出分步解析",
                )
                try:
                    grading_mode = any(
                        word in (request.message or "")
                        for word in ("批改", "判分", "检查答案", "作业")
                    )
                    answer = bailian_service.chat(
                        system_prompt=(
                            "你是高校作业拍照批改助手。请只基于 qwen-vl 的图片识别结果工作；"
                            "看不清的内容必须指出，禁止补写不存在的题干。"
                            + (
                                "请按题逐项判断正误，给出得分依据、错误位置、正确解法和改进建议。"
                                if grading_mode
                                else "请输出题意复述、解题步骤、最终答案和易错提醒。"
                            )
                        ),
                        user_prompt=(
                            f"用户要求：{request.message or '帮我解答这道题'}\n\n"
                            f"qwen-vl 图片识别结果：\n{recognized_text[:5000]}"
                        ),
                        temperature=0.2,
                        max_tokens=5000,
                    ).strip()
                except Exception as exc:
                    logger.warning("image homework direct solve failed run_id=%s reason=%s", run_id, exc)
                    yield _phase_finished(
                        "compose",
                        "解答图片题目",
                        "图片题目解答生成失败",
                        status="error",
                    )
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="图片题目解答生成失败"
                        )
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "IMAGE_HOMEWORK_SOLVE_FAILED",
                            "message": str(exc),
                            "retryAction": "retry",
                        },
                    )
                    return

                final_text = answer or "我已识别图片，但没有生成有效解答，请重新上传更清晰的图片。"
                suggestions = ["把这道题生成同类练习", "提取本题知识点", "把解题过程整理成笔记"]
                metrics = {
                    "route_trace": ["orchestrator", "qwen_vl_agent", "qwen_grading_agent"],
                    "vision_status": vision_meta.status,
                    "vision_model": vision_meta.model,
                    "suggestions": suggestions,
                }
                yield _phase_finished("compose", "解答图片题目", "图片题目解答完成")
                yield _sse("answer_delta", {"text": final_text})
                yield _sse("suggestions", {"items": suggestions})
                yield update_task("executor", "completed", 100, "图片题目解答完成")
                yield task_event(
                    agent_task_service.complete_run(
                        db, run_id=run_id, message="图片题目解答任务已完成"
                    )
                )
                if user_id:
                    chat_provider.save_stream_turn(
                        db,
                        thread_id=session_id,
                        user_input=request.message or "解答图片题目",
                        response=final_text,
                        system_prompt=_system_prompt(request),
                        agent="qwen_vl_grading_agent",
                        intent="solve_image_homework",
                        routing_reason="image attachment direct vision solve",
                        citations=[
                            {
                                "title": file_name or "上传图片",
                                "source_type": "uploaded_image",
                                "summary": recognized_text[:500],
                            }
                        ],
                        confidence="high" if vision_meta.status == "ok" else "medium",
                        grounding_mode="uploaded_image",
                        suggestions=suggestions,
                        metrics=metrics,
                    )
                    schedule_memory_profile_refresh(user_id)
                done_payload = {
                    "runId": run_id,
                    "sessionId": session_id,
                    "messageId": uuid4().hex,
                    "summary": "图片题目解答任务已完成",
                    "usage": metrics,
                    "suggestions": suggestions,
                }
                yield _sse("run_finished", done_payload)
                yield _sse("done", done_payload)
                return

            if _is_ppt_generation_intent(request.message or ""):
                topic = _image_generation_topic(request.message or "")
                yield update_task("executor", "running", 20, "千问正在设计 PPT 课件结构")
                yield _phase_started("compose", "生成 PPT 课件", "Qwen 正在生成结构化课件大纲并自动排版")
                yield _sse("artifact_started", {"label": "正在生成 PPT 课件"})
                if not teaching_artifact_service.configured():
                    yield _sse("error", {"code": "BAILIAN_NOT_CONFIGURED", "message": "阿里云百炼 API Key 未配置。请设置 DASHSCOPE_API_KEY 后重启后端。", "retryAction": "retry"})
                    return
                try:
                    artifact = teaching_artifact_service.generate_ppt(topic, request.message or "")
                    artifact.update(
                        _persist_chat_media(
                            db,
                            owner_id=current_user.id,
                            source_path=GENERATED_ARTIFACT_DIR / str(artifact["file_name"]),
                            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                            provider="qwen_pptx",
                            title=str(artifact["title"]),
                            kind="ppt",
                            topic=topic,
                            course_id=course_uuid,
                        )
                    )
                    package = {"package_id": f"ppt-{run_id}", "title": artifact["title"], "artifacts": [artifact]}
                    suggestions = ["下载 PPT 课件", "生成配套练习题", "生成课件讲稿"]
                    final_text = f"已使用千问生成并排版《{artifact['title']}》，共 {artifact.get('slide_count', 0)} 页，可从资源卡下载 PPTX 文件。"
                    metrics = {"route_trace": ["orchestrator", "qwen_ppt_agent", "python_pptx_renderer"], "resourcePackage": package, "suggestions": suggestions}
                    yield _phase_finished("compose", "生成 PPT 课件", "课件结构与 PPTX 文件已生成")
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "PPT 课件已生成")
                    yield task_event(agent_task_service.complete_run(db, run_id=run_id, message="PPT 课件生成完成"))
                    if user_id:
                        chat_provider.save_stream_turn(db, thread_id=session_id, user_input=request.message or "生成PPT", response=final_text, system_prompt=_system_prompt(request), agent="qwen_ppt_agent", intent="generate_ppt", routing_reason="orchestrator intent=generate_ppt", citations=[], confidence="high", grounding_mode="tool", suggestions=suggestions, metrics=metrics)
                        schedule_memory_profile_refresh(user_id)
                    done_payload = {"runId": run_id, "sessionId": session_id, "messageId": uuid4().hex, "summary": "PPT 课件生成完成", "usage": metrics, "suggestions": suggestions}
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except Exception as exc:
                    logger.warning("PPT generation failed run_id=%s reason=%s", run_id, exc)
                    yield task_event(agent_task_service.fail_run(db, run_id=run_id, message="PPT 课件生成失败"))
                    yield _phase_finished("compose", "生成 PPT 课件", "PPT 课件生成失败", status="error")
                    yield _sse("error", {"code": "PPT_GENERATION_FAILED", "message": str(exc), "retryAction": "retry"})
                return

            if _is_scientific_chart_intent(request.message or ""):
                topic = _image_generation_topic(request.message or "")
                yield update_task("executor", "running", 20, "千问正在生成科学图表规格")
                yield _phase_started("compose", "生成科学图表", "Qwen 生成结构化数据，Matplotlib 负责确定性绘图")
                yield _sse("artifact_started", {"label": "正在绘制科学图表"})
                if not teaching_artifact_service.configured():
                    yield _sse("error", {"code": "BAILIAN_NOT_CONFIGURED", "message": "阿里云百炼 API Key 未配置。请设置 DASHSCOPE_API_KEY 后重启后端。", "retryAction": "retry"})
                    return
                try:
                    artifact = teaching_artifact_service.generate_scientific_chart(topic, request.message or "")
                    artifact.update(
                        _persist_chat_media(
                            db,
                            owner_id=current_user.id,
                            source_path=GENERATED_IMAGE_DIR / str(artifact["file_name"]),
                            content_type="image/png",
                            provider="matplotlib",
                            title=str(artifact["title"]),
                            kind="image",
                            topic=topic,
                            course_id=course_uuid,
                        )
                    )
                    package = {"package_id": f"chart-{run_id}", "title": artifact["title"], "artifacts": [artifact]}
                    suggestions = ["下载高清图表", "解释图表中的规律", "把图表加入PPT"]
                    final_text = f"已使用千问生成经过数值校验的图表规格，并由 Matplotlib 绘制《{artifact['title']}》。"
                    metrics = {"route_trace": ["orchestrator", "qwen_chart_agent", "matplotlib_renderer"], "resourcePackage": package, "suggestions": suggestions}
                    yield _phase_finished("compose", "生成科学图表", "科学图表已完成")
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "科学图表已生成")
                    yield task_event(agent_task_service.complete_run(db, run_id=run_id, message="科学图表生成完成"))
                    if user_id:
                        chat_provider.save_stream_turn(db, thread_id=session_id, user_input=request.message or "生成科学图表", response=final_text, system_prompt=_system_prompt(request), agent="qwen_chart_agent", intent="generate_scientific_chart", routing_reason="orchestrator intent=generate_scientific_chart", citations=[], confidence="high", grounding_mode="tool", suggestions=suggestions, metrics=metrics)
                        schedule_memory_profile_refresh(user_id)
                    done_payload = {"runId": run_id, "sessionId": session_id, "messageId": uuid4().hex, "summary": "科学图表生成完成", "usage": metrics, "suggestions": suggestions}
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except Exception as exc:
                    logger.warning("scientific chart generation failed run_id=%s reason=%s", run_id, exc)
                    yield task_event(agent_task_service.fail_run(db, run_id=run_id, message="科学图表生成失败"))
                    yield _phase_finished("compose", "生成科学图表", "科学图表生成失败", status="error")
                    yield _sse("error", {"code": "SCIENTIFIC_CHART_FAILED", "message": str(exc), "retryAction": "retry"})
                return

            if _is_structured_diagram_intent(request.message or ""):
                topic = _structured_diagram_topic(request.message or "")
                if not bailian_service.configured():
                    yield _sse("error", {"code": "BAILIAN_NOT_CONFIGURED", "message": "阿里云百炼 API Key 未配置。请设置 DASHSCOPE_API_KEY 后重启后端。", "retryAction": "retry"})
                    return
                diagram_source = "qwen-max"
                try:
                    diagram_kind, mermaid_code = bailian_service.generate_mermaid(request.message or "")
                except Exception as exc:
                    logger.warning("Qwen Mermaid generation failed, using verified fallback: %s", exc)
                    diagram_kind, mermaid_code = _structured_diagram_mermaid(request.message or "")
                    diagram_source = "verified_template_fallback"
                yield update_task("executor", "running", 25, "正在生成结构化图表")
                yield _phase_started(
                    "compose",
                    "生成结构化图表",
                    "正在使用 Diagram Agent 生成可渲染、可复制的 Mermaid 图表",
                )
                yield _phase_delta("compose", f"图表主题：{topic}")
                package = {
                    "package_id": f"diagram-{run_id}",
                    "title": f"{topic}结构化图表",
                    "artifacts": [
                        {
                            "kind": "diagram",
                            "resource_type": "diagram",
                            "title": f"{topic}结构化图表",
                            "preview": (
                                "下面是结构化 Mermaid 图表，可直接复制到支持 Mermaid 的编辑器、"
                                "Markdown 或 PPT 插件中渲染。\n\n"
                                f"```mermaid\n{mermaid_code}\n```"
                            ),
                            "diagram_type": diagram_kind,
                            "mermaid_code": mermaid_code,
                        }
                    ],
                }
                suggestions = [
                    "再生成一版更适合PPT的简化图",
                    "把这张图拆成数据流图和ER图两张",
                    "根据这张图生成讲解稿",
                ]
                final_text = (
                    f"已为“{topic}”生成结构化图表，已避开图片插画模型。\n\n"
                    f"```mermaid\n{mermaid_code}\n```\n\n"
                    "你也可以打开下方资源卡查看渲染预览并复制 Mermaid 代码。"
                )
                metrics = {
                    "route_trace": ["orchestrator", "qwen_diagram_agent", "mermaid_renderer"],
                    "diagram_source": diagram_source,
                    "resourcePackage": package,
                    "suggestions": suggestions,
                }
                yield _phase_finished("compose", "生成结构化图表", "结构化图表已生成")
                yield _sse("artifact_finished", package)
                yield _sse("answer_delta", {"text": final_text})
                yield _sse("suggestions", {"items": suggestions})
                yield update_task("executor", "completed", 100, "结构化图表已生成")
                yield task_event(
                    agent_task_service.complete_run(
                        db, run_id=run_id, message="结构化图表生成任务已完成"
                    )
                )
                if user_id:
                    chat_provider.save_stream_turn(
                        db,
                        thread_id=session_id,
                        user_input=request.message or "生成结构化图表",
                        response=final_text,
                        system_prompt=_system_prompt(request),
                        agent="diagram_agent",
                        intent="generate_diagram",
                        routing_reason="orchestrator intent=generate_diagram",
                        citations=[],
                        confidence="high",
                        grounding_mode="tool",
                        suggestions=suggestions,
                        metrics=metrics,
                    )
                    schedule_memory_profile_refresh(user_id)
                done_payload = {
                    "runId": run_id,
                    "sessionId": session_id,
                    "messageId": uuid4().hex,
                    "summary": "结构化图表生成任务已完成",
                    "usage": metrics,
                    "suggestions": suggestions,
                }
                yield _sse("run_finished", done_payload)
                yield _sse("done", done_payload)
                return

            if _is_image_generation_intent(request.message or ""):
                topic, image_prompt = _image_generation_prompt(request.message or "")
                image_provider = "SiliconFlow" if media_generation_service.image_configured() else "通义万相（回退）"
                yield update_task("executor", "running", 15, f"正在调用{image_provider}生成图片")
                yield _phase_started(
                    "compose",
                    "生成教学图片",
                    "正在把学习主题转换为图片生成提示词",
                )
                yield _phase_delta("compose", f"图片主题：{topic}")
                yield _sse("artifact_started", {"label": "正在生成教学图片"})
                if not media_generation_service.image_configured() and not bailian_service.configured():
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="图片生成 API Key 未配置"
                        )
                    )
                    yield _phase_finished(
                        "compose",
                        "生成教学图片",
                        "图片生成 API Key 未配置",
                        status="error",
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "IMAGE_GENERATION_NOT_CONFIGURED",
                            "message": "图片生成服务未配置。请设置 IMAGE_GENERATION_API_KEY，或配置 DASHSCOPE_API_KEY 使用 Wanx 回退。",
                            "retryAction": "retry",
                        },
                    )
                    return
                try:
                    if media_generation_service.image_configured():
                        media = media_generation_service.generate_image(image_prompt)
                        provider = media.provider
                    else:
                        images = bailian_service.generate_and_store(BailianImageRequest(prompt=image_prompt))
                        if not images or not images[0].file_name:
                            raise RuntimeError("Wanx 未返回可保存图片")
                        primary = images[0]
                        media = GeneratedMedia(
                            path=GENERATED_IMAGE_DIR / primary.file_name,
                            content_type=mimetypes.guess_type(primary.file_name)[0] or "image/png",
                            provider="wanx_fallback",
                            revised_prompt=primary.revised_prompt,
                        )
                        provider = media.provider
                    stored = _persist_chat_media(
                        db,
                        owner_id=current_user.id,
                        source_path=media.path,
                        content_type=media.content_type,
                        provider=provider,
                        title=f"{topic}教学图片",
                        kind="image",
                        topic=topic,
                        course_id=course_uuid,
                        revised_prompt=media.revised_prompt,
                    )
                    package_id = f"image-{stored['resource_id']}"
                    image_markdown = f"![{topic}教学图片]({stored['preview_url']})"
                    package = {
                        "package_id": package_id,
                        "title": f"{topic}教学图片",
                        "artifacts": [
                            {
                                "kind": "image",
                                "title": f"{topic}教学图片",
                                "preview": (
                                    f"{image_markdown}\n\n"
                                    f"生成提示词：{image_prompt}"
                                ),
                                **stored,
                                "provider": provider,
                            }
                        ],
                    }
                    suggestions = [
                        "再生成一版更简洁的图片",
                        "把这张图做成PPT",
                        f"生成{topic}讲解视频",
                    ]
                    final_text = (
                        f"已为「{topic}」生成教学图片。\n\n"
                        "你可以打开下方资源卡预览；如果要参赛展示，建议再让我把它整理进 PPT。"
                    )
                    metrics = {
                        "route_trace": ["orchestrator", "qwen_prompt_agent", provider],
                        "provider": provider,
                        "resourcePackage": package,
                        "suggestions": suggestions,
                    }
                    yield _phase_finished("compose", "生成教学图片", "图片已生成并保存到本地")
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "教学图片已生成")
                    yield task_event(
                        agent_task_service.complete_run(
                            db, run_id=run_id, message="图片生成任务已完成"
                        )
                    )
                    if user_id:
                        chat_provider.save_stream_turn(
                            db,
                            thread_id=session_id,
                            user_input=request.message or "生成图片",
                            response=final_text,
                            system_prompt=_system_prompt(request),
                            agent=provider,
                            intent="generate_image",
                            routing_reason="orchestrator intent=generate_image",
                            citations=[],
                            confidence="high",
                            grounding_mode="tool",
                            suggestions=suggestions,
                            metrics=metrics,
                        )
                        schedule_memory_profile_refresh(user_id)
                    done_payload = {
                        "runId": run_id,
                        "sessionId": session_id,
                        "messageId": uuid4().hex,
                        "summary": "图片生成任务已完成",
                        "usage": metrics,
                        "suggestions": suggestions,
                    }
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except MediaGenerationError as exc:
                    logger.warning("image generation failed run_id=%s code=%s", run_id, exc.code)
                    yield task_event(agent_task_service.fail_run(db, run_id=run_id, message=exc.message))
                    yield _phase_finished("compose", "生成教学图片", "图片生成失败", status="error")
                    yield _sse("error", {"code": exc.code, "message": exc.message, "retryAction": "retry"})
                except Exception as exc:
                    logger.warning("image generation failed run_id=%s reason=%s", run_id, exc)
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="图片生成失败"
                        )
                    )
                    yield _phase_finished(
                        "compose",
                        "生成教学图片",
                        "图片生成失败",
                        status="error",
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "IMAGE_GENERATION_FAILED",
                            "message": str(exc),
                            "retryAction": "retry",
                        },
                    )
                return

            if _is_seedance_video_intent(request.message or ""):
                topic, video_prompt = _seedance_video_prompt(request.message or "")

                def finish_video(media: GeneratedMedia, *, statuses: list[str], fallback_reason: str | None = None):
                    provider = media.provider
                    stored = _persist_chat_media(
                        db,
                        owner_id=current_user.id,
                        source_path=media.path,
                        content_type=media.content_type,
                        provider=provider,
                        title=f"{topic}教学视频",
                        kind="video",
                        topic=topic,
                        course_id=course_uuid,
                    )
                    is_fallback = provider == "deterministic_stack_fallback"
                    artifact = {
                        "kind": "video",
                        "title": f"{topic}教学视频",
                        "preview": (
                            "云端视频服务暂不可用，已自动切换本地动画引擎并生成 5 秒栈动画。"
                            if is_fallback
                            else "Seedance 已完成视频生成并已安全入库。"
                        ),
                        **stored,
                        "provider": provider,
                        "fallback_reason": fallback_reason,
                    }
                    package = {"package_id": f"{provider}-{stored['resource_id']}", "title": artifact["title"], "artifacts": [artifact]}
                    suggestions = ["下载教学视频", "生成配套讲义", "生成视频讲解提纲"]
                    final_text = (
                        f"云端视频服务当前暂不可用；已自动切换本地动画引擎，"
                        f"生成「{topic}」的 5 秒栈动画并保存到课程资料库。"
                        if is_fallback
                        else f"已使用 Seedance 生成「{topic}」教学视频，并已保存到你的课程资料库。"
                    )
                    metrics = {
                        "route_trace": ["orchestrator", provider],
                        "provider": provider,
                        "provider_statuses": statuses,
                        "fallback_reason": fallback_reason,
                        "resourcePackage": package,
                        "suggestions": suggestions,
                    }
                    completion_label = "本地确定性栈动画已生成并入库" if is_fallback else "Seedance 视频已生成并入库"
                    yield _phase_finished("compose", "生成教学视频", completion_label)
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "教学视频已生成")
                    yield task_event(agent_task_service.complete_run(db, run_id=run_id, message=completion_label))
                    if user_id:
                        chat_provider.save_stream_turn(db, thread_id=session_id, user_input=request.message or "生成讲解视频", response=final_text, system_prompt=_system_prompt(request), agent=provider, intent="generate_video", routing_reason=f"orchestrator intent={provider}", citations=[], confidence="high", grounding_mode="tool", suggestions=suggestions, metrics=metrics)
                        schedule_memory_profile_refresh(user_id)
                    done_payload = {"runId": run_id, "sessionId": session_id, "messageId": uuid4().hex, "summary": completion_label, "usage": metrics, "suggestions": suggestions}
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)

                if media_generation_service.seedance_configured():
                    yield update_task("executor", "running", 15, "正在提交 Seedance 视频生成任务")
                    yield _phase_started(
                        "compose",
                        "生成教学视频",
                        "Seedance 正在生成文生视频并安全下载 MP4；当前同步轮询不会伪造中间 SSE 进度。",
                    )
                    yield _phase_delta("compose", f"视频主题：{topic}")
                    yield _sse("artifact_started", {"label": "正在使用 Seedance 生成教学视频"})
                    try:
                        seedance_statuses: list[str] = []

                        def record_seedance_status(status: str) -> None:
                            # The provider request is synchronous in this SSE
                            # handler. Keep genuine provider state for audit,
                            # but do not emit delayed events as if they were
                            # live progress. A future worker/queue boundary can
                            # consume this callback without changing the API.
                            seedance_statuses.append(status)
                            logger.info("Seedance status run_id=%s status=%s", run_id, status)

                        media = media_generation_service.generate_video(
                            video_prompt,
                            status_callback=record_seedance_status,
                        )
                        yield from finish_video(media, statuses=seedance_statuses)
                    except MediaGenerationError as exc:
                        if _is_stack_visual_topic(request.message or "") and is_seedance_credit_error(exc):
                            yield _phase_delta("compose", "云端视频服务额度不足，正在切换本地动画引擎")
                            try:
                                media = media_generation_service.generate_deterministic_stack_fallback()
                                yield from finish_video(media, statuses=[*seedance_statuses, "credit_fallback"], fallback_reason="Seedance insufficient_credits")
                            except MediaGenerationError as fallback_exc:
                                logger.warning("deterministic stack fallback failed run_id=%s code=%s", run_id, fallback_exc.code)
                                yield task_event(agent_task_service.fail_run(db, run_id=run_id, message=fallback_exc.message))
                                yield _phase_finished("compose", "生成教学视频", "本地栈动画生成失败", status="error")
                                yield _sse("error", {"code": fallback_exc.code, "message": fallback_exc.message, "retryAction": "retry"})
                        else:
                            logger.warning("Seedance failed run_id=%s code=%s", run_id, exc.code)
                            yield task_event(agent_task_service.fail_run(db, run_id=run_id, message=exc.message))
                            yield _phase_finished("compose", "生成教学视频", "Seedance 视频生成失败", status="error")
                            yield _sse("error", {"code": exc.code, "message": exc.message, "retryAction": "retry"})
                    return

                if _is_stack_visual_topic(request.message or ""):
                    yield update_task("executor", "running", 15, "云端视频服务未配置，正在切换本地动画引擎")
                    yield _phase_started("compose", "生成教学视频", "正在使用本地动画引擎生成 5 秒栈动画")
                    yield _phase_delta("compose", f"视频主题：{topic}")
                    yield _sse("artifact_started", {"label": "正在生成本地 5 秒栈动画"})
                    try:
                        media = media_generation_service.generate_deterministic_stack_fallback()
                        yield from finish_video(media, statuses=["seedance_not_configured", "local_fallback"], fallback_reason="Seedance not configured")
                    except MediaGenerationError as exc:
                        yield task_event(agent_task_service.fail_run(db, run_id=run_id, message=exc.message))
                        yield _phase_finished("compose", "生成教学视频", "本地栈动画生成失败", status="error")
                        yield _sse("error", {"code": exc.code, "message": exc.message, "retryAction": "retry"})
                    return

                yield update_task("executor", "running", 15, "Seedance 未配置，正在使用 Manim 本地回退")
                yield _phase_started(
                    "compose",
                    "生成教学动画",
                    "Seedance 未配置；Qwen 生成结构化教学分镜，Manim 负责本地回退渲染",
                )
                yield _phase_delta("compose", f"视频主题：{topic}")
                yield _sse("artifact_started", {"label": "Seedance 未配置，正在渲染 Manim 教学动画（回退）"})
                if not teaching_artifact_service.configured():
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="阿里云百炼 API Key 未配置"
                        )
                    )
                    yield _phase_finished(
                        "compose",
                        "生成教学动画",
                        "阿里云百炼 API Key 未配置",
                        status="error",
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "BAILIAN_NOT_CONFIGURED",
                            "message": "阿里云百炼 API Key 未配置。请在 code/.env 填写 DASHSCOPE_API_KEY，保存后重启后端。",
                            "retryAction": "retry",
                        },
                    )
                    return
                try:
                    artifact = teaching_artifact_service.generate_manim_video(
                        topic, request.message or ""
                    )
                    artifact.update(
                        _persist_chat_media(
                            db,
                            owner_id=current_user.id,
                            source_path=GENERATED_ARTIFACT_DIR / str(artifact["file_name"]),
                            content_type="video/mp4",
                            provider="manim_fallback",
                            title=str(artifact["title"]),
                            kind="video",
                            topic=topic,
                            course_id=course_uuid,
                        )
                    )
                    package_id = f"manim-{run_id}"
                    package = {
                        "package_id": package_id,
                        "title": artifact["title"],
                        "artifacts": [artifact],
                    }
                    suggestions = [
                        "下载教学动画",
                        "再生成一版更短的视频",
                        f"生成{topic}配套讲义",
                    ]
                    final_text = f"Seedance 未配置；已使用千问生成「{topic}」教学分镜，并由 Manim 本地回退渲染为可下载的 MP4 动画。"
                    metrics = {
                        "route_trace": ["orchestrator", "qwen_storyboard_agent", "manim_renderer"],
                        "provider": "manim_fallback",
                        "resourcePackage": package,
                        "suggestions": suggestions,
                    }
                    yield _phase_finished(
                        "compose",
                        "生成教学动画",
                        "Manim 教学动画已渲染完成",
                    )
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "Manim 教学动画已生成")
                    yield task_event(
                        agent_task_service.complete_run(
                            db, run_id=run_id, message="Manim 教学动画生成完成"
                        )
                    )
                    if user_id:
                        chat_provider.save_stream_turn(
                            db,
                            thread_id=session_id,
                            user_input=request.message or "生成讲解视频",
                            response=final_text,
                            system_prompt=_system_prompt(request),
                            agent="qwen_manim_agent",
                            intent="generate_video",
                            routing_reason="orchestrator intent=generate_manim_video",
                            citations=[],
                            confidence="high",
                            grounding_mode="tool",
                            suggestions=suggestions,
                            metrics=metrics,
                        )
                        schedule_memory_profile_refresh(user_id)
                    done_payload = {
                        "runId": run_id,
                        "sessionId": session_id,
                        "messageId": uuid4().hex,
                        "summary": "Manim 教学动画生成完成",
                        "usage": metrics,
                        "suggestions": suggestions,
                    }
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except Exception as exc:
                    logger.warning("Manim video generation failed run_id=%s reason=%s", run_id, exc)
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="Manim 教学动画生成失败"
                        )
                    )
                    yield _phase_finished(
                        "compose",
                        "生成教学动画",
                        "Manim 教学动画生成失败",
                        status="error",
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "MANIM_VIDEO_GENERATION_FAILED",
                            "message": str(exc),
                            "retryAction": "retry",
                        },
                    )
                return

            if _is_quiz_generation_intent(request.message or ""):
                owned_prior_user_messages = [
                    turn["user"]
                    for turn in _prior_turns(db, session_id, user_id)
                    if turn.get("user", "").strip()
                ]
                prior_resource_package = _prior_owned_resource_package_context(
                    db, session_id, user_id
                )
                course, knowledge_point, question_count, difficulty = _quiz_context(
                    request.message or "",
                    course_context=request.course_context,
                    prior_user_messages=owned_prior_user_messages,
                    prior_resource_package=prior_resource_package,
                )
                yield update_task("executor", "running", 15, "正在生成结构化专项练习")
                yield _phase_started(
                    "compose", "生成专项练习", "Quiz Agent 正在生成结构化题目与答案解析"
                )
                yield _sse("artifact_started", {"label": "正在生成专项练习"})
                try:
                    quiz = quiz_service.generate(
                        db,
                        owner_id=current_user.id,
                        course=course,
                        knowledge_point=knowledge_point,
                        count=question_count,
                        difficulty=difficulty,
                        course_id=(
                            UUID(request.course_context.course_id)
                            if request.course_context.course_id
                            else None
                        ),
                    )
                    package = _quiz_package(quiz)
                    final_text = (
                        f"已生成“{quiz.title}”，共 {len(quiz.questions)} 道题。"
                        "点击下方资源卡片进入答题。"
                    )
                    suggestions = ["开始答题", "查看资料中心", f"讲解{knowledge_point}"]
                    metrics = {
                        "route_trace": ["orchestrator", "quiz_agent"],
                        "resourcePackage": package,
                        "resource_type": "question",
                        "resource_id": str(quiz.resource_id),
                        "suggestions": suggestions,
                    }
                    yield _phase_finished(
                        "compose", "生成专项练习", f"已生成 {len(quiz.questions)} 道结构化题目"
                    )
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "专项练习已生成并保存")
                    yield update_task("evaluator", "running", 60, "正在校验题目结构")
                    yield _phase_started("verify", "校验题目", "正在检查选项、答案与解析完整性")
                    yield _phase_finished("verify", "校验题目", "结构化题目校验通过")
                    yield update_task("evaluator", "completed", 100, "题目结构校验通过")
                    yield task_event(
                        agent_task_service.complete_run(
                            db, run_id=run_id, message="专项练习任务已完成"
                        )
                    )
                    if user_id:
                        chat_provider.save_stream_turn(
                            db,
                            thread_id=session_id,
                            user_input=request.message or "生成专项练习",
                            response=final_text,
                            system_prompt=_system_prompt(request),
                            agent="quiz_agent",
                            intent="generate_quiz",
                            routing_reason="orchestrator intent=generate_quiz",
                            citations=[],
                            confidence="high",
                            grounding_mode="tool",
                            suggestions=suggestions,
                            metrics=metrics,
                        )
                    done_payload = {
                        "runId": run_id,
                        "sessionId": session_id,
                        "messageId": uuid4().hex,
                        "summary": "结构化专项练习已生成并保存",
                        "usage": metrics,
                        "suggestions": suggestions,
                    }
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except QuizGenerationError as exc:
                    logger.warning("quiz generation failed run_id=%s reason=%s", run_id, exc)
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="专项练习生成失败"
                        )
                    )
                    yield _sse(
                        "error",
                        {
                            "code": "QUIZ_GENERATION_FAILED",
                            "message": "本次练习题未通过质量校验，未保存任何题目。请重试。",
                            "retryAction": "retry",
                        },
                    )
                return

            if _is_knowledge_graph_intent(request.message or ""):
                course, knowledge_point = _knowledge_graph_context(request.message or "")
                yield update_task("executor", "running", 15, "正在生成结构化知识图谱")
                yield _phase_started("compose", "生成知识图谱", "正在生成结构化知识节点与关系")
                yield _sse("artifact_started", {"label": "正在生成知识图谱"})
                try:
                    graph = generated_knowledge_graph_service.generate(
                        db,
                        owner_id=current_user.id,
                        course=course,
                        knowledge_point=knowledge_point,
                    )
                    package = _knowledge_graph_package(graph)
                    final_text = f"已生成“{graph.title}”。点击下方资源卡片即可查看知识图谱。"
                    suggestions = ["查看知识图谱", "生成配套练习", "讲解薄弱节点"]
                    metrics = {
                        "route_trace": ["orchestrator", "knowledge_graph_agent"],
                        "resourcePackage": package,
                        "resource_type": "knowledge_graph",
                        "resource_id": str(graph.resource_id),
                        "suggestions": suggestions,
                    }
                    yield _phase_finished(
                        "compose",
                        "生成知识图谱",
                        f"已生成 {len(graph.graph_json.nodes)} 个节点和 {len(graph.graph_json.edges)} 条关系",
                    )
                    yield _sse("artifact_finished", package)
                    yield _sse("answer_delta", {"text": final_text})
                    yield _sse("suggestions", {"items": suggestions})
                    yield update_task("executor", "completed", 100, "知识图谱已生成并保存")
                    yield update_task("evaluator", "running", 50, "正在校验节点与关系完整性")
                    yield _phase_started("verify", "校验图谱", "正在校验节点引用与图谱结构")
                    yield _phase_finished("verify", "校验图谱", "节点与关系结构校验通过")
                    yield update_task("evaluator", "completed", 100, "知识图谱结构校验通过")
                    yield task_event(
                        agent_task_service.complete_run(
                            db, run_id=run_id, message="知识图谱任务已完成"
                        )
                    )
                    if user_id:
                        chat_provider.save_stream_turn(
                            db,
                            thread_id=session_id,
                            user_input=request.message or "生成知识图谱",
                            response=final_text,
                            system_prompt=_system_prompt(request),
                            agent="knowledge_graph_agent",
                            intent="generate_knowledge_graph",
                            routing_reason="orchestrator intent=generate_knowledge_graph",
                            citations=[],
                            confidence="high",
                            grounding_mode="tool",
                            suggestions=suggestions,
                            metrics=metrics,
                        )
                    done_payload = {
                        "runId": run_id,
                        "sessionId": session_id,
                        "messageId": uuid4().hex,
                        "summary": "结构化知识图谱已生成并保存",
                        "usage": metrics,
                        "suggestions": suggestions,
                    }
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except KnowledgeGraphGenerationError as exc:
                    yield task_event(
                        agent_task_service.fail_run(
                            db, run_id=run_id, message="知识图谱生成失败"
                        )
                    )
                    yield _sse(
                        "error",
                        {"code": "KNOWLEDGE_GRAPH_GENERATION_FAILED", "message": str(exc)},
                    )
                return

            if (
                request.mode == "resource_generation"
                or request.tools.resource_generation
                or _is_resource_generation_intent(request.message or "")
            ):
                yield _phase_started("compose", "生成资源", "正在规划资源类型、难度和资料包结构")
                yield _phase_delta("compose", f"资源类型：{'、'.join(request.resource_request.types or ['lecture_note', 'mind_map', 'quiz'])}")
                yield _sse("artifact_started", {"label": "正在生成资源包"})
                try:
                    resource_request = _resource_generation_request(request)
                    requested_run = resource_package_service.create_requested_run(
                        db,
                        request=resource_request,
                        owner_id=current_user.id,
                    )
                    resource_run_id = requested_run.id
                    yield _sse(
                        "resource_run_started",
                        {
                            "runId": resource_run_id,
                            "status": "requested",
                            "cancelRequested": False,
                            "cancelUrl": f"/api/v1/resource-generation/runs/{resource_run_id}/cancel",
                        },
                    )
                    resource_package_service.enqueue_requested_run(resource_run_id)
                    last_step = ""
                    while True:
                        public_run = resource_package_service.get_run(
                            db,
                            run_id=resource_run_id,
                            user_id=current_user.id,
                            is_superuser=bool(current_user.is_superuser),
                        )
                        if not public_run:
                            raise RuntimeError("资源运行状态不可用")
                        if public_run.current_step != last_step or public_run.cancel_requested:
                            last_step = public_run.current_step
                            yield _sse(
                                "resource_run_status",
                                {
                                    "runId": resource_run_id,
                                    "status": public_run.status,
                                    "currentStep": public_run.current_step,
                                    "cancelRequested": public_run.cancel_requested,
                                },
                            )
                        if public_run.status in resource_package_service.TERMINAL_STATUSES:
                            resource_run_terminal = True
                            if public_run.status not in {"completed", "partial_success"}:
                                if public_run.status == "cancelled":
                                    yield _phase_finished(
                                        "compose", "生成资源", "资源运行已由服务端取消", status="cancelled"
                                    )
                                    yield _sse(
                                        "resource_run_cancelled",
                                        {"runId": resource_run_id, "status": "cancelled"},
                                    )
                                    return
                                raise RuntimeError(public_run.error_message or "资源生成运行失败")
                            if not public_run.package_id:
                                raise RuntimeError("资源运行完成但未返回资源包")
                            package = resource_package_service.get_package(
                                db,
                                package_id=public_run.package_id,
                                user_id=current_user.id,
                                is_superuser=bool(current_user.is_superuser),
                            )
                            if not package:
                                raise RuntimeError("资源运行结果不可用")
                            break
                        time.sleep(0.25)
                    yield _phase_finished("compose", "生成资源", f"资源包已生成，包含 {len(package.get('artifacts') or [])} 类内容")
                    yield _sse("artifact_finished", package)
                    final_text = (
                        f"已围绕“{request.resource_request.target or request.message or '当前主题'}”生成资源包 "
                        f"`{package.get('package_id')}`，包含 {len(package.get('artifacts') or [])} 类学习资源。"
                        "你可以打开资源卡片预览或下载完整内容。"
                    )
                    yield _sse("answer_delta", {"text": final_text})
                    follow_up_suggestions = [
                        "这些练习覆盖了哪些核心知识点？",
                        "请给我一份完成这些练习的顺序建议。",
                        "做错后应该如何定位对应的薄弱点？",
                    ]
                    final_payload = {
                        "agent": "resource_generator",
                        "content": final_text,
                        "citations": [],
                        "confidence": "medium",
                        "grounding_mode": "tool",
                        "suggestions": follow_up_suggestions,
                        "metrics": {
                            "route_trace": ["resource_planner", "resource_generator"],
                            "resourcePackage": package,
                            "suggestions": follow_up_suggestions,
                        },
                    }
                    yield _sse("suggestions", {"items": final_payload["suggestions"]})
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
                            yield _sse("profile_update", {"status": "queued", "message": "学习画像更新任务已提交"})
                        except Exception:
                            pass
                    done_payload = {
                        "runId": run_id,
                        "sessionId": session_id,
                        "messageId": uuid4().hex,
                        "summary": "本轮资源生成与持久化流程已结束",
                        "usage": final_payload["metrics"],
                        "suggestions": final_payload["suggestions"],
                    }
                    yield _sse("run_finished", done_payload)
                    yield _sse("done", done_payload)
                except GeneratorExit:
                    raise
                except ResourcePackagePersistenceError as exc:
                    if exc.code == "CONTENT_SAFETY_BLOCKED" and exc.safety_review:
                        yield _sse(
                            "safety_check",
                            {
                                **exc.safety_review,
                                "status": "blocked",
                                "message": str(exc),
                            },
                        )
                        yield _phase_finished(
                            "compose", "生成资源", "资源内容未通过安全审核", status="error"
                        )
                        yield _sse(
                            "error",
                            {
                                "code": exc.code,
                                "message": str(exc),
                                "auditId": exc.safety_review.get("audit_id"),
                            },
                        )
                    else:
                        yield _phase_finished("compose", "生成资源", "资源生成服务返回错误", status="error")
                        yield _sse("error", {"code": "RESOURCE_GENERATION_FAILED", "message": "资源生成未完成，请稍后重试。"})
                except Exception:
                    yield _phase_finished("compose", "生成资源", "资源生成服务返回错误", status="error")
                    yield _sse("error", {"code": "RESOURCE_GENERATION_FAILED", "message": "资源生成未完成，请稍后重试。"})
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
                    "agentKey": request.agent_key,
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
            answer_stream_started = False
            answer_input_seen = False
            next_answer_progress_chars = 480
            course_agent_output_guard = CourseAgentOutputGuard(
                hide_quiz_solution=is_initial_quiz_request(request.agent_key, request.message)
            )
            output_safety_guard = ContentSafetyStreamGuard(content_safety_service)
            output_safety_blocked = False
            output_safety_review = None

            def emit_approved_answer(text: str):
                nonlocal final_text, answer_stream_started, next_answer_progress_chars
                if not text:
                    return
                final_text += text
                if not answer_stream_started:
                    answer_stream_started = True
                    yield _phase_delta("compose", "回答已开始流式输出，可以边读边展开查看处理记录")
                yield _sse("answer_delta", {"text": text})
                if len(final_text) >= next_answer_progress_chars:
                    yield _phase_delta("compose", f"已输出约 {len(final_text)} 字，继续补全结构和细节")
                    next_answer_progress_chars += 640

            def emit_visible_answer(visible_text: str):
                nonlocal final_text, output_safety_blocked, output_safety_review
                if output_safety_blocked:
                    return
                if not visible_text:
                    return
                try:
                    approved = output_safety_guard.push(visible_text)
                except ContentSafetyBlockedError as exc:
                    output_safety_blocked = True
                    output_safety_review = exc.review
                    final_text = stable_block_message("output")
                    yield _sse(
                        "safety_check",
                        {
                            **exc.review.public_dict(),
                            "status": "blocked",
                            "message": final_text,
                        },
                    )
                    yield _sse("answer_delta", {"text": final_text})
                    return
                if approved:
                    yield from emit_approved_answer(approved)

            def emit_safe_answer(text: str):
                nonlocal answer_input_seen
                if text:
                    # The output guards may buffer short chunks before anything is
                    # approved for display. Track input separately from final_text so
                    # a provider's terminal payload is not fed through the guards a
                    # second time while that first chunk is still buffered.
                    answer_input_seen = True
                visible_text = course_agent_output_guard.push(text)
                if visible_text:
                    yield from emit_visible_answer(visible_text)

            for payload in stream_chat_events(chat_request):
                if isinstance(payload, dict):
                    if payload.get("type") == "final":
                        final_payload = payload
                        raw_final_text = str(payload.get("content") or "")
                        if not answer_input_seen and raw_final_text:
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
                            yield _sse(event_name, event_payload)
            process_delta = process_normalizer.ingest(reasoning_buffer)
            if process_delta:
                yield _process_delta_sse(process_delta.to_payload())
            guarded_tail = course_agent_output_guard.finish()
            if guarded_tail:
                yield from emit_visible_answer(guarded_tail)
            if not output_safety_blocked:
                try:
                    approved_tail = output_safety_guard.finish()
                except ContentSafetyBlockedError as exc:
                    output_safety_blocked = True
                    output_safety_review = exc.review
                    final_text = stable_block_message("output")
                    yield _sse(
                        "safety_check",
                        {
                            **exc.review.public_dict(),
                            "status": "blocked",
                            "message": final_text,
                        },
                    )
                    yield _sse("answer_delta", {"text": final_text})
                else:
                    if approved_tail:
                        yield from emit_approved_answer(approved_tail)
                    if output_safety_guard.last_review:
                        output_safety_review = output_safety_guard.last_review
                        yield _sse(
                            "safety_check",
                            {
                                **output_safety_guard.last_review.public_dict(),
                                "status": "passed",
                            },
                        )
            if course_agent_output_guard.sanitized and not output_safety_blocked:
                answer_guard_triggered = True
                yield _sse(
                    "process_sanitized",
                    {
                        "phaseId": "verify_output",
                        "title": "校验输出",
                        "summary": "已隐藏学生作答前不应出现的提示与答案线索。",
                        "status": "done",
                        "sanitized": True,
                        "timestamp": _now_iso(),
                    },
                )
                if not re.search(r"请.{0,12}(?:作答|回复|选择|判断)", final_text):
                    invitation = "\n\n请先给出你的答案和理由，我会在你作答后再提供提示与解析。"
                    final_text += invitation
                    yield _sse("answer_delta", {"text": invitation})
            if (
                not output_safety_blocked
                and final_text
                and contains_supplier_context(final_text)
                and not adapter_context.user_allows_supplier_context
            ):
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
            yield _phase_started("verify", "校验输出", "正在检查内部过程标记与产品身份边界")
            visible_output_safe = not bool(
                re.search(r"<\/?think>|intent_classifier|intermediate_steps", final_text, re.I)
            )
            yield _phase_finished(
                "verify",
                "校验输出",
                "已完成可见内容边界检查" if visible_output_safe else "检测到内部过程标记并已过滤",
                status="done" if visible_output_safe else "error",
            )
            metrics = dict(final_payload.get("metrics") or {})
            metrics["content_safety"] = {
                "input": input_safety.public_dict(),
                "output": output_safety_review.public_dict()
                if output_safety_review
                else None,
            }
            final_payload["metrics"] = metrics
            if output_safety_blocked:
                final_payload.update(
                    {
                        "content": stable_block_message("output"),
                        "citations": [],
                        "suggestions": [],
                        "confidence": "low",
                        "grounding_mode": "safety_blocked",
                    }
                )
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
                    yield _sse("profile_update", {"status": "queued", "message": "学习画像更新任务已提交"})
                except Exception:
                    pass
            done_payload = {
                "runId": run_id,
                "sessionId": session_id,
                "messageId": uuid4().hex,
                "summary": "本轮回答与可见内容边界检查已完成",
                "usage": (final_payload.get("metrics") or {}),
                "suggestions": list(final_payload.get("suggestions") or []),
            }
            yield _sse("run_finished", done_payload)
            yield _sse("done", done_payload)
        except Exception:
            yield _sse("error", {"code": "MODEL_PROVIDER_ERROR", "message": "模型服务暂时不可用，请稍后重试。"})
        finally:
            if resource_run_id and not resource_run_terminal:
                try:
                    resource_package_service.request_cancel(
                        db,
                        run_id=resource_run_id,
                        user_id=current_user.id,
                    )
                except Exception:
                    db.rollback()
            try:
                _trace_recorder.reset(trace_token)
            except ValueError:
                # StreamingResponse may close a generator from a different task context.
                _trace_recorder.set(None)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=_SSE_HEADERS)
