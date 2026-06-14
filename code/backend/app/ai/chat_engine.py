from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.ai.chat_models import ChatRequest, ChatResponse, State, SupervisorDecision
from app.ai.demo_response import build_demo_chat_response
from app.ai.chat_runtime import AGENT_CONFIG, resolve_system_prompt
from app.ai.structured_output import (
    StructuredAnswerPayload,
    build_citation_candidates,
    normalize_confidence,
    normalize_grounding_mode,
    parse_structured_payload,
)
from app.ai.chat_tools import (
    TOOL_KEYS_BY_AGENT,
    get_tools_for_agent,
    get_llm,
    message_text,
    collect_tool_calls,
)
from app.core.config import settings
from app.core.db import engine
from app.services.chat_model_factory import ChatModelFactory
from app.services.rag_service import RAGService
from app.services.pending_actions import pending_action_store
from app.services.ai_usage_logger import collect_usage_from_messages
from app.services.chat_semantic_cache import chat_semantic_cache
from app.ai.reasoning_stream import (
    ReasoningStreamController,
    clear_reasoning_context,
    get_reasoning_controller,
    set_reasoning_controller,
    set_reasoning_emitter,
    stream_thought_events as _stream_thought_events_impl,
)
from app.services.math_markdown import (
    looks_like_broken_math_markup,
    normalize_math_delimiters,
)
from app.services.user_memory_profile_service import user_memory_profile_service
from sqlmodel import Session

rag_service = RAGService()

_WORKERS = frozenset(
    {
        "code_tutor",
        "knowledge_mentor",
        "planner",
        "analyst",
        "doc_researcher",
        "quiz_master",
        "profile_agent",
        "retrieval_agent",
        "web_research_agent",
        "tutor_agent",
        "grading_agent",
        "safety_review_agent",
    }
)
_MAX_SUPERVISOR_ENTRIES = 12
# 连续「解析失败兜底」达到此次数则强制 FINISH，避免 supervisor ↔ worker 死循环
_MAX_SUPERVISOR_FALLBACK_STREAK = 2

# 工具节点进入时推送（stream_mode=updates 下每个 ToolNode 执行前可见）
_TOOL_NODE_PIPELINE_MSG: dict[str, str] = {
    "code_tutor_tools": "【知识检索】代码导师正在调用知识库 / 联网 / 代码沙盒等工具。",
    "knowledge_mentor_tools": "【知识检索】学科讲师正在调用知识库或联网检索。",
    "planner_tools": "【知识检索】规划师正在检索知识库以支撑计划建议。",
    "analyst_tools": "【学情分析】分析师正在调用知识库或行为分析类工具。",
    "doc_researcher_tools": "【文档检索】文档研究员正在检索你上传的文件。",
    "quiz_master_tools": "【测验支持】测验官正在检索相关知识点用于出题与讲解。",
}

_STAGE_PHASE_MAP: dict[str, tuple[str, str, str]] = {
    "pipeline_start": ("understand", "supervisor", "理解问题并启动多智能体协作"),
    "kb_inject": ("retrieve", "retrieval_agent", "检索课程知识库并注入上下文"),
    "tool_policy": ("plan", "supervisor", "配置本轮可用工具"),
    "web_policy": ("research", "web_research_agent", "准备联网检索补充"),
    "cache": ("finalize", "supervisor", "语义缓存命中，跳过协作图"),
    "tool_run": ("execute", "retrieval_agent", "执行检索或分析工具"),
    "vision_status": ("perceive", "tutor_agent", "解析上传图片内容"),
    "demo_mode": ("finalize", "supervisor", "演示模式回答"),
}

_TAG_PHASE_RULES: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"主管|拆解|流水线|策略|协作"), "understand", "supervisor", "协调任务分工"),
    (re.compile(r"知识检索|RAG|检索|文档"), "retrieve", "retrieval_agent", "检索知识证据"),
    (re.compile(r"联网|web", re.I), "research", "web_research_agent", "联网补充信息"),
    (re.compile(r"学情|行为|画像"), "analyze", "analyst", "分析学习情况"),
    (re.compile(r"测验|出题|练习"), "quiz", "quiz_master", "组织测验与讲解"),
    (re.compile(r"代码|沙盒|debug", re.I), "code", "code_tutor", "代码分析与调试"),
    (re.compile(r"汇总|合成|审查|安全"), "finalize", "safety_review_agent", "汇总并审查回答"),
    (re.compile(r"视觉|图像|图片"), "perceive", "tutor_agent", "理解视觉输入"),
]


def _build_phase_event(content: str, stage: str | None = None) -> dict[str, Any] | None:
    stage_key = (stage or "").strip()
    if stage_key in _STAGE_PHASE_MAP:
        phase, agent, default_summary = _STAGE_PHASE_MAP[stage_key]
    else:
        phase, agent, default_summary = "process", "supervisor", "协作处理中"
        tag = content or ""
        for pattern, p, a, s in _TAG_PHASE_RULES:
            if pattern.search(tag):
                phase, agent, default_summary = p, a, s
                break
    match = re.match(r"^【([^】]+)】([\s\S]*)$", content or "")
    summary = (
        (match.group(2) if match else content or default_summary).strip()[:160]
        or default_summary
    )
    return {
        "type": "phase",
        "phase": phase,
        "agent": agent,
        "summary": summary,
        "status": "running",
    }


def _stream_thought_events(
    content: str,
    stage: str | None = None,
    *,
    user_visible: bool = True,
    user_input: str = "",
    controller: ReasoningStreamController | None = None,
):
    yield from _stream_thought_events_impl(
        content,
        stage,
        user_visible=user_visible,
        user_input=user_input,
        controller=controller,
    )
    if not user_visible:
        return
    phase_evt = _build_phase_event(content, stage)
    if phase_evt:
        yield phase_evt


def _drain_reasoning_queue(queue: list[dict[str, Any]]):
    while queue:
        yield queue.pop(0)


def _normalize_answer_text(text: str) -> str:
    return normalize_math_delimiters(text or "")


def _stream_answer_tokens(text: str, chunk_size: int = 24):
    normalized = _normalize_answer_text(text)
    for i in range(0, len(normalized), chunk_size):
        chunk = normalized[i : i + chunk_size]
        yield {"type": "token", "content": chunk}


_JSON_OBJ = re.compile(r"\{[\s\S]*\}")
_DOC_QUERY_HINT = re.compile(
    r"(这篇|该|这个)?(论文|文档|报告|课件|pdf|PDF|word|Word|doc|DOC|章节|第[一二三四五六七八九十0-9]+章|摘要|方法|实验|结论|创新点|原文)"
)
_QUIZ_HINT = re.compile(
    r"(考考我|出题|做题|测验|测试我|我来答题|我来回答|来道题|出[一1]?道题|随堂测|小测)"
)
_GRADE_HINT = re.compile(r"(批改|评分|打分|订正|错因|我的答案|参考答案|掌握度)")
_FRESH_WEB_HINT = re.compile(
    r"(最新|最近|当前|今天|本周|本月|今年|新闻|政策|发布|版本|官网|开源|许可证|价格|行情|current|latest|today|news|version|official)"
)
_EXPLAIN_WITH_PRACTICE_HINT = re.compile(
    r"((讲解|解释|知识点|基础|不熟|不会|掌握|学习).{0,50}(练习|题目|训练|刷题)|"
    r"(练习|题目|训练|刷题).{0,50}(讲解|解释|知识点|基础|不熟|不会|掌握|学习))"
)

# 防止异常超大请求；实际需要更长可在 .env 提高 CHAT_DEFAULT_MAX_TOKENS
_MAX_OUTPUT_CAP = 131072
_SELECTION_MIN_ANSWER_CHARS = 420
_GENERAL_MIN_ANSWER_CHARS = 650
_BRIEF_ANSWER_HINT_RE = re.compile(r"(一句话|简短|简单说|概括|只要|不要展开|100字以内)")
_SUBSTANTIVE_TEACHING_HINT_RE = re.compile(
    r"(基础|基础不好|不太好|不熟|不会|零基础|讲解|讲讲|讲一讲|解释|说明|生成|写一份|教程|语法|例子|示例|步骤|怎么|如何|为什么|知识点|学习|练习|代码|链表|数组|栈|队列|数据库|SQL)"
)


def _supervisor_fallback_decision() -> SupervisorDecision:
    return SupervisorDecision(
        next_agent="knowledge_mentor",
        routing_reason="主管结构化输出解析失败或调用异常，已默认交给学科讲师处理。",
        task_breakdown="",
    )


def _strip_llm_json_fences(text: str) -> str:
    """去掉 ``` / ```json 围栏及常见 Markdown 包裹，降低主管 JSON 解析失败率。"""
    s = (text or "").strip()
    s = re.sub(r"```(?:json|JSON)?\s*", "", s)
    s = re.sub(r"\s*```", "", s)
    return s.strip()


def _parse_supervisor_decision_safe(text: str) -> tuple[SupervisorDecision, bool]:
    """主管路由 JSON 容错解析，永不抛异常。返回 (决策, 是否使用了兜底)。"""
    fb = _supervisor_fallback_decision()
    raw_in = _strip_llm_json_fences(str(text or "").strip())
    if not raw_in:
        return fb, True
    candidates = [raw_in]
    m = _JSON_OBJ.search(raw_in)
    if m and m.group() not in candidates:
        candidates.append(m.group())
    for cand in candidates:
        try:
            return SupervisorDecision.model_validate_json(cand), False
        except Exception:
            pass
        try:
            i, j = cand.find("{"), cand.rfind("}")
            if i < 0 or j <= i:
                continue
            blob = cand[i : j + 1]
            obj = json.loads(blob)
            if isinstance(obj, dict):
                return SupervisorDecision.model_validate(obj), False
        except Exception:
            continue
    return fb, True


def _truncate_message_contents(messages: list, max_chars: int) -> list:
    """单条消息正文过长时截断，避免工具返回/RAG 块撑爆上下文。"""
    out: list = []
    for m in messages:
        c = getattr(m, "content", "")
        if isinstance(c, str):
            if len(c) <= max_chars:
                out.append(m)
                continue
            nc = c[:max_chars] + "\n…[已截断]"
        elif isinstance(c, list):
            flat = message_text(m)
            if len(flat) <= max_chars:
                out.append(m)
                continue
            nc = flat[:max_chars] + "\n…[已截断]"
        else:
            out.append(m)
            continue
        if isinstance(m, SystemMessage):
            out.append(SystemMessage(content=nc))
        elif isinstance(m, HumanMessage):
            out.append(HumanMessage(content=nc))
        elif isinstance(m, AIMessage):
            out.append(
                AIMessage(content=nc, tool_calls=getattr(m, "tool_calls", None))
            )
        elif isinstance(m, ToolMessage):
            out.append(ToolMessage(content=nc, tool_call_id=m.tool_call_id))
        else:
            out.append(m)
    return out


def _normalize_graph_stream_event(event: Any) -> tuple[str | None, Any]:
    """将 graph.stream 的单步事件统一为 (mode, payload)，兼容多模式流与仅 updates 的旧行为。"""
    if isinstance(event, dict):
        t = event.get("type")
        if t in ("updates", "values", "messages", "debug", "tasks", "custom", "checkpoints"):
            if "data" in event:
                return str(t), event["data"]
        # 少数版本/模式下可能直接抛出完整 State 字典而非 ("values", dict)
        if "messages" in event and (
            "next_agent" in event or "supervisor_entries" in event
        ):
            return "values", event
        return "updates", event
    if isinstance(event, tuple):
        if len(event) == 2:
            a, b = event
            if isinstance(a, str) and a in (
                "updates",
                "values",
                "messages",
                "debug",
                "tasks",
                "custom",
                "checkpoints",
            ):
                return a, b
        if len(event) == 3:
            _ns, mode, chunk = event
            if isinstance(mode, str):
                return mode, chunk
    return None, event


# 用变量拼接标签名，避免工具/脱敏把字面量 `think` 改坏
_TK = "think"
_MODEL_THINK_STRIP = (
    re.compile(rf"<{_TK}>[\s\S]*?</{_TK}>", re.IGNORECASE | re.DOTALL),
    re.compile(r"<analysis>[\s\S]*?</analysis>", re.IGNORECASE | re.DOTALL),
    re.compile(rf"</?{_TK}>", re.IGNORECASE),
    re.compile(r"</?analysis>", re.IGNORECASE),
)


def _strip_think_blocks_from_text(text: str) -> str:
    """从 content 字符串中去掉思考/分析块，减少主气泡里的「内心戏」残留。"""
    if not text:
        return text
    t = text
    for pat in _MODEL_THINK_STRIP:
        t = pat.sub("", t)
    return t.strip()


def _strict_ai_content_for_user(message: Any) -> str:
    """
    仅使用 AIMessage.content 作为用户可见正文。
    绝不读取 additional_kwargs 的 reasoning_content/thinking（否则会泄漏到主聊天气泡）。
    """
    if not isinstance(message, AIMessage):
        return (message_text(message) or "").strip()
    c = message.content
    if isinstance(c, str):
        s = c.strip()
    elif isinstance(c, list):
        parts: list[str] = []
        for block in c:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif "text" in block:
                    parts.append(str(block["text"]))
            elif isinstance(block, str):
                parts.append(block)
        s = "\n".join(parts).strip()
    else:
        s = (str(c) if c else "").strip()
    return _strip_think_blocks_from_text(s)


def _last_meaningful_assistant_text(messages: list) -> str:
    """自尾向前取第一条含正文的 AIMessage（仅 content，不含 reasoning 通道）。"""
    for m in reversed(messages or []):
        if not isinstance(m, AIMessage):
            continue
        body = _strict_ai_content_for_user(m)
        if body:
            return body
        tool_calls = getattr(m, "tool_calls", None) or []
        if tool_calls:
            continue
    if messages:
        last = messages[-1]
        if isinstance(last, AIMessage):
            t = _strict_ai_content_for_user(last)
            if t:
                return t
        tail = message_text(last)
        if isinstance(tail, str) and tail.strip():
            return _strip_think_blocks_from_text(tail.strip())
    return ""


def _looks_like_route_json_blob(text: str) -> bool:
    s = (text or "").strip()
    if not s.startswith("{"):
        return False
    low = s.lower()
    return "next_agent" in low and ("routing" in low or "task_breakdown" in low)


def _latest_human_index(messages: list) -> int:
    for i in range(len(messages or []) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return i
    return -1


def _latest_human_question(messages: list) -> str:
    idx = _latest_human_index(messages)
    if idx < 0:
        return ""
    return (message_text(messages[idx]) or "").strip()


def _recent_public_history(messages: list, max_turns: int = 4) -> list[str]:
    """仅保留学生与最终导师可见对话，排除专员中间日志。"""
    lines: list[str] = []
    for m in messages or []:
        if isinstance(m, HumanMessage):
            txt = (message_text(m) or "").strip()
            if txt:
                lines.append(f"学生：{txt}")
            continue
        if isinstance(m, AIMessage) and getattr(m, "name", "") == "final_answer":
            txt = _strict_ai_content_for_user(m)
            if txt:
                lines.append(f"导师：{txt}")
    if max_turns <= 0:
        return lines
    return lines[-(max_turns * 2) :]


def _rag_system_excerpt(messages: list, max_chars: int) -> str:
    if not messages:
        return ""
    m0 = messages[0]
    if not isinstance(m0, SystemMessage):
        return ""
    body = (message_text(m0) or "").strip()
    if not body:
        return ""
    if len(body) > max_chars:
        return body[:max_chars] + "\n…[知识库上下文已截断]"
    return body


def _load_user_memory_context(user_id: str | None) -> str:
    if not user_id:
        return ""
    try:
        with Session(engine) as session:
            return user_memory_profile_service.build_prompt_injection(session, user_id)
    except Exception:
        return ""


def _collect_worker_outputs_for_finalize(messages: list, max_total: int = 14000) -> str:
    """仅收集当前问题之后的专员产出，避免把旧轮次材料重复喂给汇总。"""
    blocks: list[str] = []
    latest_human = _latest_human_index(messages)
    start = latest_human + 1 if latest_human >= 0 else 0
    for m in (messages or [])[start:]:
        if not isinstance(m, AIMessage):
            continue
        if getattr(m, "name", "") == "final_answer":
            continue
        chunk = _strict_ai_content_for_user(m)
        if not chunk:
            continue
        if _looks_like_route_json_blob(chunk):
            continue
        blocks.append(chunk)
    if not blocks:
        return ""
    merged = "\n\n---\n\n".join(blocks)
    if len(merged) <= max_total:
        return merged
    return merged[-max_total:] + "\n…[较早专员输出已截断，保留较近内容]"


def _is_selection_query_text(text: str) -> bool:
    blob = text or ""
    return "选中了" in blob and "上下文片段" in blob


# AI辅助生成：Kimi Code, 2026-04-08
def _expand_selection_answer_if_needed(
    llm: Any,
    *,
    current_q: str,
    answer: str,
    rag_excerpt: str,
    worker_material: str,
) -> str:
    clean_answer = (answer or "").strip()
    if (
        not _is_selection_query_text(current_q)
        or len(clean_answer) >= _SELECTION_MIN_ANSWER_CHARS
    ):
        return clean_answer

    expand_sys = SystemMessage(
        content=(
            "你是智屿课堂划词唤醒的最终解答老师。学生选中了课堂内容中的一个概念，"
            "你需要把已有短答扩写成完整、耐心、可直接展示的课堂讲解。"
            "硬性要求：正文控制在 500-800 个中文字符；使用 3-5 个 Markdown 小标题；"
            "必须覆盖概念定位、核心机制、课堂例子、常见误区或实践价值、下一步学习建议；"
            "如果涉及数据库索引，请准确区分 B 树/B+ 树这类多路平衡搜索树与二叉搜索树；"
            "不要输出内部思考，不要提及模型、路由、工具或 JSON。"
        )
    )
    expand_human = HumanMessage(
        content=(
            f"【划词问题】\n{current_q}\n\n"
            f"【已有短答】\n{clean_answer or '（无）'}\n\n"
            f"【知识库摘要】\n{rag_excerpt or '（无）'}\n\n"
            "【专员材料】\n"
            f"{worker_material or '（无）'}"
        )
    )
    try:
        expanded_msg = llm.invoke([expand_sys, expand_human])
        expanded = _strip_think_blocks_from_text(
            _strict_ai_content_for_user(expanded_msg)
        ).strip()
        if len(expanded) > len(clean_answer):
            return expanded
    except Exception:
        pass
    return clean_answer


def _needs_substantive_teaching_answer(user_q: str, answer: str) -> bool:
    q = (user_q or "").strip()
    if not q:
        return False
    if _is_selection_query_text(q):
        return False
    if len((answer or "").strip()) >= _GENERAL_MIN_ANSWER_CHARS:
        return False
    if _BRIEF_ANSWER_HINT_RE.search(q):
        return False
    if _QUIZ_HINT.search(q) and not _EXPLAIN_WITH_PRACTICE_HINT.search(q):
        return False
    return bool(_SUBSTANTIVE_TEACHING_HINT_RE.search(q))


def _expand_general_answer_if_needed(
    llm: Any,
    *,
    current_q: str,
    answer: str,
    rag_excerpt: str,
    worker_material: str,
) -> str:
    clean_answer = (answer or "").strip()
    if not _needs_substantive_teaching_answer(current_q, clean_answer):
        return clean_answer
    current_topic = _pick_topic_from_question(current_q)

    expand_sys = SystemMessage(
        content=(
            "你是智屿智能伴学的最终答复老师。学生需要的是可直接学习的完整回答，"
            "而不是一句短定义。请把已有短答扩写成 700-1100 个中文字符的教学型回答。"
            "必须围绕学生当前问题本身，不要被知识库里相邻但不同的主题带偏。"
            "要求：1）先回应学生水平与目标；2）分层讲清核心概念和操作步骤；"
            "3）至少给一个贴近题目的例子，涉及数据结构/代码时给最小可读示例；"
            "4）列出常见误区；5）给出下一步练习建议。"
            "如果学生明确要求练习题，最后必须补一个【练习题】小节，给 2-4 道由浅入深的题目，"
            "并标出每题考查点或提示。"
            "不要输出内部思考、模型提示、路由或 JSON。"
        )
    )
    expand_human = HumanMessage(
        content=(
            f"【学生问题】\n{current_q}\n\n"
            f"【当前主题锁定】\n{current_topic}\n\n"
            f"【已有短答】\n{clean_answer or '（无）'}\n\n"
            f"【知识库摘要】\n{rag_excerpt or '（无）'}\n\n"
            f"【专员材料】\n{worker_material or '（无）'}"
        )
    )
    try:
        expanded_msg = llm.invoke([expand_sys, expand_human])
        expanded = _strip_think_blocks_from_text(
            _strict_ai_content_for_user(expanded_msg)
        ).strip()
        if len(expanded) > len(clean_answer):
            return expanded
    except Exception:
        pass
    return clean_answer


def _expand_final_answer_if_needed(
    llm: Any,
    *,
    current_q: str,
    answer: str,
    rag_excerpt: str,
    worker_material: str,
) -> str:
    if _is_selection_query_text(current_q):
        return _expand_selection_answer_if_needed(
            llm,
            current_q=current_q,
            answer=answer,
            rag_excerpt=rag_excerpt,
            worker_material=worker_material,
        )
    return _expand_general_answer_if_needed(
        llm,
        current_q=current_q,
        answer=answer,
        rag_excerpt=rag_excerpt,
        worker_material=worker_material,
    )


def _clip_messages_for_llm(messages: list) -> list:
    """保留首段（通常为 RAG 系统消息）+ 最近若干条，再按单条长度截断。"""
    if not messages:
        return messages
    h = max(1, int(settings.CHAT_CONTEXT_HEAD_MESSAGES))
    t = max(4, int(settings.CHAT_CONTEXT_TAIL_MESSAGES))
    mc = max(512, int(settings.CHAT_CONTEXT_MAX_MESSAGE_CHARS))
    if len(messages) <= h + t:
        clipped = list(messages)
    else:
        clipped = list(messages[:h]) + list(messages[-t:])
    return _truncate_message_contents(clipped, mc)


def _resolve_max_tokens(request: ChatRequest) -> int:
    """请求未传或非法时使用配置默认值，保证专员/汇总始终带显式上限（避免部分模型默认过短）。"""
    mt = request.max_tokens
    if mt is not None and mt > 0:
        return min(int(mt), _MAX_OUTPUT_CAP)
    return min(int(settings.CHAT_DEFAULT_MAX_TOKENS), _MAX_OUTPUT_CAP)


def _with_resolved_max_tokens(request: ChatRequest) -> ChatRequest:
    return request.model_copy(update={"max_tokens": _resolve_max_tokens(request)})


# AI辅助生成：Claude Code, 2026-04-21
SUPERVISOR_SYSTEM_PROMPT = """你是「智屿学习系统」的主管 Supervisor（包工头），负责编排多位专员协同完成学生问题。

下属专员（每次只派其中一人发言，或判定可以结束）：
- code_tutor：编程语言报错、调试、运行失败、SQL/Python/Java/TS 等工程问题。
- knowledge_mentor：跨学科知识点讲解、概念辨析、教材型问答（经管、数理、文史、自然科学等），非代码排错优先找 TA。
- planner：学习计划、进度、复习节奏、里程碑与任务拆解。
- analyst：学习行为、状态评估、风险与数据化解读。
- doc_researcher：围绕用户当前挂载文档（论文/课件/报告）做检索式解读与细节问答。
- quiz_master：主动测验与批改，负责“出题->等待作答->点评引导”闭环。
- profile_agent：学习画像维度、掌握度变化和干预建议。
- retrieval_agent：课程知识库与上传文档证据整理。
- web_research_agent：联网搜索、来源筛选、时效判断和事实校验。
- tutor_agent：图像+文本多模态题解、概念讲解和分步辅导。
- grading_agent：练习批改、评分、错因和后续练习建议。
- safety_review_agent：事实性、防幻觉、来源标注和安全审查。

规则：
1. 结合完整对话历史判断「下一步谁最合适」；复合型需求可拆成多轮，一轮只派一名专员。
2. 若专员已在消息中充分覆盖且无需他人补位，输出 FINISH 进入汇总阶段。
3. 信息严重不足时可先派 knowledge_mentor 或 code_tutor 做澄清式回答，再视情况 FINISH 或继续派其他人。
4. 输出必须严格符合约定的结构化字段（next_agent / routing_reason / task_breakdown），不要输出其它闲聊；禁止用 Markdown 代码块包裹 JSON。
5. 【必须遵守】当你认为下属专员已经给出足够信息、或问题已可收束、或不宜再换人时，你 MUST 将 next_agent 设为字符串 FINISH（仅此一种写法），进入汇总；不要继续派发专员。
6. task_breakdown 仅写简短要点（每条一行内），禁止写入完整解题过程或长篇推导，避免污染协作上下文。
7. 用户明确请求“考考我/出题/测试一下/我来回答上一题”等主动测验场景时，优先路由 quiz_master；
   但如果同一句里同时要求“讲解知识点/基础不熟/给练习题”，先路由 knowledge_mentor 完成讲解与练习设计，不要只走测验流程。
8. 若用户当前挂载了文件，且问题指向该文件内容（如“总结这篇论文”“解释第三章”），优先路由 doc_researcher。"""

FINALIZE_SYSTEM_PROMPT = """你是智屿学习系统的最终发言人。你将收到「学生问题」「知识库摘要」「专员协作产出」。请面向学生生成可直接发送的最终答复。

必须遵守：
1. 直接给出完整、专业的解答，使用 Markdown 标题与列表排版；语气像耐心的导师。
2. 禁止「我先想想」「接下来我要」「不对，应该是」等内心独白、草稿式自言自语；禁止复述专员的思考过程，只输出结论与推导要点。
3. 禁止提及主管、路由、JSON、工具名、Agent、LangGraph 等内部实现与协作流程词。
4. 专员材料不足时诚实说明，可结合知识库与通用知识合理补充，勿编造上传资料中不存在的事实。
5. 涉及公式、复杂度、推导或符号化定义时，行内公式用 $...$，独立公式用 $$...$$，不要把 LaTeX 放进代码块。
6. 如果本轮使用了联网搜索，正文中必须单独写出“联网搜索补充”，说明来源类型、合理性判断和与课程资料的关系；不能把搜索结果伪装成课程知识库内容。
7. 在正文结束后，必须附加如下结构（严格保留标签）：
[SUGGESTIONS]
问题1
问题2
问题3"""

_SUGGESTIONS_TAG = re.compile(r"\[SUGGESTIONS\]", re.IGNORECASE)


def _split_suggestions(text: str) -> tuple[str, list[str]]:
    raw = (text or "").strip()
    if not raw:
        return "", []
    m = _SUGGESTIONS_TAG.search(raw)
    if not m:
        return raw, []
    body = raw[: m.start()].strip()
    tail = raw[m.end() :].strip()
    lines = [ln.strip(" -\t\r\n") for ln in tail.splitlines() if ln.strip()]
    suggestions: list[str] = []
    for s in lines:
        s2 = re.sub(r"^(问题\s*\d+[:：.\-、]?\s*)", "", s, flags=re.IGNORECASE)
        s2 = re.sub(r"^(\d+[:：.\-、]\s*)", "", s2)
        s2 = s2.strip()
        if len(s2) < 2:
            continue
        suggestions.append(s2[:80])
        if len(suggestions) >= 3:
            break
    return body, suggestions


def _rule_based_route(state: State) -> tuple[str, str] | None:
    try:
        user_q = _latest_human_question(state.get("messages") or []).strip()
    except Exception:
        user_q = ""
    if not user_q:
        return None
    tool_mode = (state.get("tool_mode") or "chat").strip()
    if tool_mode == "exercise_grading" or _GRADE_HINT.search(user_q):
        return ("grading_agent", "练习批改或订正请求，交由批改教师处理。")
    if tool_mode == "image_tutoring" or state.get("image_context"):
        return ("tutor_agent", "检测到图片与文本联合提问，交由多模态辅导教师处理。")
    if tool_mode == "digital_human_explain":
        return ("tutor_agent", "数字人讲解请求，交由辅导教师生成适合口播的视频讲稿。")
    active_tools = set(state.get("active_tools") or [])
    if "web_search" in active_tools and _FRESH_WEB_HINT.search(user_q):
        return ("web_research_agent", "问题包含时效性或外部事实校验需求，启用联网研究员。")
    if _EXPLAIN_WITH_PRACTICE_HINT.search(user_q):
        return ("knowledge_mentor", "复合学习请求，先完成知识讲解与练习设计。")
    if _QUIZ_HINT.search(user_q):
        return ("quiz_master", "命中测验意图，进入主动测验流程。")
    current_file_id = (state.get("current_file_id") or "").strip()
    if current_file_id and _DOC_QUERY_HINT.search(user_q):
        file_name = (state.get("current_file_name") or "").strip()
        return (
            "doc_researcher",
            f"文档问题，优先检索《{file_name or current_file_id}》。",
        )
    return None


def _default_suggestions(user_q: str) -> list[str]:
    q = (user_q or "").strip()
    if not q:
        return [
            "这一步最容易在哪里出错？",
            "能给一个最小练习题吗？",
            "下一步应该怎么学？",
        ]
    return [
        "先补哪个核心知识点？",
        "能给一道由浅入深的练习题吗？",
        "答错时应该怎么快速纠正？",
    ]


def _parse_suggestion_candidates(raw: str) -> list[str]:
    s = (raw or "").strip()
    if not s:
        return []
    candidates: list[str] = []
    try:
        obj = json.loads(s)
        if isinstance(obj, list):
            candidates = [str(x).strip() for x in obj if str(x).strip()]
        elif isinstance(obj, dict):
            arr = obj.get("suggestions") or []
            if isinstance(arr, list):
                candidates = [str(x).strip() for x in arr if str(x).strip()]
    except Exception:
        block = re.search(r"\[[\s\S]*\]", s)
        if block:
            try:
                arr = json.loads(block.group(0))
                if isinstance(arr, list):
                    candidates = [str(x).strip() for x in arr if str(x).strip()]
            except Exception:
                candidates = []
    out: list[str] = []
    q_hint = re.compile(
        r"(吗|么|如何|为什么|怎么|是否|能否|能不能|帮我|给我|带我|我该|我想|哪|哪些|几种|\?)"
    )
    for c in candidates:
        cc = re.sub(r"\s+", " ", c).strip()
        if len(cc) < 4:
            continue
        if not q_hint.search(cc):
            continue
        if not cc.endswith(("?", "？")):
            cc = f"{cc}？"
        if cc in out:
            continue
        out.append(cc[:80])
        if len(out) >= 3:
            break
    return out


_SUBJECT_KEYWORDS = [
    "数据库关系模型",
    "关系数据库模型",
    "关系模型",
    "ER模型",
    "E-R模型",
    "实体关系模型",
    "数据库",
    "SQL",
    "事务处理",
    "并发控制",
    "范式",
    "主键",
    "外键",
    "索引",
    "B+树",
    "B树",
    "小学数学",
    "初中数学",
    "高中数学",
    "微积分",
    "线性代数",
    "概率论",
    "链表",
    "数组",
    "栈",
    "队列",
    "二叉树",
    "树结构",
    "递归",
    "排序",
    "指针",
]

_BAD_TOPIC_FRAGMENT_RE = re.compile(
    r"(必要|一些|一下|帮我|给我|讲解|解释|说明|学习|最近|掌握|不熟|不会|基础|知识点|题型|题目|练习)"
)


def _clean_topic_candidate(value: str) -> str:
    topic = re.sub(r"\s+", "", str(value or "").strip())
    topic = re.sub(r"^(关于|围绕|针对|聚焦|一下|一些|这个|该|当前|本节|本课)", "", topic)
    topic = re.sub(
        r"(的)?(基础|语法|教程|知识点|知识|内容|题型|题目|练习|问题|部分)$",
        "",
        topic,
    )
    topic = re.sub(r"[的地得]+$", "", topic)
    if len(topic) < 2 or _BAD_TOPIC_FRAGMENT_RE.search(topic):
        return ""
    return topic[:20]


def _pick_topic_from_question(user_q: str) -> str:
    q = (user_q or "").strip()
    if not q:
        return "这个知识点"
    # 优先按明确学科/知识点关键词识别主题，避免提取成“必要的知识点”这类动作片段。
    for kw in _SUBJECT_KEYWORDS:
        if kw in q:
            return kw
    # 优先提取「X的/关于X/围绕X」这类显式主题片段
    patterns = [
        r"(?:关于|围绕|针对|聚焦)\s*([^\s，。；！？,.!?]{2,24})",
        r"(?:生成|写|讲|解释|学习|整理|梳理)(?:一个|一份|一下)?\s*([^\s，。；！？,.!?]{2,24}?)(?:基础|语法|教程|知识|示例|代码)",
        r"([^\s，。；！？,.!?]{2,24})\s*的(?:核心|典型|重点|难点|易错点|题型|知识点)",
        r"解决\s*([^\s，。；！？,.!?]{2,24})\s*(?:问题|难题|题目)",
    ]
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            topic = _clean_topic_candidate(m.group(1))
            if topic:
                return topic

    return "这个知识点"


def _pick_topic_from_context(user_q: str, answer: str) -> str:
    topic = _pick_topic_from_question(user_q)
    if topic != "这个知识点":
        return topic
    text = f"{user_q}\n{answer or ''}"
    for kw in _SUBJECT_KEYWORDS:
        if kw in text:
            return kw
    return topic


def _infer_followup_intent(user_q: str, answer: str) -> str:
    text = f"{user_q}\n{answer}".lower()
    if re.search(r"(错题|做错|纠正|订正|debug|排错)", text):
        return "fix"
    if re.search(r"(练习|刷题|题目|训练|测验|出题)", text):
        return "practice"
    if re.search(r"(总结|梳理|归纳|框架)", text):
        return "summary"
    return "explain"


def _contextual_suggestions_from_llm(
    user_q: str, answer: str, max_tokens: int | None = None
) -> list[str]:
    # 为保证主回复稳定，不再在流式尾部二次调用 LLM；
    # 改为基于当前问题主题生成上下文相关追问。
    topic = _pick_topic_from_context(user_q, answer)
    intent = _infer_followup_intent(user_q, answer)
    _ = max_tokens
    if topic in {"数据库关系模型", "关系数据库模型", "关系模型"}:
        if intent == "practice":
            return [
                "实体、属性和关系怎么区分？",
                "能给几道关系模型入门题吗？",
                "关系模型和ER模型有什么区别？",
            ]
        return [
            "关系模型最核心的概念有哪些？",
            "主键和外键怎么快速判断？",
            "能给一个关系模型转换例子吗？",
        ]
    if topic == "这个知识点":
        if intent == "practice":
            return [
                "能先给一道入门练习吗？",
                "这部分最容易错在哪里？",
                "能用例子带我做一遍吗？",
            ]
        if intent == "fix":
            return [
                "这类错误应该怎么排查？",
                "能给一个订正思路模板吗？",
                "遇到同类题怎么快速自检？",
            ]
        if intent == "summary":
            return [
                "能帮我梳理成复习提纲吗？",
                "哪些概念最容易混淆？",
                "接下来应该先复习哪部分？",
            ]
        return [
            "这部分核心概念怎么串起来？",
            "能举一个更具体的例子吗？",
            "学这里最容易卡在哪里？",
        ]
    if intent == "practice":
        return [
            f"能先给一道{topic}入门练习吗？",
            f"{topic}最容易错在哪里？",
            f"能用{topic}例子带我做一遍吗？",
        ]
    if intent == "fix":
        return [
            f"{topic}最常见的3个错误是什么？",
            f"能给一个{topic}错题订正模板吗？",
            f"遇到{topic}同类题时怎么快速自检？",
        ]
    if intent == "summary":
        return [
            f"能把{topic}压缩成5条速记卡片吗？",
            f"能给一张{topic}易混概念对照表吗？",
            f"{topic}复习优先级怎么安排？",
        ]
    return [
        f"{topic}的核心概念怎么串起来？",
        f"能举一个{topic}的具体例子吗？",
        f"学{topic}最容易混淆哪里？",
    ]


def _llm_followup_suggestions(user_q: str, answer: str) -> list[str]:
    if not (user_q or "").strip() or not (answer or "").strip():
        return []
    topic = _pick_topic_from_context(user_q, answer)
    try:
        llm = ChatModelFactory.create(temperature=0.25, max_tokens=384)
        prompt = [
            SystemMessage(
                content=(
                    "你负责为智能伴学对话生成 3 个下一轮追问胶囊。"
                    "这些胶囊会被学生点击后直接发送给 AI，所以要像学生自然会继续问的问题。"
                    "只输出 JSON 数组，正好 3 条。"
                    "每条 10-34 个中文字符，语气自然、具体、可直接发送；"
                    "可以使用“能不能/怎么/哪些/为什么/帮我”等表达，"
                    "但不要为了第一人称硬塞“我，”“我想我”“请问您是否需要”等别扭话。"
                    "必须综合【学生上一问】和【AI刚才回答】来预测下一步问题，"
                    "不要只套模板，不要把“必要、一些、知识点、题型”当作主题。"
                    "三条追问应分别覆盖：继续理解、练习巩固、易错/迁移应用。"
                    "必须紧扣学生上一问的主题或回答中的具体概念，不要跳到无关知识点。"
                )
            ),
            HumanMessage(
                content=(
                    f"【学生上一问】\n{user_q}\n\n"
                    f"【识别出的主题】\n{topic}\n\n"
                    f"【AI刚才回答】\n{answer[:1800]}\n\n"
                    "请预测学生最可能继续关心的 3 个问题；如果主题识别有误，以学生上一问和回答正文为准。"
                )
            ),
        ]
        msg = llm.invoke(prompt)
        return _parse_suggestion_candidates(_strict_ai_content_for_user(msg))
    except Exception:
        return []


_FOLLOWUP_FORBIDDEN_VIEWPOINT_RE = re.compile(
    r"(您|你是否|是否需要|请问你|请问您)"
)
_FOLLOWUP_QUESTION_HINT_RE = re.compile(
    r"(吗|么|如何|为什么|怎么|是否|能否|能不能|帮我|给我|带我|我该|我想|可以|应该|哪|哪些|哪个|\?|？)"
)
def _clean_followup_question(text: str) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", s)
    s = re.sub(r"^(问题\s*\d+[:：.\-、]?\s*)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^(\d+[:：.\-、]\s*)", "", s)
    s = s.strip(" -\t\r\n\"'“”‘’")
    s = re.sub(r"^我[，,、：:]\s*", "", s)
    s = re.sub(r"^我\s+(?=(帮我|给我|能不能|可以|需要|应该|该|想|要))", "", s)
    s = re.sub(r"^(帮我|给我)\s*(帮我|给我)", r"\1", s)
    s = re.sub(r"[。.!！?？]+$", "", s).strip()
    if not s:
        return ""
    s = f"{s}？"
    return s[:80]


def _is_followup_relevant(user_q: str, answer: str, item: str) -> bool:
    topic = _pick_topic_from_context(user_q, answer)
    text = item or ""
    if re.search(r"(解一下必要|解一些必要|必要哪|一些必要|必要题型)", text):
        return False
    related_topics = {
        "数据库关系模型": {"关系数据库模型", "关系模型", "ER模型", "E-R模型", "实体关系模型", "数据库"},
        "关系数据库模型": {"数据库关系模型", "关系模型", "ER模型", "E-R模型", "实体关系模型", "数据库"},
        "关系模型": {"数据库关系模型", "关系数据库模型", "ER模型", "E-R模型", "实体关系模型", "数据库"},
        "数据库": {"SQL", "事务处理", "并发控制", "范式", "主键", "外键", "索引", "B+树", "B树", "关系模型"},
    }
    if topic != "这个知识点":
        allowed_topics = {topic, *related_topics.get(topic, set())}
        if any(kw in text for kw in _SUBJECT_KEYWORDS if kw not in allowed_topics):
            return False
    if topic == "这个知识点":
        return True
    if topic in text:
        return True
    # 允许自然代词，但要求仍是学习推进类问题。
    if re.search(r"(这个|这类|同类|入门|基础|核心|易错|练习|题|例子|步骤|区别|判断|自检)", text):
        return True
    domain_terms = {
        "数据库关系模型": ["实体", "属性", "关系", "ER", "E-R", "主键", "外键", "表", "范式"],
        "关系数据库模型": ["实体", "属性", "关系", "ER", "E-R", "主键", "外键", "表", "范式"],
        "关系模型": ["实体", "属性", "关系", "ER", "E-R", "主键", "外键", "表", "范式"],
        "数据库": ["SQL", "表", "字段", "主键", "外键", "范式", "事务", "索引"],
        "链表": ["节点", "指针", "头结点", "遍历", "插入", "删除"],
    }
    return any(term in text for term in domain_terms.get(topic, []))


def _normalize_followups(
    user_q: str, answer: str, candidates: list[str] | None
) -> list[str]:
    normalized: list[str] = []
    for raw in candidates or []:
        item = _clean_followup_question(raw)
        if len(item) < 4:
            continue
        if _FOLLOWUP_FORBIDDEN_VIEWPOINT_RE.search(item):
            continue
        if not _FOLLOWUP_QUESTION_HINT_RE.search(item):
            continue
        if not _is_followup_relevant(user_q, answer, item):
            continue
        if item not in normalized:
            normalized.append(item)
        if len(normalized) >= 3:
            return normalized[:3]

    for raw in _contextual_suggestions_from_llm(user_q, answer):
        item = _clean_followup_question(raw)
        if item and item not in normalized:
            normalized.append(item)
        if len(normalized) >= 3:
            return normalized[:3]

    for raw in _default_suggestions(user_q):
        item = _clean_followup_question(raw)
        if item and item not in normalized:
            normalized.append(item)
        if len(normalized) >= 3:
            break
    return normalized[:3]


def _build_rag_context(request: ChatRequest) -> tuple[SystemMessage, list[dict[str, Any]]]:
    general_results = rag_service.query_knowledge_base(
        query=request.user_input,
        k=request.rag_k,
        user_id=request.user_id,
        is_admin=request.is_admin,
    )
    document_results: list[dict[str, Any]] = []
    current_file_id = (request.current_file_id or "").strip()
    if current_file_id:
        document_results = rag_service.search_uploaded_document(
            query=request.user_input,
            file_id=current_file_id,
            thread_id=request.thread_id,
            user_id=request.user_id,
            is_admin=request.is_admin,
            top_k=max(6, int(request.rag_k)),
        )
        if re.search(
            r"(总结|概括|主要内容|motivation|method|methodology|abstract|"
            r"conclusion|贡献|创新点|研究动机|研究方法)",
            request.user_input or "",
            re.I,
        ):
            document_results.extend(
                rag_service.search_uploaded_document(
                    query=(
                        "abstract introduction research motivation problem "
                        "method methodology experiment result conclusion contribution"
                    ),
                    file_id=current_file_id,
                    thread_id=request.thread_id,
                    user_id=request.user_id,
                    is_admin=request.is_admin,
                    top_k=6,
                )
            )
        controller = get_reasoning_controller()
        if controller is not None:
            controller.on_document_retrieve(
                request.user_input,
                len(document_results),
                [
                    str(item.get("content") or "")[:120]
                    for item in document_results[:4]
                ],
            )

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in [*document_results, *general_results]:
        key = (
            str(item.get("source") or ""),
            str(item.get("chunk_id") or item.get("content") or "")[:160],
        )
        if key in seen:
            continue
        seen.add(key)
        normalized = dict(item)
        normalized["citation_id"] = len(results) + 1
        normalized["context_scope"] = (
            "uploaded_document" if item in document_results else "knowledge_base"
        )
        results.append(normalized)

    strict_effective = bool(request.strict_mode) and bool(results)
    if results:
        context_chunks = "\n\n".join(
            (
                f"[citation:{item['citation_id']}] "
                f"source={item.get('source', 'unknown')} "
                f"scope={item.get('context_scope', 'knowledge_base')}\n"
                f"{item['content']}"
            )
            for item in results
        )
        source_label = "上传文档与知识库" if document_results else "知识库"
        preamble = (
            f"【{source_label}上下文】下列为与问题相关的证据片段"
            "（有帮助时请引用并标注 [citation:x]）。\n"
            "若片段不足以完整回答，可结合通用知识补充，并区分资料与推断。\n"
        )
    else:
        context_chunks = "（本次未检索到相关知识库片段。）"
        preamble = (
            "【知识库上下文】未命中片段时，请基于通用知识与教学规范作答；勿编造未上传的专属材料。\n"
        )
    body = f"{preamble}\n{context_chunks}"
    if strict_effective:
        body += (
            "\n\n【严格模式】仅依据上述片段作答；关键结论须带 [citation:x]；"
            "证据不足则说明知识库证据不足。"
        )
    return SystemMessage(content=body), results


def _reasoning_chunk_text(chunk: Any) -> str:
    extras = getattr(chunk, "additional_kwargs", None) or {}
    for key in ("reasoning_content", "reasoning", "thinking"):
        value = extras.get(key)
        if isinstance(value, str) and value:
            return value
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(block.get("text") or "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _visible_chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(block.get("text") or "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _stream_delta(text: str, previous: str) -> tuple[str, str]:
    if not text:
        return "", previous
    if previous and text.startswith(previous):
        return text[len(previous) :], text
    return text, previous + text


def _stream_grounded_document_answer(
    request: ChatRequest,
    context_message: SystemMessage,
    rag_results: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    """Stream native model reasoning and answer channels in one grounded call."""
    started_at = time.perf_counter()
    first_token_at: float | None = None
    prompt = SystemMessage(
        content=(
            "你是严谨的大学课程助教。先在模型的思考通道中核对问题、"
            "上传文档证据和结论，再在回答通道输出清晰完整的中文讲解。"
            "思考通道直接从具体证据或待核对的关键点开始，禁止使用"
            "“好的，我现在需要”“首先我得”“用户希望我”之类的模板开场，"
            "也不要复述用户问题。"
            "回答必须以用户上传的文档为主要依据，关键结论标注 [citation:x]；"
            "不得编造文档没有的数据。使用 Markdown，所有数学公式必须严格使用"
            "行内 $...$ 或块级 $$...$$ LaTeX，禁止裸露 LaTeX、HTML 和 MathML。"
        )
    )
    llm = ChatModelFactory.create(
        temperature=min(float(request.temperature or 0.35), 0.45),
        max_tokens=min(max(int(request.max_tokens or 2048), 1024), 4096),
        top_p=request.top_p,
        top_k=request.top_k,
        reasoning=True,
    )
    reasoning_text = ""
    answer_text = ""
    previous_reasoning = ""
    previous_answer = ""

    for chunk in llm.stream(
        [prompt, context_message, HumanMessage(content=request.user_input)]
    ):
        extras = getattr(chunk, "additional_kwargs", None) or {}
        raw_reasoning = ""
        for key in ("reasoning_content", "reasoning", "thinking"):
            value = extras.get(key)
            if isinstance(value, str) and value:
                raw_reasoning = value
                break
        reasoning_delta, previous_reasoning = _stream_delta(
            raw_reasoning, previous_reasoning
        )
        if reasoning_delta:
            reasoning_text += reasoning_delta
            yield {"type": "reasoning_token", "content": reasoning_delta}

        answer_delta, previous_answer = _stream_delta(
            _visible_chunk_text(chunk), previous_answer
        )
        if answer_delta:
            if first_token_at is None:
                first_token_at = time.perf_counter()
            answer_text += answer_delta
            yield {"type": "token", "content": answer_delta}

    text = _normalize_answer_text(answer_text)
    if not text.strip():
        yield {
            "type": "error",
            "content": "模型完成了思考，但没有生成最终回答，请重试。",
        }
        return

    cited_ids = {
        int(value)
        for value in re.findall(r"\[citation:(\d+)\]", text, flags=re.I)
    }
    document_evidence = [
        item
        for item in rag_results
        if item.get("context_scope") == "uploaded_document"
    ]
    if not cited_ids:
        cited_ids = {
            int(item.get("citation_id") or 0)
            for item in document_evidence[:3]
            if int(item.get("citation_id") or 0) > 0
        }
    citations = _normalize_structured_citations(
        rag_results,
        [{"citation_id": citation_id} for citation_id in sorted(cited_ids)],
    )
    suggestions = _normalize_followups(request.user_input, text, [])
    latency_ms = max(1, round((time.perf_counter() - started_at) * 1000))
    ttft_ms = (
        max(1, round((first_token_at - started_at) * 1000))
        if first_token_at is not None
        else None
    )
    metrics = {
        "ttft_ms": ttft_ms,
        "latency_ms": latency_ms,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
        "estimated_tokens": False,
        "agent_hops": 1,
        "cache_hit": False,
        "rag_hit_count": len(rag_results),
        "tool_calls_count": 0,
        "route_trace": ["document_reasoning"],
    }
    yield {"type": "suggestions", "data": suggestions}
    yield {
        "type": "final",
        "content": text,
        "agent": "knowledge_mentor",
        "intent": "document_grounded_reasoning",
        "routing_reason": "当前上传文档直接讲解",
        "tool_calls": [],
        "requires_confirmation": False,
        "pending_action_id": None,
        "citations": citations,
        "confidence": "high" if citations else "medium",
        "grounding_mode": "rag" if citations else "general",
        "suggestions": suggestions,
        "metrics": metrics,
    }


def _stream_model_reasoning(
    request: ChatRequest, context_message: SystemMessage
) -> Iterator[dict[str, Any]]:
    """Stream an actual model analysis pass instead of scripted filler."""
    if not request.reasoning_enabled:
        return
    context = str(context_message.content or "")
    if len(context) > 6000:
        context = context[:6000] + "\n（证据片段已截断）"
    prompt = SystemMessage(
        content=(
            "你正在为学生问题生成可展示的“思考过程”。"
            "请真实分析当前问题与证据，按自然思路逐步推进：识别目标、"
            "检查材料、比较可能解释、核对结论。使用第一人称简洁中文，"
            "不要套用固定开场，不要提及系统、Agent、路由或提示词，"
            "不要提前输出完整最终答案。"
        )
    )
    llm = ChatModelFactory.create(
        temperature=0.35,
        max_tokens=min(max(int(request.max_tokens or 512), 256), 512),
        top_p=request.top_p,
        top_k=request.top_k,
        reasoning=True,
    )
    previous = ""
    for chunk in llm.stream(
        [prompt, context_message, HumanMessage(content=request.user_input)]
    ):
        text = _reasoning_chunk_text(chunk)
        if not text:
            continue
        if previous and text.startswith(previous):
            delta = text[len(previous) :]
            previous = text
        else:
            delta = text
            previous += text
        if delta:
            yield {"type": "reasoning_token", "content": delta}


def _rag_system_message(request: ChatRequest) -> SystemMessage:
    message, _ = _build_rag_context(request)
    return message


def _invoke_supervisor_llm(state: State) -> tuple[SupervisorDecision, bool]:
    """返回 (决策, 是否走了解析/调用失败兜底)。"""
    try:
        trim = _clip_messages_for_llm(state["messages"])
        supervisor_text = (
            SUPERVISOR_SYSTEM_PROMPT
            + "\n\n当前 task_breakdown 草稿（可覆盖）：\n"
            + (state.get("task_breakdown") or "（空）")
        )
        memory_context = (state.get("user_memory_context") or "").strip()
        if memory_context:
            supervisor_text += f"\n\n{memory_context}"
        current_file_id = (state.get("current_file_id") or "").strip()
        current_file_name = (state.get("current_file_name") or "").strip()
        if current_file_id:
            supervisor_text += (
                "\n\n【文件挂载上下文】"
                f"用户当前已挂载文件：《{current_file_name or current_file_id}》。"
                "若用户问题明显指向该文件（如总结论文、解释章节、定位细节），"
                "优先路由给 doc_researcher，并在 task_breakdown 中写明检索关键词。"
            )
        human_sys = SystemMessage(content=supervisor_text)
        messages = [human_sys, *trim]

        worker_cap = int(state.get("max_tokens") or settings.CHAT_DEFAULT_MAX_TOKENS)
        sup_cap = max(
            1024,
            min(worker_cap, int(settings.CHAT_SUPERVISOR_MAX_TOKENS)),
        )
        llm = ChatModelFactory.create(
            temperature=state.get("temperature") if state.get("temperature") is not None else 0.25,
            max_tokens=sup_cap,
        )
        try:
            structured = llm.with_structured_output(SupervisorDecision)
            decision = structured.invoke(messages)
            if isinstance(decision, SupervisorDecision):
                return decision, False
            if isinstance(decision, dict):
                try:
                    return SupervisorDecision.model_validate(decision), False
                except Exception:
                    pass
        except Exception:
            pass
        resp = llm.invoke(messages)
        return _parse_supervisor_decision_safe(str(resp.content or ""))
    except Exception:
        return _supervisor_fallback_decision(), True


def supervisor_node(state: State) -> dict[str, Any]:
    entries = state.get("supervisor_entries", 0) + 1
    thought_super = "【主管拆解】主管正在分析对话历史并决定下一步由哪位专员处理。"

    if entries > _MAX_SUPERVISOR_ENTRIES:
        return {
            "next_agent": "FINISH",
            "routing_reason": "已达到协作深度上限，结束派发并进入汇总。",
            "intermediate_steps": [
                thought_super,
                "【主管拆解】协作轮次已达上限，转入【汇总生成】阶段。",
            ],
            "supervisor_entries": entries,
            "supervisor_fallback_streak": 0,
        }

    fa = state.get("force_agent")
    if (
        fa
        and fa in _WORKERS
        and not state.get("force_agent_consumed")
    ):
        label = AGENT_CONFIG[fa]["label"]
        return {
            "next_agent": fa,
            "routing_reason": "用户指定由该专员优先处理。",
            "intermediate_steps": [
                thought_super,
                f"【主管拆解】按用户指定移交 → {label}（{fa}）。",
            ],
            "supervisor_entries": entries,
            "force_agent_consumed": True,
            "supervisor_fallback_streak": 0,
            "agent_route_trace": [fa],
        }

    last_worker = str(state.get("collaboration_last_worker") or "").strip()
    ruled = _rule_based_route(state)
    if ruled and not last_worker:
        agent_name, reason = ruled
        label = AGENT_CONFIG[agent_name]["label"]
        return {
            "next_agent": agent_name,
            "routing_reason": reason,
            "task_breakdown": state.get("task_breakdown", ""),
            "intent": "supervisor_route",
            "intermediate_steps": [
                thought_super,
                f"【主管拆解】下一步：{label}（{agent_name}）。",
            ],
            "supervisor_entries": entries,
            "supervisor_fallback_streak": 0,
            "agent_route_trace": [agent_name],
        }

    decision, used_fallback = _invoke_supervisor_llm(state)
    prev_fb = int(state.get("supervisor_fallback_streak") or 0)
    streak = prev_fb + 1 if used_fallback else 0

    na = decision.next_agent
    routing_reason = (decision.routing_reason or "").strip()
    task_bd = decision.task_breakdown.strip()

    if used_fallback and streak >= _MAX_SUPERVISOR_FALLBACK_STREAK:
        na = "FINISH"
        routing_reason = (
            "主管路由结构化输出连续解析失败，已强制结束协作并进入汇总；"
            "将基于当前对话中已有专员发言生成答复。"
        )

    if last_worker and na == last_worker:
        na = "FINISH"
        routing_reason = (
            f"{AGENT_CONFIG[last_worker]['label']}已完成本轮任务，"
            "避免重复派发并进入汇总。"
        )

    if na not in _WORKERS and na != "FINISH":
        na = "FINISH"
    label = (
        AGENT_CONFIG[na]["label"]
        if na in _WORKERS
        else "结束协作"
    )
    step = f"【主管拆解】下一步：{'【汇总生成】' if na == 'FINISH' else f'{label}（{na}）'}"
    if task_bd:
        step += f"\n子任务清单：{task_bd}"

    return {
        "next_agent": na,
        "task_breakdown": task_bd or state.get("task_breakdown", ""),
        "routing_reason": routing_reason,
        "intent": "supervisor_route",
        "intermediate_steps": [thought_super, step],
        "supervisor_entries": entries,
        "supervisor_fallback_streak": streak,
        "agent_route_trace": [na] if na in _WORKERS else [],
    }


def finalize_node(state: State) -> dict[str, Any]:
    llm = ChatModelFactory.create(
        temperature=state.get("temperature"),
        max_tokens=state.get("max_tokens"),
    )
    msgs = state["messages"]
    current_q = _latest_human_question(msgs).strip()
    if not current_q:
        current_q = "（未解析到当前学生问题，请根据历史与材料尽量作答。）"
    is_selection_query = _is_selection_query_text(current_q)
    current_topic = _pick_topic_from_question(current_q)

    history_lines = _recent_public_history(msgs, max_turns=4)
    recent_history = "\n".join(history_lines) if history_lines else "（暂无历史对话）"
    rag_ex = _rag_system_excerpt(msgs, max_chars=3500)
    worker_mat = _collect_worker_outputs_for_finalize(msgs, max_total=12000)

    sys_chunks: list[str] = [FINALIZE_SYSTEM_PROMPT]
    resolved = (state.get("resolved_system_prompt") or "").strip()
    if resolved:
        sys_chunks.append(f"【全局辅导偏好】\n{resolved}")
    memory_context = (state.get("user_memory_context") or "").strip()
    if memory_context:
        sys_chunks.append(memory_context)
    if current_topic != "这个知识点":
        sys_chunks.append(
            f"【当前主题锁定】学生当前问题主题是「{current_topic}」。"
            "最终 answer 必须优先围绕这个主题组织；"
            "知识库里出现的相邻主题只能作为补充背景，不能把回答主体替换成其它知识点。"
        )
    if is_selection_query:
        sys_chunks.append(
            "【划词唤醒回答要求】本次是学生在课堂内容中划词后的即时解答。"
            "最终 answer 正文必须是完整课堂讲解，不能压缩成一段短答；"
            "除非学生明确要求总结，否则至少覆盖概念、机制、例子、易错点和学习建议；"
            "若涉及数据库索引，须保证术语严谨，避免把 B 树/B+ 树误写成二叉搜索树。"
        )
    rr = (state.get("routing_reason") or "").strip()
    if rr and ("强制" in rr or "解析失败" in rr or "连续" in rr):
        sys_chunks.append(
            "【补充】本次为异常收束，请在不暴露系统内部错误的前提下完成最终回答。"
        )
    sys = SystemMessage(content="\n\n".join(sys_chunks))

    human_parts = [
        f"【前情提要（最近公开对话）】\n{recent_history}",
        f"【当前学生问题】\n{current_q}",
    ]
    if rag_ex:
        human_parts.append(f"【知识库参考摘要】\n{rag_ex}")
    human_parts.append(
        "【当前专员研究资料】（用于提炼，不要原样复读内部思考）\n"
        + (worker_mat or "（本轮暂无专员正文，请直接基于问题与上下文作答。）")
    )
    citation_candidates = build_citation_candidates(state.get("rag_results") or [])
    human_parts.append(f"【可引用证据候选】\n{citation_candidates}")
    human = HumanMessage(content="\n\n".join(human_parts))

    def _fallback_from_recent_worker_messages(all_msgs: list[Any]) -> str:
        """汇总模型空输出时，回退到最近一条可见专员正文。"""
        for m in reversed(all_msgs):
            if not isinstance(m, AIMessage):
                continue
            text = _strip_think_blocks_from_text(_strict_ai_content_for_user(m))
            t = (text or "").strip()
            if not t:
                continue
            if "汇总阶段未得到可见正文" in t:
                continue
            return t
        return ""

    structured_prompt_text = (
        "你必须输出结构化结果，字段包括 answer, confidence, grounding_mode, citations, follow_ups。\n"
        "confidence 只能是 high / medium / low；grounding_mode 只能是 rag / general / tool / mixed。\n"
        "如果使用知识库证据，citations 中必须引用上面候选里的 citation_id；"
        "不要编造不存在的 citation_id。\n"
        "follow_ups 必须正好 3 条，必须是学生会点击后直接发给你的下一轮问题；"
        "每条都要像学生自然追问，不要写成“请问您是否需要...”这类面向用户的提示，"
        "也不要刻意用“我，”开头。"
        "普通伴学问题若属于讲解、教程、语法、例题或学习指导，answer 不得只给短定义；"
        "除非学生明确要求简短，否则建议 700-1100 个中文字符。"
        "如果学生问题中有明确主题，answer 和 follow_ups 都必须围绕该主题，"
        "不能被知识库片段中的相邻主题带偏。"
        "如果学生同时要求知识点讲解和练习题，answer 必须先系统讲解，再提供由浅入深练习题和提示。"
        "所有数学、算法复杂度或数据库符号公式必须使用标准 LaTeX，行内 $...$、块级 $$...$$；"
        "禁止输出 HTML/XML/MathML 标签，也禁止输出 class=\"math\" 之类的属性文本。"
    )
    if is_selection_query:
        structured_prompt_text += (
            "\n本次是划词唤醒场景，answer 字段必须优先满足课堂讲解长度："
            "建议 500-800 个中文字符，使用小标题或列表，不要只输出简短定义；"
            "数据库索引相关内容必须区分多路平衡树与二叉搜索树。"
        )
    structured_prompt = SystemMessage(content=structured_prompt_text)
    citations: list[dict[str, Any]] = []
    confidence = "medium"
    grounding_mode = "general"
    follow_ups: list[str] = []

    try:
        raw_msg = None
        payload: StructuredAnswerPayload | None = None
        try:
            structured = llm.with_structured_output(StructuredAnswerPayload)
            structured_result = structured.invoke([sys, structured_prompt, human])
            if isinstance(structured_result, StructuredAnswerPayload):
                payload = structured_result
            elif isinstance(structured_result, dict):
                payload = StructuredAnswerPayload.model_validate(structured_result)
        except Exception:
            payload = None
        if payload is None:
            raw_msg = llm.invoke([sys, structured_prompt, human])
            payload = parse_structured_payload(_strict_ai_content_for_user(raw_msg))
        if payload:
            clean = _strip_think_blocks_from_text((payload.answer or "").strip())
            if looks_like_broken_math_markup(clean):
                clean = _fallback_from_recent_worker_messages(msgs)
                if not clean or looks_like_broken_math_markup(clean):
                    raise ValueError("structured answer contained broken math markup")
            clean = _expand_final_answer_if_needed(
                llm,
                current_q=current_q,
                answer=clean,
                rag_excerpt=rag_ex,
                worker_material=worker_mat,
            )
            citations = _normalize_structured_citations(
                state.get("rag_results") or [],
                [
                    item.model_dump() if hasattr(item, "model_dump") else item
                    for item in payload.citations
                ],
            )
            confidence = normalize_confidence(payload.confidence)
            grounding_mode = normalize_grounding_mode(
                payload.grounding_mode,
                has_citations=bool(citations),
            )
            if clean:
                llm_followups = _llm_followup_suggestions(current_q, clean)
                follow_ups = _normalize_followups(
                    current_q,
                    clean,
                    [*llm_followups, *list(payload.follow_ups or [])],
                )
                msg = AIMessage(content=clean, name="final_answer")
            else:
                raw_fallback = (
                    _strict_ai_content_for_user(raw_msg)
                    if raw_msg is not None
                    else ""
                )
                clean = _strip_think_blocks_from_text(raw_fallback)
                clean = _expand_final_answer_if_needed(
                    llm,
                    current_q=current_q,
                    answer=clean,
                    rag_excerpt=rag_ex,
                    worker_material=worker_mat,
                )
                if clean:
                    llm_followups = _llm_followup_suggestions(current_q, clean)
                    follow_ups = _normalize_followups(
                        current_q,
                        clean,
                        [*llm_followups, *list(payload.follow_ups or [])],
                    )
                    msg = AIMessage(content=clean, name="final_answer")
                else:
                    raise ValueError("structured answer empty")
        else:
            raise ValueError("structured answer parse failed")
    except Exception as e:
        fallback_text = _fallback_from_recent_worker_messages(msgs)
        if fallback_text:
            fallback_text = _expand_final_answer_if_needed(
                llm,
                current_q=current_q,
                answer=fallback_text,
                rag_excerpt=rag_ex,
                worker_material=worker_mat,
            )
            msg = AIMessage(content=fallback_text, name="final_answer")
        else:
            msg = AIMessage(
                content=(
                    "汇总阶段暂时无法完成（常见于上下文过长或服务限制）。请尝试缩短问题或开启新对话。"
                    f"\n（详情：{str(e)[:400]}）"
                ),
                name="final_answer",
            )
        confidence = "low"
        grounding_mode = "general"
        llm_followups = _llm_followup_suggestions(current_q, msg.content)
        follow_ups = _normalize_followups(
            current_q,
            msg.content,
            llm_followups or _default_suggestions(current_q),
        )
    if state.get("current_file_id") and not citations:
        document_evidence = [
            item
            for item in state.get("rag_results") or []
            if item.get("context_scope") == "uploaded_document"
        ][:3]
        citations = _normalize_structured_citations(
            state.get("rag_results") or [],
            [{"citation_id": item.get("citation_id")} for item in document_evidence],
        )
        if citations:
            grounding_mode = "rag"
    return {
        "messages": [msg],
        "selected_agent": "supervisor",
        "intent": "final_summary",
        "routing_reason": state.get("routing_reason", "") or "协作汇总",
        "intermediate_steps": [
            "【汇总生成】主管正在综合各专员发言，生成面向学生的最终答复。"
        ],
        "final_citations": citations,
        "final_confidence": confidence,
        "final_grounding_mode": grounding_mode,
        "final_follow_ups": follow_ups,
    }


_WORKER_DONE_TAG: dict[str, str] = {
    "code_tutor": "【代码验证】代码导师本轮处理完成，结果已同步至主管。",
    "knowledge_mentor": "【学科讲解】学科知识讲师本轮处理完成，已同步至主管。",
    "planner": "【学习规划】学习规划师本轮处理完成，已同步至主管。",
    "analyst": "【学情分析】学习分析师本轮处理完成，已同步至主管。",
    "doc_researcher": "【文档研究】文档研究员本轮处理完成，已同步至主管。",
    "quiz_master": "【主动测验】测验官本轮处理完成，已同步至主管。",
    "profile_agent": "【学习画像】画像分析师本轮处理完成，已同步至主管。",
    "retrieval_agent": "【证据检索】课程证据检索员本轮处理完成，已同步至主管。",
    "web_research_agent": "【联网研究】联网研究员本轮处理完成，已同步至主管。",
    "tutor_agent": "【多模态辅导】辅导教师本轮处理完成，已同步至主管。",
    "grading_agent": "【练习批改】批改教师本轮处理完成，已同步至主管。",
    "safety_review_agent": "【事实审查】事实与安全审查员本轮处理完成，已同步至主管。",
}


def _team_member_prefix(agent: str) -> str:
    label = AGENT_CONFIG[agent]["label"]
    return (
        f"你是团队成员「{label}」（{agent}）。主管已将你加入协作线程。\n"
        "请基于对话与知识库上下文完成本轮任务，将结论写入助手消息；"
        "保持专业、简洁，勿编造未给出的数据。"
    )


def _invoke_worker(state: State, agent: str) -> dict[str, Any]:
    role_prompt = AGENT_CONFIG[agent]["prompt"]
    merged = f"{_team_member_prefix(agent)}\n\n{role_prompt}"
    resolved = (state.get("resolved_system_prompt") or "").strip()
    if resolved:
        merged = f"{resolved}\n\n{merged}"
    memory_context = (state.get("user_memory_context") or "").strip()
    if memory_context:
        merged = f"{memory_context}\n\n{merged}"
    sys = SystemMessage(content=merged)
    llm = get_llm(
        agent,
        enable_tools=True,
        active_tools=state.get("active_tools"),
        rag_user_id=state.get("rag_user_id"),
        rag_is_admin=bool(state.get("rag_is_admin")),
        rag_k=int(state.get("rag_top_k") or 4),
        thread_id=str(state.get("current_thread_id") or "default"),
        current_file_id=state.get("current_file_id"),
        temperature=state.get("temperature"),
        max_tokens=state.get("max_tokens"),
        top_p=state.get("top_p"),
        top_k=state.get("top_k"),
    )
    clipped = _clip_messages_for_llm(state["messages"])
    try:
        ai_msg = llm.invoke([sys, *clipped])
    except Exception as e:
        ai_msg = AIMessage(
            content=(
                f"本专员（{AGENT_CONFIG[agent]['label']}）处理时出错，已跳过本轮模型调用。"
                f" 可稍后重试或缩短问题。详情：{str(e)[:500]}"
            )
        )
    return {
        "messages": [ai_msg],
        "selected_agent": agent,
        "intent": f"worker_{agent}",
        "collaboration_last_worker": agent,
        "intermediate_steps": [
            _WORKER_DONE_TAG.get(
                agent,
                f"【专员】{AGENT_CONFIG[agent]['label']} 本轮处理完成，已同步至主管。",
            )
        ],
    }


def _worker_tools_or_supervisor(state: State) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "supervisor"


def _supervisor_branch(state: State) -> str:
    n = (state.get("next_agent") or "FINISH").strip()
    if n == "FINISH":
        return "finalize"
    if n in _WORKERS:
        return n
    return "finalize"


def _make_worker_node(agent_name: str):
    def _run(state: State) -> dict[str, Any]:
        return _invoke_worker(state, agent_name)

    return _run


def _build_supervisor_graph(
    active_tools: list[str] | None = None,
    *,
    rag_user_id: str | None = None,
    rag_is_admin: bool = False,
    rag_k: int = 4,
    thread_id: str = "default",
    current_file_id: str | None = None,
):
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("finalize", finalize_node)

    worker_specs = [
        ("code_tutor", "code_tutor_tools"),
        ("knowledge_mentor", "knowledge_mentor_tools"),
        ("planner", "planner_tools"),
        ("analyst", "analyst_tools"),
        ("doc_researcher", "doc_researcher_tools"),
        ("quiz_master", "quiz_master_tools"),
        ("profile_agent", "profile_agent_tools"),
        ("retrieval_agent", "retrieval_agent_tools"),
        ("web_research_agent", "web_research_agent_tools"),
        ("tutor_agent", "tutor_agent_tools"),
        ("grading_agent", "grading_agent_tools"),
        ("safety_review_agent", "safety_review_agent_tools"),
    ]
    for name, tools_node in worker_specs:
        builder.add_node(name, _make_worker_node(name))
        tlist = get_tools_for_agent(
            name,
            active_tools,
            rag_user_id=rag_user_id,
            rag_is_admin=rag_is_admin,
            rag_k=rag_k,
            thread_id=thread_id,
            current_file_id=current_file_id,
        )
        builder.add_node(tools_node, ToolNode(tools=tlist))
        builder.add_conditional_edges(
            name,
            _worker_tools_or_supervisor,
            {"tools": tools_node, "supervisor": "supervisor"},
        )
        builder.add_edge(tools_node, name)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _supervisor_branch,
        {
            "code_tutor": "code_tutor",
            "knowledge_mentor": "knowledge_mentor",
            "planner": "planner",
            "analyst": "analyst",
            "doc_researcher": "doc_researcher",
            "quiz_master": "quiz_master",
            "profile_agent": "profile_agent",
            "retrieval_agent": "retrieval_agent",
            "web_research_agent": "web_research_agent",
            "tutor_agent": "tutor_agent",
            "grading_agent": "grading_agent",
            "safety_review_agent": "safety_review_agent",
            "finalize": "finalize",
        },
    )
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=MemorySaver())


def _build_selection_prompt(request: ChatRequest) -> str:
    selected = (request.selected_text or "").strip()
    context = (request.surrounding_context or "").strip()
    module = (request.course_module or "当前课程").strip()
    video_time = (request.video_time or "").strip()
    action_hint = (request.system_prompt or "").strip()
    if not selected:
        return request.user_input

    prompt = (
        f"学生在学习《{module}》时选中了“{selected}”。\n"
        f"上下文片段：{context or '（无）'}\n"
    )
    if video_time:
        prompt += f"当前视频时间点：{video_time}\n"
    if action_hint:
        prompt += f"学生点击的划词操作要求：{action_hint}\n"

    is_summary_mode = bool(re.search(r"(总结|概括|要点)", action_hint))
    if is_summary_mode:
        prompt += (
            "请按课堂笔记复盘的方式回答：先给一句总览，再给 4-6 条要点；"
            "每条要点都补充必要解释和学习提醒，避免只输出一句短答。"
        )
    else:
        prompt += (
            "请按课堂讲解模式输出较完整的一段答复，建议 450-800 字。"
            "必须覆盖：1）概念定位；2）核心机制或原理；3）贴近课堂的例子；"
            "4）常见误区或实践价值；5）学生下一步如何理解。"
            "可以用 Markdown 小标题或列表组织，但不要只给一小段概括，"
            "也不要以“是否还需要我继续解释”作为正文结尾。"
            "如果涉及数据库索引，请准确区分 B 树/B+ 树这类多路平衡搜索树与二叉搜索树，"
            "不要把 B 树说成 BST。"
        )
    prompt += (
        "请用引导式、教学友好的口吻回答，直接给学生可阅读的内容。"
    )
    return prompt


def _should_use_semantic_cache(request: ChatRequest) -> bool:
    """划词和教学讲解类问题不走语义缓存，避免旧模板/旧长度答案被复用。"""
    if request.selected_text or request.current_file_id or request.image_base64_list:
        return False
    if _SUBSTANTIVE_TEACHING_HINT_RE.search(request.user_input or ""):
        return False
    return not bool(request.prior_turns or [])


def resolve_stream_user_text_for_storage(request: ChatRequest) -> str:
    """与 stream/协作图一致的用户侧文本，用于落库 thread 历史。"""
    if request.selected_text:
        return _build_selection_prompt(request)
    return (request.user_input or "").strip()


def _requires_hitl(
    intent: str,
    user_input: str,
    task_breakdown: str = "",
    last_worker: str = "",
) -> bool:
    if (last_worker or "") != "planner":
        return False
    blob = f"{user_input or ''}\n{task_breakdown or ''}".lower()
    return any(k in blob for k in ["进度", "复习", "计划", "落后", "冲刺"])


def _tool_status_text(
    active_tools: list[str] | None,
) -> tuple[list[str], list[str]]:
    allowed = sorted({k for keys in TOOL_KEYS_BY_AGENT.values() for k in keys})
    active = set(active_tools or ["knowledge_base", "code_sandbox"])
    enabled = [k for k in allowed if k in active]
    disabled = [k for k in allowed if k not in active]
    return enabled, disabled


def _resolve_image_context(request: ChatRequest):
    from app.services.vision_client import VisionCallResult, build_chat_image_context

    images = [img for img in (request.image_base64_list or []) if img]
    if not images:
        return "", VisionCallResult(status="empty")
    return build_chat_image_context(images, user_hint=request.user_input or "")


def _build_image_context(request: ChatRequest) -> str:
    context, _ = _resolve_image_context(request)
    return context


def _normalize_structured_citations(
    rag_results: list[dict[str, Any]],
    citations: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    by_id = {
        int(item.get("citation_id") or 0): item
        for item in rag_results or []
        if int(item.get("citation_id") or 0) > 0
    }
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in citations or []:
        citation_id = int(raw.get("citation_id") or 0)
        if citation_id <= 0 or citation_id in seen:
            continue
        base = by_id.get(citation_id)
        if not base:
            continue
        seen.add(citation_id)
        out.append(
            {
                "citation_id": citation_id,
                "source": str(base.get("source") or "unknown"),
                "file_id": str((base.get("metadata") or {}).get("file_id") or ""),
                "chunk_id": base.get("chunk_id"),
                "score": float(base.get("score") or 0.0),
                "snippet": str(raw.get("snippet") or base.get("content") or "")[:220],
                "reason": str(raw.get("reason") or "").strip(),
                "relevance_score": float(raw.get("relevance_score") or 0.0),
            }
        )
    return out


def _agent_hops_from_trace(trace: list[str], *, cache_hit: bool) -> int:
    if cache_hit:
        return 1
    worker_hops = len([item for item in trace if item])
    # supervisor 启动 + 专员流转 + 最终汇总
    return max(2, worker_hops + 2)


def _build_metrics(
    *,
    messages: list[Any],
    route_trace: list[str],
    cache_hit: bool,
    rag_hit_count: int,
    tool_calls_count: int,
    ttft_ms: int | None = None,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    usage = collect_usage_from_messages(messages)
    return {
        "ttft_ms": ttft_ms,
        "latency_ms": latency_ms,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "estimated_tokens": bool(usage.get("estimated")),
        "agent_hops": _agent_hops_from_trace(route_trace, cache_hit=cache_hit),
        "cache_hit": cache_hit,
        "rag_hit_count": rag_hit_count,
        "tool_calls_count": tool_calls_count,
        "route_trace": route_trace,
    }


def _initial_state(
    request: ChatRequest,
    user_text: str,
    *,
    image_context: str | None = None,
    rag_context: tuple[SystemMessage, list[dict[str, Any]]] | None = None,
) -> State:
    rag_msg, rag_results = rag_context or _build_rag_context(request)
    preset = resolve_system_prompt(request.prompt_key, request.system_prompt)
    memory_context = _load_user_memory_context(request.user_id)
    if image_context is None:
        image_context = _build_image_context(request)
    messages: list = [rag_msg]
    if image_context:
        messages.append(SystemMessage(content=image_context))
    for turn in request.prior_turns or []:
        u = (turn.get("user") or "").strip()
        a = (turn.get("assistant") or "").strip()
        if u:
            messages.append(HumanMessage(content=u))
        if a:
            messages.append(AIMessage(content=a))
    messages.append(HumanMessage(content=user_text))
    return cast(
        State,
        {
            "messages": messages,
            "next_agent": "",
            "task_breakdown": "",
            "intermediate_steps": [],
            "selected_agent": "code_tutor",
            "intent": "",
            "routing_reason": "",
            "resolved_system_prompt": preset or "",
            "force_agent": request.force_agent,
            "force_agent_consumed": False,
            "active_tools": request.active_tools,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "supervisor_entries": 0,
            "supervisor_fallback_streak": 0,
            "strict_mode": bool(request.strict_mode),
            "collaboration_last_worker": "",
            "rag_user_id": request.user_id,
            "rag_is_admin": bool(request.is_admin),
            "rag_top_k": int(request.rag_k),
            "current_thread_id": str(request.thread_id),
            "current_file_id": request.current_file_id,
            "current_file_name": request.file_name or "",
            "image_context": image_context,
            "tool_mode": request.tool_mode,
            "user_memory_context": memory_context,
            "rag_results": rag_results,
            "final_citations": [],
            "final_confidence": "medium",
            "final_grounding_mode": "general",
            "final_follow_ups": [],
            "agent_route_trace": [],
        },
    )


def chat_service(request: ChatRequest) -> ChatResponse:
    request = _with_resolved_max_tokens(request)
    if request.selected_text:
        request.user_input = _build_selection_prompt(request)

    if request.force_cache:
        demo = build_demo_chat_response(request.user_input)
        demo.metrics = {
            "ttft_ms": 1,
            "latency_ms": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "estimated_tokens": False,
            "agent_hops": 1,
            "cache_hit": True,
            "rag_hit_count": 0,
            "tool_calls_count": 0,
            "route_trace": ["demo_mode"],
        }
        return demo

    cache_hit = (
        chat_semantic_cache.get(request.user_input)
        if _should_use_semantic_cache(request)
        else None
    )
    if cache_hit:
        cached_text = cache_hit.answer
        return ChatResponse(
            response=cached_text,
            tool_calls=[],
            agent="supervisor",
            intent="semantic_cache",
            routing_reason=f"语义缓存命中（hit_count={cache_hit.hit_count}）",
            thoughts=["⚡ 语义缓存命中，直接返回历史高相似答案。"],
            confidence="high",
            grounding_mode="general",
            suggestions=_normalize_followups(request.user_input, cached_text, []),
            metrics={
                "ttft_ms": 0,
                "latency_ms": 0,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "estimated_tokens": False,
                "agent_hops": 1,
                "cache_hit": True,
                "rag_hit_count": 0,
                "tool_calls_count": 0,
                "route_trace": ["semantic_cache"],
            },
        )

    graph = _build_supervisor_graph(
        request.active_tools,
        rag_user_id=request.user_id,
        rag_is_admin=request.is_admin,
        rag_k=int(request.rag_k),
        thread_id=str(request.thread_id),
        current_file_id=request.current_file_id,
    )
    thread_config = {"configurable": {"thread_id": request.thread_id}}
    initial = _initial_state(request, request.user_input)
    started_at = time.perf_counter()

    result = graph.invoke(initial, config=thread_config)
    final_text = _last_meaningful_assistant_text(result.get("messages") or [])
    final_text, inline_suggestions = _split_suggestions(final_text)
    thoughts = list(result.get("intermediate_steps") or [])
    tool_calls = collect_tool_calls(result.get("messages", []))
    route_trace = list(result.get("agent_route_trace") or [])
    suggestions = _normalize_followups(
        request.user_input,
        final_text,
        list(result.get("final_follow_ups") or []) or inline_suggestions,
    )
    latency_ms = max(1, round((time.perf_counter() - started_at) * 1000))
    citations = list(result.get("final_citations") or [])
    response = ChatResponse(
        response=final_text,
        tool_calls=tool_calls,
        agent=result.get("selected_agent", "supervisor"),
        intent=result.get("intent", "collaborative_supervisor"),
        routing_reason=result.get("routing_reason", "") or "协作完成",
        thoughts=thoughts,
        citations=citations,
        confidence=normalize_confidence(result.get("final_confidence")),
        grounding_mode=normalize_grounding_mode(
            result.get("final_grounding_mode"),
            has_citations=bool(citations),
        ),
        suggestions=suggestions,
        metrics=_build_metrics(
            messages=result.get("messages") or [],
            route_trace=route_trace,
            cache_hit=False,
            rag_hit_count=len(result.get("rag_results") or []),
            tool_calls_count=len(tool_calls),
            ttft_ms=latency_ms,
            latency_ms=latency_ms,
        ),
    )
    if _requires_hitl(
        response.intent,
        request.user_input,
        result.get("task_breakdown") or "",
        result.get("collaboration_last_worker") or "",
    ):
        action = pending_action_store.create(
            user_id=request.user_id or "anonymous",
            thread_id=request.thread_id,
            plan_text=response.response,
        )
        response.requires_confirmation = True
        response.pending_action_id = action.action_id
        response.thoughts = [
            *response.thoughts,
            "⏸ 已触发 HITL，请用户确认后写入日历。",
        ]

    if _should_use_semantic_cache(request):
        chat_semantic_cache.put(request.user_input, response.response)
    return response


def stream_chat_events(request: ChatRequest):
    request = _with_resolved_max_tokens(request)
    user_input = request.user_input
    if request.selected_text:
        user_input = _build_selection_prompt(request)
    req = request.model_copy(update={"user_input": user_input})
    started_at = time.perf_counter()
    first_token_at: float | None = None
    reasoning_queue: list[dict[str, Any]] = []
    reasoning = ReasoningStreamController(req.user_input)
    emitter_token = set_reasoning_emitter(reasoning_queue.append)
    controller_token = set_reasoning_controller(reasoning)

    def _flush_reasoning():
        yield from _drain_reasoning_queue(reasoning_queue)

    try:
        if req.force_cache:
            yield from _stream_thought_events(
                "【演示模式】已启用稳定兜底回答。",
                "demo_mode",
                user_visible=False,
            )
            demo = build_demo_chat_response(req.user_input)
            demo_text = _normalize_answer_text(demo.response)
            for chunk in _stream_answer_tokens(demo_text):
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                yield chunk
            yield {"type": "suggestions", "data": demo.suggestions}
            yield {
                "type": "final",
                "content": demo_text,
                "agent": demo.agent,
                "intent": demo.intent,
                "routing_reason": demo.routing_reason,
                "tool_calls": demo.tool_calls,
                "requires_confirmation": False,
                "pending_action_id": None,
                "citations": demo.citations,
                "confidence": demo.confidence,
                "grounding_mode": demo.grounding_mode,
                "suggestions": demo.suggestions,
                "metrics": demo.metrics,
            }
            return

        enabled_tools, disabled_tools = _tool_status_text(req.active_tools)
        yield from _stream_thought_events(
            "【流水线】多智能体协作已启动（Supervisor + 专员 + 汇总）。",
            "pipeline_start",
            user_visible=False,
        )
        yield from _stream_thought_events(
            "【知识检索】已根据当前问题检索知识库并将上下文注入协作线程（首条系统消息）。",
            "kb_inject",
            user_visible=False,
        )
        if req.active_tools is not None:
            yield from _stream_thought_events(
                f"【工具策略】启用工具：{enabled_tools or ['none']}；已关闭：{disabled_tools or ['none']}",
                "tool_policy",
                user_visible=False,
            )
            if "web_search" in enabled_tools:
                yield from _stream_thought_events(
                    "【联网搜索】本轮允许联网搜索；最终回答会区分课程资料、联网补充和模型推断。",
                    "web_policy",
                    user_visible=False,
                )
            if not enabled_tools:
                yield from _stream_thought_events(
                    "【工具策略】当前过滤后无可用工具，专员将仅依赖模型能力。",
                    "tool_policy",
                    user_visible=False,
                )

        rag_context = _build_rag_context(req)
        yield from _flush_reasoning()
        if req.current_file_id and req.reasoning_enabled:
            yield from _stream_grounded_document_answer(
                req,
                rag_context[0],
                rag_context[1],
            )
            return
        if req.reasoning_enabled:
            try:
                yield from _stream_model_reasoning(req, rag_context[0])
            except Exception as exc:
                if req.debug_mode:
                    yield {
                        "type": "thought",
                        "content": f"真实思考流暂不可用：{str(exc)[:240]}",
                        "stage": "reasoning_error",
                    }

        cache_hit = (
            chat_semantic_cache.get(req.user_input)
            if _should_use_semantic_cache(req)
            else None
        )
        if cache_hit:
            yield from _stream_thought_events(
                "【流水线】语义缓存命中，跳过协作图执行。",
                "cache",
                user_visible=False,
            )
            text = _normalize_answer_text(cache_hit.answer)
            for chunk in _stream_answer_tokens(text):
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                yield chunk
            sug = _normalize_followups(req.user_input, text, [])
            yield {"type": "suggestions", "data": sug}
            yield {
                "type": "final",
                "content": text,
                "agent": "supervisor",
                "intent": "semantic_cache",
                "routing_reason": "语义缓存",
                "tool_calls": [],
                "requires_confirmation": False,
                "pending_action_id": None,
                "citations": [],
                "confidence": "high",
                "grounding_mode": "general",
                "metrics": {
                    "ttft_ms": 0,
                    "latency_ms": 0,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                    "estimated_tokens": False,
                    "agent_hops": 1,
                    "cache_hit": True,
                    "rag_hit_count": 0,
                    "tool_calls_count": 0,
                    "route_trace": ["semantic_cache"],
                },
            }
            return

        graph = _build_supervisor_graph(
            req.active_tools,
            rag_user_id=req.user_id,
            rag_is_admin=req.is_admin,
            rag_k=int(req.rag_k),
            thread_id=str(req.thread_id),
            current_file_id=req.current_file_id,
        )
        thread_config = {"configurable": {"thread_id": str(req.thread_id)}}
        image_context_str = ""
        vision_meta = None
        if req.image_base64_list:
            image_context_str, vision_meta = _resolve_image_context(req)
            if vision_meta is not None and (vision_meta.text or "").strip():
                reasoning.on_vision((vision_meta.text or "")[:160])
                yield from _flush_reasoning()
            if req.debug_mode and vision_meta is not None:
                summary = (vision_meta.text or "")[:160].replace("\n", " ")
                yield from _stream_thought_events(
                    (
                        f"【视觉识别】status={vision_meta.status} source={vision_meta.source or 'n/a'} "
                        f"model={vision_meta.model or 'n/a'} fields={vision_meta.field_summary or {}} "
                        f"summary={summary or 'empty'}"
                    ),
                    "vision_status",
                    user_visible=False,
                )
        initial = _initial_state(
            req,
            req.user_input,
            image_context=image_context_str or None,
            rag_context=rag_context,
        )

        final_state: dict | None = None
        last_values_state: dict | None = None
        emitted_tool_nodes: set[str] = set()
        try:
            try:
                stream_iter = graph.stream(
                    initial,
                    config=thread_config,
                    stream_mode=["updates", "values"],
                )
            except TypeError:
                stream_iter = graph.stream(
                    initial, config=thread_config, stream_mode="updates"
                )

            for event in stream_iter:
                mode, chunk = _normalize_graph_stream_event(event)
                if mode == "values" and isinstance(chunk, dict):
                    last_values_state = chunk
                    continue
                if mode != "updates" or not isinstance(chunk, dict):
                    continue
                for node_name, data in chunk.items():
                    if not isinstance(node_name, str):
                        continue
                    if node_name.endswith("_tools") and node_name not in emitted_tool_nodes:
                        emitted_tool_nodes.add(node_name)
                        yield from _stream_thought_events(
                            _TOOL_NODE_PIPELINE_MSG.get(
                                node_name,
                                "【工具执行】正在运行后端工具节点。",
                            ),
                            "tool_run",
                            user_visible=False,
                        )
                    if isinstance(data, dict):
                        for s in data.get("intermediate_steps") or []:
                            step = str(s)
                            yield from reasoning.from_intermediate_step(step)
                            yield {"type": "thought", "content": step}
                yield from _flush_reasoning()

            final_state = last_values_state
            if final_state is None:
                try:
                    snap = graph.get_state(thread_config)
                    if snap is not None and getattr(snap, "values", None) is not None:
                        final_state = dict(snap.values)
                except Exception:
                    final_state = None
        except Exception as exc:
            yield {"type": "error", "content": f"处理失败：{exc}"}
            return

        if not final_state:
            yield {"type": "error", "content": "协作图未返回状态"}
            return

        msgs = final_state.get("messages") or []
        text = _normalize_answer_text(_last_meaningful_assistant_text(msgs))
        text, suggestions = _split_suggestions(text)
        if not (text or "").strip():
            yield {
                "type": "error",
                "content": "协作图已结束但未生成可展示的助手正文，请重试或检查模型输出。",
            }
            return

        if _should_use_semantic_cache(req):
            chat_semantic_cache.put(req.user_input, text)

        for chunk in _stream_answer_tokens(text):
            if first_token_at is None:
                first_token_at = time.perf_counter()
            yield chunk
        dynamic_suggestions = _normalize_followups(
            req.user_input,
            text,
            list(final_state.get("final_follow_ups") or []) or suggestions,
        )
        yield {"type": "suggestions", "data": dynamic_suggestions}

        tool_calls = collect_tool_calls(final_state.get("messages", []))
        citations = list(final_state.get("final_citations") or [])
        route_trace = list(final_state.get("agent_route_trace") or [])
        ttft_ms = (
            max(1, round((first_token_at - started_at) * 1000))
            if first_token_at is not None
            else None
        )
        latency_ms = max(1, round((time.perf_counter() - started_at) * 1000))
        resp = ChatResponse(
            response=text,
            tool_calls=tool_calls,
            agent=final_state.get("selected_agent", "supervisor"),
            intent=final_state.get("intent", "collaborative_supervisor"),
            routing_reason=final_state.get("routing_reason", "") or "协作完成",
            thoughts=list(final_state.get("intermediate_steps") or []),
            citations=citations,
            confidence=normalize_confidence(final_state.get("final_confidence")),
            grounding_mode=normalize_grounding_mode(
                final_state.get("final_grounding_mode"),
                has_citations=bool(citations),
            ),
            suggestions=dynamic_suggestions[:3],
            metrics=_build_metrics(
                messages=final_state.get("messages") or [],
                route_trace=route_trace,
                cache_hit=False,
                rag_hit_count=len(final_state.get("rag_results") or []),
                tool_calls_count=len(tool_calls),
                ttft_ms=ttft_ms,
                latency_ms=latency_ms,
            ),
        )
        if _requires_hitl(
            resp.intent,
            req.user_input,
            final_state.get("task_breakdown") or "",
            final_state.get("collaboration_last_worker") or "",
        ):
            action = pending_action_store.create(
                user_id=req.user_id or "anonymous",
                thread_id=req.thread_id,
                plan_text=resp.response,
            )
            resp.requires_confirmation = True
            resp.pending_action_id = action.action_id

        yield {
            "type": "final",
            "content": text,
            "agent": resp.agent,
            "intent": resp.intent,
            "routing_reason": resp.routing_reason,
            "tool_calls": resp.tool_calls,
            "requires_confirmation": resp.requires_confirmation,
            "pending_action_id": resp.pending_action_id,
            "citations": resp.citations,
            "confidence": resp.confidence,
            "grounding_mode": resp.grounding_mode,
            "suggestions": resp.suggestions,
            "metrics": resp.metrics,
        }
    finally:
        clear_reasoning_context(emitter_token, controller_token)
