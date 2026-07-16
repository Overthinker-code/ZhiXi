from app.ai.chat_models import ChatRequest
from app.ai.chat_trace import ChatTraceRecorder, public_engine_events
from app.ai.chat_engine import _live_process_snapshot
from app.api.v1.endpoints.ai_chat import _legacy_event_to_ai_events
from app.services.reasoning_adapter import (
    ReasoningAdapterContext,
    ReasoningProcessNormalizer,
)


def test_trace_recorder_adds_identity_sequence_and_duration() -> None:
    trace = ChatTraceRecorder("run-test")
    started = trace.event(
        "phase_started",
        {"phaseId": "retrieve_knowledge", "title": "检索资料"},
    )
    finished = trace.event(
        "phase_finished",
        {
            "phaseId": "retrieve_knowledge",
            "title": "检索资料",
            "summary": "获得 2 条资料",
        },
    )

    assert started["runId"] == "run-test"
    assert started["traceVersion"] == "1.0"
    assert started["stepId"] == finished["stepId"] == "phase:retrieve_knowledge"
    assert finished["sequence"] == started["sequence"] + 1
    assert finished["category"] == "retrieval"
    assert finished["durationMs"] >= 0
    assert finished["finishedAt"]


def test_public_engine_events_never_forward_raw_reasoning_or_tool_arguments() -> None:
    trace = ChatTraceRecorder("run-safe")

    assert public_engine_events(
        {"type": "reasoning_token", "content": "<think>private chain of thought</think>"},
        trace,
    ) == []
    assert public_engine_events(
        {"type": "thought", "content": "system_prompt=secret"},
        trace,
    ) == []

    events = public_engine_events(
        {
            "type": "reasoning_action",
            "action": "retrieve",
            "title": "检索知识库",
            "detail": "找到 3 条课程资料",
            "items": ["raw private document chunk"],
            "arguments": {"token": "secret"},
        },
        trace,
    )
    assert len(events) == 1
    assert events[0]["type"] == "tool_result"
    assert events[0]["summary"] == "找到 3 条课程资料"
    assert events[0]["items"] == []
    assert "arguments" not in events[0]
    retry = public_engine_events(
        {
            "type": "reasoning_action",
            "action": "retrieve",
            "title": "检索知识库",
            "detail": "重试后找到 2 条课程资料",
        },
        trace,
    )[0]
    assert retry["callId"] != events[0]["callId"]
    assert retry["stepId"] != events[0]["stepId"]


def test_trace_step_preserves_truthful_streaming_mode() -> None:
    trace = ChatTraceRecorder("run-stream")
    events = public_engine_events(
        {
            "type": "trace_step",
            "event": "phase_finished",
            "phaseId": "generate_answer",
            "title": "生成回答",
            "summary": "回答已完成",
            "status": "done",
            "streamingMode": "replayed",
        },
        trace,
    )
    assert events[0]["type"] == "phase_finished"
    assert events[0]["streamingMode"] == "replayed"


def test_live_process_snapshot_is_a_single_summary_not_fake_tokens() -> None:
    request = ChatRequest(user_input="解释事务", thread_id="trace-test")
    events = list(_live_process_snapshot(request, []))
    assert len(events) == 1
    assert events[0]["type"] == "trace_step"
    assert events[0]["event"] == "phase_updated"


def test_reasoning_normalizer_keeps_only_bounded_diagnostic_tail() -> None:
    normalizer = ReasoningProcessNormalizer(ReasoningAdapterContext())
    normalizer.ingest("回答结构" * 3000)
    assert len(normalizer.internal_raw_reasoning) <= 4096


def test_ai_chat_final_payload_forwards_grounded_citations() -> None:
    events = _legacy_event_to_ai_events(
        {
            "type": "final",
            "content": "事务原子性要求全部完成或全部回滚。",
            "citations": [
                {
                    "citation_id": 1,
                    "source": "02_lecture_notes.md",
                    "locator": "事务与 ACID",
                }
            ],
        }
    )
    assert [name for name, _ in events] == ["tool_result", "citation"]
    assert events[1][1]["source"] == "02_lecture_notes.md"
