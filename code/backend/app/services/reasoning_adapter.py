from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


ProcessStageId = Literal[
    "understand_problem",
    "select_capability",
    "prepare_context",
    "retrieve_knowledge",
    "call_tool",
    "plan_answer",
    "generate_answer",
    "verify_output",
    "update_learning_profile",
    "suggest_next_step",
]


STAGE_TITLES: dict[ProcessStageId, str] = {
    "understand_problem": "理解问题",
    "select_capability": "选择能力",
    "prepare_context": "准备上下文",
    "retrieve_knowledge": "检索课程资料",
    "call_tool": "调用工具",
    "plan_answer": "组织回答",
    "generate_answer": "生成回答",
    "verify_output": "校验输出",
    "update_learning_profile": "更新学习画像",
    "suggest_next_step": "生成后续建议",
}

SUPPLIER_CONTEXT_TERMS = (
    "小米",
    "米家",
    "HyperOS",
    "MIUI",
    "澎湃OS",
    "手机",
    "手环",
    "电视",
    "智能家居",
    "生态设备",
    "售后",
    "系统优化",
    "官方发布",
    "小米助手",
    "我是小米",
    "小爱",
)

ANSWER_GUARD_MESSAGE = (
    "我会以智屿 AI 伴学助手身份回答：围绕高校课程学习、课程资料问答、"
    "作业辅导、资源生成、学习路径规划、学情分析和深度研究提供支持。"
)

INTERNAL_PROCESS_RE = re.compile(
    r"(?:"
    r"intent_classifier|course_context|reasoning_content|"
    r"系统消息|上下文注入|协作线程|首条系统消息|"
    r"Supervisor|intermediate_steps|tool_policy|route_trace|"
    r"【(?:流水线|知识检索|工具策略|工具执行|联网搜索|多智能体协作)】"
    r")",
    re.IGNORECASE,
)


@dataclass
class ReasoningAdapterContext:
    message: str = ""
    mode: str = "tutor"
    tools: dict[str, Any] = field(default_factory=dict)
    course_context: dict[str, Any] = field(default_factory=dict)
    retrieval_status: str = ""
    citation_status: str = ""

    @property
    def user_allows_supplier_context(self) -> bool:
        text = self.message.lower()
        return any(term.lower() in text for term in SUPPLIER_CONTEXT_TERMS)

    @property
    def is_course_question(self) -> bool:
        return bool(
            self.course_context.get("useCourseRag")
            or self.course_context.get("use_course_rag")
            or self.tools.get("courseRag")
            or self.tools.get("course_rag")
        )


@dataclass
class ProcessDelta:
    phase_id: ProcessStageId
    summary: str
    status: str = "running"
    sanitized: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "phaseId": self.phase_id,
            "title": STAGE_TITLES[self.phase_id],
            "summary": self.summary,
            "status": self.status,
            "sanitized": self.sanitized,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        }


def contains_supplier_context(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(term.lower() in lowered for term in SUPPLIER_CONTEXT_TERMS)


def strip_reasoning_markers(text: str) -> str:
    return re.sub(r"</?think>", "", str(text or ""), flags=re.IGNORECASE).strip()


def strip_reasoning_blocks(text: str) -> tuple[str, bool]:
    """Remove provider/native reasoning blocks before text reaches answer UI."""

    raw = str(text or "")
    if not raw:
        return "", False
    blocked = bool(re.search(r"</?think>", raw, flags=re.IGNORECASE))
    clean = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE)
    clean = re.sub(r"<think>[\s\S]*$", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</think>", "", clean, flags=re.IGNORECASE)
    return clean, blocked


def sanitize_visible_answer_delta(
    text: str,
    context: ReasoningAdapterContext,
    *,
    preserve_edges: bool = False,
) -> tuple[str, bool]:
    """Keep process/reasoning logs out of the final assistant answer stream."""

    clean, blocked = strip_reasoning_blocks(text)
    if not clean:
        return "", blocked

    kept_lines: list[str] = []
    for line in clean.splitlines(keepends=True):
        stripped = line.strip()
        if stripped and INTERNAL_PROCESS_RE.search(stripped):
            blocked = True
            continue
        kept_lines.append(line)
    clean = "".join(kept_lines)
    if not clean:
        return "", True

    guarded, supplier_blocked = guard_answer_delta(
        clean if preserve_edges else clean.strip(),
        context,
    )
    return guarded, blocked or supplier_blocked


def _clip_summary(text: str, limit: int = 72) -> str:
    clean = re.sub(r"\s+", " ", strip_reasoning_markers(text)).strip(" ，。；;")
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip(" ，。；;") + "。"


def _mode_stage(context: ReasoningAdapterContext) -> tuple[ProcessStageId, str]:
    mode = context.mode
    tools = context.tools or {}
    if mode == "homework_review" or tools.get("homeworkReview") or tools.get("homework_review"):
        return "plan_answer", "正在识别题目、分析解题步骤，并准备生成错因反馈。"
    if mode == "resource_generation" or tools.get("resourceGeneration") or tools.get("resource_generation"):
        return "plan_answer", "正在规划讲义、练习题、思维导图和代码案例等资源结构。"
    if mode == "deep_research" or tools.get("deepResearch") or tools.get("deep_research"):
        return "retrieve_knowledge", "正在制定检索计划、筛选来源，并组织研究报告结构。"
    if context.is_course_question:
        return "retrieve_knowledge", "正在结合课程资料与学习上下文，整理可引用依据。"
    return "plan_answer", "已识别为通用问答，将以智屿学习助手能力组织回答。"


def normalize_reasoning_to_product_process(
    raw_reasoning: str,
    context: ReasoningAdapterContext,
) -> ProcessDelta | None:
    """Convert provider-native reasoning into a ZhiXi product process delta."""

    raw = strip_reasoning_markers(raw_reasoning)
    if not raw:
        return None

    sanitized = contains_supplier_context(raw) and not context.user_allows_supplier_context
    if sanitized:
        stage, summary = _mode_stage(context)
        return ProcessDelta(stage, summary, sanitized=True)

    lowered = raw.lower()
    if any(token in raw for token in ("引用", "校验", "安全", "幻觉", "不确定")):
        return ProcessDelta("verify_output", "正在检查回答是否保持智屿教育产品定位，并校验引用与安全边界。")
    if any(token in raw for token in ("检索", "资料", "知识库", "课程", "证据", "片段", "rag")):
        if context.is_course_question:
            return ProcessDelta("retrieve_knowledge", "正在结合课程资料与学习上下文，整理可引用依据。")
        return ProcessDelta("prepare_context", "正在判断是否需要课程资料、上传附件或联网来源支持。")
    if any(token in raw for token in ("题目", "解题", "错因", "批改", "评分")):
        return ProcessDelta("plan_answer", "正在识别题目结构、分析解题步骤，并准备生成反馈。")
    if any(token in raw for token in ("讲义", "练习", "思维导图", "资源", "题库", "代码案例")):
        return ProcessDelta("plan_answer", "正在规划个性化学习资源的结构与难度。")
    if any(token in raw for token in ("联网", "来源", "报告", "研究", "筛选")):
        return ProcessDelta("retrieve_knowledge", "正在制定检索计划、筛选来源，并组织报告结构。")
    if any(token in raw for token in ("问题", "意图", "目标", "能力", "能做什么", "介绍")) or "capability" in lowered:
        return ProcessDelta("select_capability", "正在识别用户意图，并选择适合的智屿学习支持能力。")
    if any(token in raw for token in ("组织", "结构", "回答", "结论", "例子", "建议")):
        return ProcessDelta("plan_answer", "正在按结论、解释、例子、常见误区和下一步建议组织回答。")

    stage, fallback = _mode_stage(context)
    return ProcessDelta(stage, _clip_summary(fallback))


class ReasoningProcessNormalizer:
    """Stateful adapter used by SSE streaming to dedupe product process deltas."""

    def __init__(self, context: ReasoningAdapterContext):
        self.context = context
        self.internal_raw_reasoning = ""
        self._last_summary_by_stage: dict[str, str] = {}
        self._sanitized = False

    @property
    def sanitized(self) -> bool:
        return self._sanitized

    def ingest(self, raw_reasoning: str) -> ProcessDelta | None:
        raw = str(raw_reasoning or "")
        if not raw:
            return None
        self.internal_raw_reasoning += raw
        delta = normalize_reasoning_to_product_process(raw, self.context)
        if not delta:
            return None
        self._sanitized = self._sanitized or delta.sanitized
        previous = self._last_summary_by_stage.get(delta.phase_id)
        if previous == delta.summary:
            return None
        self._last_summary_by_stage[delta.phase_id] = delta.summary
        return delta

    def process_sanitized_payload(self) -> dict[str, Any] | None:
        if not self._sanitized:
            return None
        return {
            "phaseId": "verify_output",
            "title": STAGE_TITLES["verify_output"],
            "summary": "已完成过程整理，过滤与智屿教育场景无关的供应商语境。",
            "status": "done",
            "sanitized": True,
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        }


def guard_answer_delta(text: str, context: ReasoningAdapterContext) -> tuple[str, bool]:
    raw = str(text or "")
    if not raw or context.user_allows_supplier_context:
        return raw, False
    if not contains_supplier_context(raw):
        return raw, False
    return "", True


def guarded_fallback_answer(context: ReasoningAdapterContext) -> str:
    if context.message and ("能做什么" in context.message or "你可以" in context.message):
        return (
            "我是智屿智能教育平台的 AI 伴学助手，可以支持：\n\n"
            "1. 课程问答：结合课程资料、知识点和引用证据解释问题。\n"
            "2. 作业批改：分析题目、定位错因，并给出改进建议。\n"
            "3. 个性化练习：围绕薄弱知识点生成训练题和解析。\n"
            "4. 资料生成：生成讲义、练习题、思维导图、代码案例和拓展阅读。\n"
            "5. 学习路径：根据掌握度推荐下一步学习任务。\n"
            "6. 学情诊断与深度研究：整理学习画像、筛选资料来源并输出研究报告。"
        )
    return ANSWER_GUARD_MESSAGE
