"""Tests for ReasoningStreamController and silent bootstrap stages."""

from app.ai.reasoning_stream import (
    ReasoningStreamController,
    stream_thought_events,
)


def test_initial_thought_is_contextual_not_pipeline():
    ctrl = ReasoningStreamController("栈和队列有什么区别")
    events = list(ctrl.initial_thought())
    assert events
    joined = "".join(e.get("content", "") for e in events if e["type"] == "reasoning_token")
    assert "用户刚发来一个问题" not in joined
    assert "栈" in joined or "问题" in joined


def test_bootstrap_stages_silent():
    events = list(
        stream_thought_events(
            "【流水线】多智能体协作已启动",
            "pipeline_start",
        )
    )
    reasoning = [e for e in events if e["type"] == "reasoning_token"]
    thoughts = [e for e in events if e["type"] == "thought"]
    assert not reasoning
    assert thoughts


def test_supervisor_boilerplate_filtered():
    ctrl = ReasoningStreamController("hello")
    events = list(ctrl.from_intermediate_step("主管正在分析对话历史，下一步由 tutor 处理"))
    assert not events


def test_reasoning_action_via_controller():
    captured: list[dict] = []

    def _emit(evt: dict) -> None:
        captured.append(evt)

    from app.ai import reasoning_stream

    token = reasoning_stream.set_reasoning_emitter(_emit)
    ctrl_token = reasoning_stream.set_reasoning_controller(
        ReasoningStreamController("积分")
    )
    try:
        ctrl = reasoning_stream.get_reasoning_controller()
        assert ctrl is not None
        ctrl.on_knowledge_retrieve("积分", 2, ["定积分定义"])
    finally:
        reasoning_stream.reset_reasoning_emitter(token)
        reasoning_stream.reset_reasoning_controller(ctrl_token)

    assert captured
    assert captured[0]["type"] == "reasoning_action"
    assert captured[0]["action"] == "retrieve"
    assert "2" in captured[0]["detail"]
