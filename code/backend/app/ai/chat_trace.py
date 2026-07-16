"""Public chat execution trace helpers.

The trace describes observable execution boundaries and safe result summaries. It
must never contain model chain-of-thought, system prompts, or raw tool arguments.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from typing import Any

TRACE_VERSION = "1.0"

_PHASE_ALIASES = {
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

_CATEGORIES = {
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

_BLOCKED_TRACE_TEXT = re.compile(
    r"<\/?think>|system[_ ]?prompt|系统提示词|内部提示词|"
    r"intermediate_steps|route_trace|tool_policy|additional_kwargs|"
    r"Supervisor|LangGraph|协作线程|上下文注入",
    re.I,
)


def normalize_phase(value: Any) -> str:
    raw = str(value or "understand_problem").strip()
    allowed = set(_PHASE_ALIASES.values())
    return _PHASE_ALIASES.get(raw, raw if raw in allowed else "understand_problem")


def safe_trace_summary(value: Any, fallback: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text or _BLOCKED_TRACE_TEXT.search(text):
        return fallback
    return text[:limit]


class ChatTraceRecorder:
    """Attach stable identity, ordering and measured durations to SSE events."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.sequence = 0
        self._started: dict[str, tuple[float, str]] = {}
        self._tool_occurrences: dict[str, int] = {}

    def next_tool_call_id(self, tool: str) -> str:
        safe_tool = self._safe_key(tool or "tool")
        occurrence = self._tool_occurrences.get(safe_tool, 0) + 1
        self._tool_occurrences[safe_tool] = occurrence
        return f"{safe_tool}:{occurrence}"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    @staticmethod
    def _safe_key(value: Any) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value or "").strip())[:80]

    def _identity(self, event: str, payload: dict[str, Any]) -> tuple[str, str, str]:
        phase_id = normalize_phase(payload.get("phaseId"))
        if event.startswith("tool_"):
            tool = self._safe_key(payload.get("tool") or "tool")
            call_id = self._safe_key(payload.get("callId") or tool)
            return f"tool:{call_id}", "call_tool", "tool"
        if event in {"token", "answer_delta", "suggestions", "citation", "final"}:
            return "output:answer", "generate_answer", "output"
        if event in {"run_started", "message_started", "session_created"}:
            return "run:lifecycle", phase_id, "route"
        if event in {"run_finished", "done"}:
            return "run:lifecycle", phase_id, "output"
        if event in {"safety_check", "process_sanitized"}:
            return "phase:verify_output", "verify_output", "safety"
        if event == "profile_update":
            return "phase:update_learning_profile", "update_learning_profile", "profile"
        return (
            f"phase:{self._safe_key(phase_id or event)}",
            phase_id,
            _CATEGORIES.get(phase_id, "output"),
        )

    def enrich(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(payload)
        self.sequence += 1
        now_mono = time.perf_counter()
        now_iso = self._now_iso()
        step_id, phase_id, category = self._identity(event, enriched)
        enriched.setdefault("runId", self.run_id)
        enriched.setdefault("traceVersion", TRACE_VERSION)
        enriched.setdefault("sequence", self.sequence)
        enriched.setdefault("stepId", step_id)
        enriched.setdefault("phaseId", phase_id)
        enriched.setdefault("category", category)
        enriched.setdefault("timestamp", now_iso)

        starts = event in {"phase_started", "tool_started", "run_started", "message_started"}
        finishes = event in {"phase_finished", "tool_result", "run_finished", "done", "error", "final"}
        if starts:
            self._started.setdefault(step_id, (now_mono, now_iso))
            enriched.setdefault("startedAt", self._started[step_id][1])
            enriched.setdefault("status", "running")
        elif step_id in self._started:
            enriched.setdefault("startedAt", self._started[step_id][1])
        if finishes:
            started_mono, started_iso = self._started.pop(step_id, (now_mono, now_iso))
            enriched.setdefault("startedAt", started_iso)
            enriched.setdefault("finishedAt", now_iso)
            enriched.setdefault("durationMs", max(0, round((now_mono - started_mono) * 1000)))
            if event != "error":
                enriched.setdefault("status", "done")
        return enriched

    def event(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"type": event, **self.enrich(event, payload)}


def public_engine_events(
    payload: dict[str, Any], recorder: ChatTraceRecorder
) -> list[dict[str, Any]]:
    """Convert chat-engine output to public events while suppressing raw CoT."""

    kind = str(payload.get("type") or "")
    if kind in {"reasoning_token", "thought"}:
        return []
    if kind == "trace_step":
        event = str(payload.get("event") or "phase_updated")
        safe = {
            "phaseId": normalize_phase(payload.get("phaseId")),
            "title": safe_trace_summary(payload.get("title"), "处理当前任务", 60),
            "summary": safe_trace_summary(payload.get("summary"), "正在处理当前任务"),
            "status": str(payload.get("status") or "running"),
        }
        if payload.get("streamingMode") in {"provider", "replayed"}:
            safe["streamingMode"] = payload["streamingMode"]
        return [recorder.event(event, safe)]
    if kind == "reasoning_action":
        action = str(payload.get("action") or "tool")
        tool = {
            "retrieve": "course_retriever",
            "web_search": "web_search",
            "vision": "attachment_reader",
            "code": "code_sandbox",
        }.get(action, "learning_tool")
        detail = safe_trace_summary(payload.get("detail"), "工具执行完成")
        call_id = recorder.next_tool_call_id(tool)
        return [
            recorder.event(
                "tool_result",
                {
                    "tool": tool,
                    "callId": call_id,
                    "title": safe_trace_summary(payload.get("title"), "工具执行", 60),
                    "summary": detail,
                    "status": "done",
                    # Raw tool parameters and provider payloads are intentionally omitted.
                    "items": [],
                },
            )
        ]
    if kind == "phase":
        phase_id = normalize_phase(payload.get("phase"))
        title = {
            "select_capability": "选择处理能力",
            "retrieve_knowledge": "检索学习资料",
            "call_tool": "执行学习工具",
            "generate_answer": "组织回答",
            "verify_output": "校验输出",
        }.get(phase_id, "处理当前任务")
        return [
            recorder.event(
                "phase_updated",
                {
                    "phaseId": phase_id,
                    "title": title,
                    "summary": safe_trace_summary(payload.get("summary"), title),
                    "status": "running",
                },
            )
        ]
    if kind == "token":
        public_token = {"content": str(payload.get("content") or "")}
        if payload.get("streamingMode") in {"provider", "replayed"}:
            public_token["streamingMode"] = payload["streamingMode"]
        return [recorder.event("token", public_token)]
    if kind == "suggestions":
        return [recorder.event("suggestions", {"data": payload.get("data") or []})]
    if kind == "final":
        public = dict(payload)
        public["routingSummary"] = safe_trace_summary(
            public.get("routing_reason"), "已按当前问题类型完成处理"
        )
        public.pop("thoughts", None)
        public.pop("intermediate_steps", None)
        public.pop("routing_reason", None)
        return [recorder.event("final", public)]
    if kind == "error":
        return [
            recorder.event(
                "error",
                {
                    "code": "CHAT_EXECUTION_FAILED",
                    "content": "本轮处理未完成，请稍后重试。",
                    "status": "error",
                },
            )
        ]
    return []
