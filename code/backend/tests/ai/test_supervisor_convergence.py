from app.ai import chat_engine
from app.ai.chat_models import SupervisorDecision


def _state(**overrides):
    state = {
        "supervisor_entries": 1,
        "supervisor_fallback_streak": 0,
        "collaboration_last_worker": "knowledge_mentor",
        "force_agent": None,
        "force_agent_consumed": False,
        "task_breakdown": "",
        "agent_route_trace": ["knowledge_mentor"],
    }
    state.update(overrides)
    return state


def test_rule_based_route_does_not_repeat_completed_worker(monkeypatch):
    monkeypatch.setattr(
        chat_engine,
        "_rule_based_route",
        lambda state: ("knowledge_mentor", "知识讲解"),
    )
    monkeypatch.setattr(
        chat_engine,
        "_invoke_supervisor_llm",
        lambda state: (
            SupervisorDecision(
                next_agent="FINISH",
                routing_reason="信息已经充分",
                task_breakdown="",
            ),
            False,
        ),
    )

    result = chat_engine.supervisor_node(_state())

    assert result["next_agent"] == "FINISH"
    assert result["supervisor_entries"] == 2


def test_repeated_llm_worker_decision_is_forced_to_finish(monkeypatch):
    monkeypatch.setattr(chat_engine, "_rule_based_route", lambda state: None)
    monkeypatch.setattr(
        chat_engine,
        "_invoke_supervisor_llm",
        lambda state: (
            SupervisorDecision(
                next_agent="knowledge_mentor",
                routing_reason="再次讲解",
                task_breakdown="重复任务",
            ),
            False,
        ),
    )

    result = chat_engine.supervisor_node(_state())

    assert result["next_agent"] == "FINISH"
    assert "避免重复派发" in result["routing_reason"]
    assert result["agent_route_trace"] == []
