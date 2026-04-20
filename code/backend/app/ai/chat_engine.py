from __future__ import annotations

import json
import re
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.ai.chat_models import ChatRequest, ChatResponse, State, SupervisorDecision
from app.ai.chat_runtime import AGENT_CONFIG, resolve_system_prompt
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
from app.services.chat_semantic_cache import chat_semantic_cache
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

_JSON_OBJ = re.compile(r"\{[\s\S]*\}")
_DOC_QUERY_HINT = re.compile(
    r"(这篇|该|这个)?(论文|文档|报告|课件|pdf|PDF|word|Word|doc|DOC|章节|第[一二三四五六七八九十0-9]+章|摘要|方法|实验|结论|创新点|原文)"
)
_QUIZ_HINT = re.compile(
    r"(考考我|出题|做题|测验|测试我|我来答题|我来回答|练习题|来道题|随堂测|小测)"
)

# 防止异常超大请求；实际需要更长可在 .env 提高 CHAT_DEFAULT_MAX_TOKENS
_MAX_OUTPUT_CAP = 131072


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
    re.compile(rf"`</{_TK}>[\s\S]*?`</{_TK}>`", re.IGNORECASE | re.DOTALL),
    re.compile(r"<analysis>[\s\S]*?</analysis>", re.IGNORECASE),
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


SUPERVISOR_SYSTEM_PROMPT = """你是「知曦学习系统」的主管 Supervisor（包工头），负责编排多位专员协同完成学生问题。

下属专员（每次只派其中一人发言，或判定可以结束）：
- code_tutor：编程语言报错、调试、运行失败、SQL/Python/Java/TS 等工程问题。
- knowledge_mentor：跨学科知识点讲解、概念辨析、教材型问答（经管、数理、文史、自然科学等），非代码排错优先找 TA。
- planner：学习计划、进度、复习节奏、里程碑与任务拆解。
- analyst：学习行为、状态评估、风险与数据化解读。
- doc_researcher：围绕用户当前挂载文档（论文/课件/报告）做检索式解读与细节问答。
- quiz_master：主动测验与批改，负责“出题->等待作答->点评引导”闭环。

规则：
1. 结合完整对话历史判断「下一步谁最合适」；复合型需求可拆成多轮，一轮只派一名专员。
2. 若专员已在消息中充分覆盖且无需他人补位，输出 FINISH 进入汇总阶段。
3. 信息严重不足时可先派 knowledge_mentor 或 code_tutor 做澄清式回答，再视情况 FINISH 或继续派其他人。
4. 输出必须严格符合约定的结构化字段（next_agent / routing_reason / task_breakdown），不要输出其它闲聊；禁止用 Markdown 代码块包裹 JSON。
5. 【必须遵守】当你认为下属专员已经给出足够信息、或问题已可收束、或不宜再换人时，你 MUST 将 next_agent 设为字符串 FINISH（仅此一种写法），进入汇总；不要继续派发专员。
6. task_breakdown 仅写简短要点（每条一行内），禁止写入完整解题过程或长篇推导，避免污染协作上下文。
7. 用户请求“考考我/出题/测试一下/我来回答上一题”等测验场景时，优先路由 quiz_master。
8. 若用户当前挂载了文件，且问题指向该文件内容（如“总结这篇论文”“解释第三章”），优先路由 doc_researcher。"""

FINALIZE_SYSTEM_PROMPT = """你是知曦学习系统的最终发言人。你将收到「学生问题」「知识库摘要」「专员协作产出」。请面向学生生成可直接发送的最终答复。

必须遵守：
1. 直接给出完整、专业的解答，使用 Markdown 标题与列表排版；语气像耐心的导师。
2. 禁止「我先想想」「接下来我要」「不对，应该是」等内心独白、草稿式自言自语；禁止复述专员的思考过程，只输出结论与推导要点。
3. 禁止提及主管、路由、JSON、工具名、Agent、LangGraph 等内部实现与协作流程词。
4. 专员材料不足时诚实说明，可结合知识库与通用知识合理补充，勿编造上传资料中不存在的事实。
5. 在正文结束后，必须附加如下结构（严格保留标签）：
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
        return ["这一步哪里最容易出错？", "能给我一个最小练习题吗？", "下一步我该怎么学？"]
    return [
        "基于这个问题，最核心的知识点是什么？",
        "给我一道由浅入深的练习题。",
        "如果答错了，我该如何快速纠正？",
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
    q_hint = re.compile(r"(吗|么|如何|为什么|怎么|是否|能否|要不要|哪个|哪些|几种|\?)")
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


def _pick_topic_from_question(user_q: str) -> str:
    q = (user_q or "").strip()
    if not q:
        return "这个知识点"
    # 优先提取「X的/关于X/围绕X」这类显式主题片段
    patterns = [
        r"(?:关于|围绕|针对|聚焦)\s*([^\s，。；！？,.!?]{2,24})",
        r"([^\s，。；！？,.!?]{2,24})\s*的(?:核心|典型|重点|难点|易错点|题型|知识点)",
        r"解决\s*([^\s，。；！？,.!?]{2,24})\s*(?:问题|难题|题目)",
    ]
    for pat in patterns:
        m = re.search(pat, q)
        if m:
            topic = re.sub(r"[的地得]+$", "", m.group(1).strip())
            if topic:
                return topic[:20]

    # 次优：按学科关键词兜底，避免提取成“指导我完成高分训练”这类动作词
    subject_keywords = [
        "小学数学",
        "初中数学",
        "高中数学",
        "微积分",
        "线性代数",
        "概率论",
        "数据库",
        "SQL",
        "事务处理",
        "并发控制",
    ]
    for kw in subject_keywords:
        if kw in q:
            return kw
    return "这个知识点"


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
    topic = _pick_topic_from_question(user_q)
    intent = _infer_followup_intent(user_q, answer)
    _ = max_tokens
    if intent == "practice":
        return [
            f"先从 {topic} 的哪三类题型开始练最提分？",
            f"基于 {topic} 给我一道阶梯练习题，并先只给第 1 步提示？",
            f"做 {topic} 题时最常见的失分点有哪些？",
        ]
    if intent == "fix":
        return [
            f"我在 {topic} 上最可能犯的 3 个错误分别是什么？",
            f"能给我一个 {topic} 的错题订正模板吗？",
            f"下次遇到 {topic} 同类题，我该如何快速自检？",
        ]
    if intent == "summary":
        return [
            f"把 {topic} 再压缩成 5 条考前速记卡片可以吗？",
            f"{topic} 中最容易混淆的概念对照表能给我吗？",
            f"按考试频率，{topic} 的复习优先级该怎么排？",
        ]
    return [
        f"{topic} 最容易混淆的概念有哪些？",
        f"能围绕 {topic} 给我一题由浅入深的练习吗？",
        f"如果我在 {topic} 上做错题，应该怎么快速纠正？",
    ]


def _rag_system_message(request: ChatRequest) -> SystemMessage:
    results = rag_service.query_knowledge_base(
        query=request.user_input,
        k=request.rag_k,
        user_id=request.user_id,
        is_admin=request.is_admin,
    )
    strict_effective = bool(request.strict_mode) and bool(results)
    if results:
        context_chunks = "\n\n".join(
            f"[citation:{item['citation_id']}] {item['content']}" for item in results
        )
        preamble = (
            "【知识库上下文】下列为与问题相关的知识库片段（有帮助时请引用并标注 [citation:x]）。\n"
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
    return SystemMessage(content=body)


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
        }

    ruled = _rule_based_route(state)
    if ruled:
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
        }

    decision, used_fallback = _invoke_supervisor_llm(state)
    prev_fb = int(state.get("supervisor_fallback_streak") or 0)
    streak = prev_fb + 1 if used_fallback else 0

    na = decision.next_agent
    routing_reason = (decision.routing_reason or "").strip()
    task_bd = decision.task_breakdown.strip()

    forced_finish_parse = False
    if used_fallback and streak >= _MAX_SUPERVISOR_FALLBACK_STREAK:
        na = "FINISH"
        routing_reason = (
            "主管路由结构化输出连续解析失败，已强制结束协作并进入汇总；"
            "将基于当前对话中已有专员发言生成答复。"
        )
        forced_finish_parse = True

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

    try:
        raw_msg = llm.invoke([sys, human])
        clean = _strip_think_blocks_from_text(_strict_ai_content_for_user(raw_msg))
        if clean:
            msg = AIMessage(content=clean, name="final_answer")
        else:
            fallback_text = _fallback_from_recent_worker_messages(msgs)
            if fallback_text:
                msg = AIMessage(content=fallback_text, name="final_answer")
            else:
                msg = AIMessage(
                    content="当前轮次生成异常，请重试一次或换个问法，我会继续给出可见答复。",
                    name="final_answer",
                )
    except Exception as e:
        msg = AIMessage(
            content=(
                "汇总阶段暂时无法完成（常见于上下文过长或服务限制）。请尝试缩短问题或开启新对话。"
                f"\n（详情：{str(e)[:400]}）"
            ),
            name="final_answer",
        )
    return {
        "messages": [msg],
        "selected_agent": "supervisor",
        "intent": "final_summary",
        "routing_reason": state.get("routing_reason", "") or "协作汇总",
        "intermediate_steps": [
            "【汇总生成】主管正在综合各专员发言，生成面向学生的最终答复。"
        ],
    }


_WORKER_DONE_TAG: dict[str, str] = {
    "code_tutor": "【代码验证】代码导师本轮处理完成，结果已同步至主管。",
    "knowledge_mentor": "【学科讲解】学科知识讲师本轮处理完成，已同步至主管。",
    "planner": "【学习规划】学习规划师本轮处理完成，已同步至主管。",
    "analyst": "【学情分析】学习分析师本轮处理完成，已同步至主管。",
    "doc_researcher": "【文档研究】文档研究员本轮处理完成，已同步至主管。",
    "quiz_master": "【主动测验】测验官本轮处理完成，已同步至主管。",
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
    if not selected:
        return request.user_input

    prompt = (
        f"学生在学习《{module}》时选中了“{selected}”。\n"
        f"上下文片段：{context or '（无）'}\n"
    )
    if video_time:
        prompt += f"当前视频时间点：{video_time}\n"
    prompt += (
        "请用引导式、教学友好的口吻回答。"
        "如果适合，请补充一个简短示例帮助理解。"
    )
    return prompt


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
    if not active_tools:
        return allowed, []
    active = set(active_tools)
    enabled = [k for k in allowed if k in active]
    disabled = [k for k in allowed if k not in active]
    return enabled, disabled


def _initial_state(request: ChatRequest, user_text: str) -> State:
    rag_msg = _rag_system_message(request)
    preset = resolve_system_prompt(request.prompt_key, request.system_prompt)
    memory_context = _load_user_memory_context(request.user_id)
    messages: list = [rag_msg]
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
            "user_memory_context": memory_context,
        },
    )


def chat_service(request: ChatRequest) -> ChatResponse:
    request = _with_resolved_max_tokens(request)
    if request.selected_text:
        request.user_input = _build_selection_prompt(request)

    cache_hit = (
        None
        if (request.prior_turns or [])
        else chat_semantic_cache.get(request.user_input)
    )
    if cache_hit:
        return ChatResponse(
            response=cache_hit.answer,
            tool_calls=[],
            agent="supervisor",
            intent="semantic_cache",
            routing_reason=f"语义缓存命中（hit_count={cache_hit.hit_count}）",
            thoughts=["⚡ 语义缓存命中，直接返回历史高相似答案。"],
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

    result = graph.invoke(initial, config=thread_config)
    final_text = _last_meaningful_assistant_text(result.get("messages") or [])
    final_text, _ = _split_suggestions(final_text)
    thoughts = list(result.get("intermediate_steps") or [])
    response = ChatResponse(
        response=final_text,
        tool_calls=collect_tool_calls(result.get("messages", [])),
        agent=result.get("selected_agent", "supervisor"),
        intent=result.get("intent", "collaborative_supervisor"),
        routing_reason=result.get("routing_reason", "") or "协作完成",
        thoughts=thoughts,
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

    chat_semantic_cache.put(request.user_input, response.response)
    return response


def stream_chat_events(request: ChatRequest):
    request = _with_resolved_max_tokens(request)
    user_input = request.user_input
    if request.selected_text:
        user_input = _build_selection_prompt(request)
    req = request.model_copy(update={"user_input": user_input})

    enabled_tools, disabled_tools = _tool_status_text(req.active_tools)
    yield {
        "type": "thought",
        "content": "【流水线】多智能体协作已启动（Supervisor + 专员 + 汇总）。",
        "stage": "pipeline_start",
    }
    yield {
        "type": "thought",
        "content": "【知识检索】已根据当前问题检索知识库并将上下文注入协作线程（首条系统消息）。",
        "stage": "kb_inject",
    }
    if req.active_tools is not None:
        yield {
            "type": "thought",
            "content": f"【工具策略】启用工具：{enabled_tools or ['none']}；已关闭：{disabled_tools or ['none']}",
            "stage": "tool_policy",
        }
        if not enabled_tools:
            yield {
                "type": "thought",
                "content": "【工具策略】当前过滤后无可用工具，专员将仅依赖模型能力。",
                "stage": "tool_policy",
            }

    cache_hit = (
        None
        if (req.prior_turns or [])
        else chat_semantic_cache.get(req.user_input)
    )
    if cache_hit:
        yield {
            "type": "thought",
            "content": "【流水线】语义缓存命中，跳过协作图执行。",
            "stage": "cache",
        }
        text = cache_hit.answer
        for i in range(0, len(text), 24):
            yield {"type": "token", "content": text[i : i + 24]}
        sug = _contextual_suggestions_from_llm(
            req.user_input, text, max_tokens=req.max_tokens
        ) or _default_suggestions(req.user_input)
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
    initial = _initial_state(req, req.user_input)

    final_state: dict | None = None
    last_values_state: dict | None = None
    emitted_tool_nodes: set[str] = set()
    try:
        # 同时订阅 updates（流水线 thought）与 values（每步完整 State，最后一步含 finalize 的 messages）
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
                    yield {
                        "type": "thought",
                        "content": _TOOL_NODE_PIPELINE_MSG.get(
                            node_name,
                            "【工具执行】正在运行后端工具节点。",
                        ),
                        "stage": "tool_run",
                    }
                if isinstance(data, dict):
                    for s in data.get("intermediate_steps") or []:
                        yield {"type": "thought", "content": s}

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
    text = _last_meaningful_assistant_text(msgs)
    text, suggestions = _split_suggestions(text)
    if not (text or "").strip():
        yield {
            "type": "error",
            "content": "协作图已结束但未生成可展示的助手正文，请重试或检查模型输出。",
        }
        return

    chat_semantic_cache.put(req.user_input, text)

    chunk_size = 24
    for i in range(0, len(text), chunk_size):
        yield {"type": "token", "content": text[i : i + chunk_size]}
    dynamic_suggestions = (
        suggestions
        or _contextual_suggestions_from_llm(
            req.user_input, text, max_tokens=req.max_tokens
        )
        or _default_suggestions(req.user_input)
    )
    yield {"type": "suggestions", "data": dynamic_suggestions}

    resp = ChatResponse(
        response=text,
        tool_calls=collect_tool_calls(final_state.get("messages", [])),
        agent=final_state.get("selected_agent", "supervisor"),
        intent=final_state.get("intent", "collaborative_supervisor"),
        routing_reason=final_state.get("routing_reason", "") or "协作完成",
        thoughts=list(final_state.get("intermediate_steps") or []),
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
    }
