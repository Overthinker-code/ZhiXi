"""DeepSeek-style reasoning stream: contextual prose + tool action cards, no pipeline monologue."""

from __future__ import annotations

import contextvars
import re
from collections.abc import Iterator
from typing import Any, Callable

_reasoning_emitter: contextvars.ContextVar[Callable[[dict[str, Any]], None] | None] = (
    contextvars.ContextVar("reasoning_emitter", default=None)
)

# Bootstrap stages that must never appear as user-visible reasoning
_SILENT_STAGES = frozenset(
    {
        "pipeline_start",
        "kb_inject",
        "tool_policy",
        "web_policy",
        "cache",
        "tool_run",
        "demo_mode",
    }
)

_SUPERVISOR_BOILERPLATE = re.compile(
    r"主管正在分析|下一步由|本轮处理完成|已同步至主管|协作图|流水线|"
    r"Supervisor|intermediate_steps|tool_policy|启用工具|已关闭",
    re.I,
)


def set_reasoning_emitter(
    emitter: Callable[[dict[str, Any]], None] | None,
) -> contextvars.Token:
    return _reasoning_emitter.set(emitter)


def reset_reasoning_emitter(token: contextvars.Token) -> None:
    _reasoning_emitter.reset(token)


def emit_reasoning_event(event: dict[str, Any]) -> None:
    emitter = _reasoning_emitter.get()
    if emitter is not None:
        emitter(event)


def _chunk_reasoning_token(text: str, chunk_size: int = 8) -> Iterator[dict[str, Any]]:
    if not text:
        return
    for i in range(0, len(text), chunk_size):
        yield {"type": "reasoning_token", "content": text[i : i + chunk_size]}


def _emit_action(
    action: str,
    title: str,
    detail: str,
    items: list[str] | None = None,
) -> Iterator[dict[str, Any]]:
    payload: dict[str, Any] = {
        "type": "reasoning_action",
        "action": action,
        "title": title,
        "detail": detail,
    }
    if items:
        payload["items"] = items[:6]
    yield payload


class ReasoningStreamController:
    """Builds user-visible reasoning from user question + real tool outcomes only."""

    def __init__(self, user_input: str) -> None:
        self.user_input = (user_input or "").strip()
        self._opened = False
        self._seen: set[str] = set()

    def initial_thought(self) -> Iterator[dict[str, Any]]:
        if self._opened:
            return
        self._opened = True
        text = self._contextual_opening()
        if text:
            yield from _chunk_reasoning_token(text)

    def _contextual_opening(self) -> str:
        q = self.user_input
        if not q:
            return "我先理清问题的目标和已有条件，再决定直接讲解还是补充检索。"
        focus = re.sub(r"\s+", " ", q).strip()[:72]
        if re.search(r"文档|论文|课件|pdf|PDF|Word|上传", q, re.I):
            return (
                f"我先围绕「{focus}」定位上传材料中的对应段落，"
                "再区分原文依据和需要补充的解释。"
            )
        if re.search(r"代码|程序|报错|debug|算法实现", q, re.I):
            return (
                f"我先把「{focus}」拆成现象、原因和验证步骤，"
                "必要时再用代码或资料核对判断。"
            )
        if re.search(r"最新|新闻|今天|当前|版本|政策", q, re.I):
            return (
                f"「{focus}」可能涉及时效信息，我先确认关键事实的时间范围，"
                "再判断是否需要联网补充。"
            )
        if re.search(r"公式|定理|证明|积分|微分|矩阵|级数|极限|导数", q, re.I):
            return (
                f"我先判断「{focus}」属于哪类数学问题，"
                "再选择合适的定义或判别方法，并核对结论是否满足条件。"
            )
        return (
            f"我先抓住「{focus}」真正要解决的点，"
            "再决定直接解释，还是先补充课程资料中的依据。"
        )

    def from_intermediate_step(self, raw: str) -> Iterator[dict[str, Any]]:
        text = (raw or "").strip()
        if not text or _SUPERVISOR_BOILERPLATE.search(text):
            return
        if text.startswith("【") and "】" in text:
            return
        key = text[:80]
        if key in self._seen:
            return
        self._seen.add(key)
        yield from _chunk_reasoning_token(text)

    def on_knowledge_retrieve(
        self, query: str, hit_count: int, snippets: list[str] | None = None
    ) -> None:
        q = (query or self.user_input)[:80]
        detail = (
            f"在知识库中找到 {hit_count} 条与「{q}」相关的片段"
            if hit_count
            else f"知识库中暂未找到与「{q}」直接匹配的片段"
        )
        items = [(s or "")[:120] for s in (snippets or [])[:4] if s]
        for evt in _emit_action("retrieve", "检索知识库", detail, items):
            emit_reasoning_event(evt)

    def on_document_retrieve(
        self, query: str, hit_count: int, snippets: list[str] | None = None
    ) -> None:
        q = (query or self.user_input)[:80]
        detail = (
            f"在上传文档中找到 {hit_count} 处相关内容"
            if hit_count
            else "上传文档中未找到直接匹配的内容"
        )
        items = [(s or "")[:120] for s in (snippets or [])[:4] if s]
        for evt in _emit_action("retrieve", "检索上传文档", detail, items):
            emit_reasoning_event(evt)

    def on_web_search(self, query: str, result_text: str) -> None:
        q = (query or self.user_input)[:80]
        preview = (result_text or "").replace("搜索结果：", "").strip()
        items: list[str] = []
        if preview:
            for part in re.split(r"[\n;；]", preview):
                part = part.strip()
                if part and len(part) > 8:
                    items.append(part[:100])
                if len(items) >= 5:
                    break
        count = len(items) or (1 if preview else 0)
        detail = f"联网搜索「{q}」，获取到 {count} 条参考信息"
        for evt in _emit_action("web_search", "联网搜索", detail, items):
            emit_reasoning_event(evt)

    def on_code_sandbox(self, ok: bool, preview: str = "") -> None:
        detail = "代码已在沙盒中验证" if ok else "沙盒验证未通过，我会调整解释"
        items = [preview[:100]] if preview else []
        for evt in _emit_action("code", "代码验证", detail, items):
            emit_reasoning_event(evt)

    def on_vision(self, summary: str) -> None:
        detail = (summary or "正在理解图片内容")[:160]
        for evt in _emit_action("vision", "理解图片", detail):
            emit_reasoning_event(evt)


_reasoning_controller: contextvars.ContextVar[ReasoningStreamController | None] = (
    contextvars.ContextVar("reasoning_controller", default=None)
)


def set_reasoning_controller(
    controller: ReasoningStreamController | None,
) -> contextvars.Token:
    return _reasoning_controller.set(controller)


def reset_reasoning_controller(token: contextvars.Token) -> None:
    _reasoning_controller.reset(token)


def clear_reasoning_context(
    emitter_token: contextvars.Token | None = None,
    controller_token: contextvars.Token | None = None,
) -> None:
    """Restore reasoning contextvars; tolerate cross-task generator cleanup."""
    for var, reset_fn, token in (
        (_reasoning_emitter, reset_reasoning_emitter, emitter_token),
        (_reasoning_controller, reset_reasoning_controller, controller_token),
    ):
        if token is None:
            var.set(None)
            continue
        try:
            reset_fn(token)
        except ValueError:
            var.set(None)


def get_reasoning_controller() -> ReasoningStreamController | None:
    return _reasoning_controller.get()


def stream_thought_events(
    content: str,
    stage: str | None = None,
    *,
    user_visible: bool = True,
    user_input: str = "",
    controller: ReasoningStreamController | None = None,
) -> Iterator[dict[str, Any]]:
    """Emit thought/phase for debug; reasoning_token only when user_visible and meaningful."""
    stage_key = (stage or "").strip()
    if stage_key in _SILENT_STAGES:
        user_visible = False
    trimmed = (content or "").strip()
    if user_visible and trimmed and not trimmed.startswith("【"):
        if _SUPERVISOR_BOILERPLATE.search(trimmed):
            user_visible = False
    if user_visible and trimmed:
        ctrl = controller or ReasoningStreamController(user_input)
        yield from ctrl.from_intermediate_step(trimmed)
    yield {"type": "thought", "content": content, "stage": stage}
