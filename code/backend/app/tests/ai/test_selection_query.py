from app.ai.chat_engine import _build_selection_prompt, _should_use_semantic_cache
from app.ai.chat_models import ChatRequest


def test_selection_prompt_requests_long_form_teaching_answer() -> None:
    request = ChatRequest(
        user_input="B树索引",
        selected_text="B树索引",
        surrounding_context="索引是提高查询性能的关键技术，B树索引最常用于数据库。",
        system_prompt='请用简白易懂的方式解释以下数据库概念："B树索引"',
    )

    prompt = _build_selection_prompt(request)

    assert "学生点击的划词操作要求" in prompt
    assert "450-800 字" in prompt
    assert "概念定位" in prompt
    assert "核心机制或原理" in prompt
    assert "不要只给一小段概括" in prompt
    assert "简短示例" not in prompt


def test_selection_prompt_keeps_summary_mode_but_avoids_one_line_answer() -> None:
    request = ChatRequest(
        user_input="事务处理",
        selected_text="事务处理",
        system_prompt='请总结以下内容的核心要点："事务处理"',
    )

    prompt = _build_selection_prompt(request)

    assert "4-6 条要点" in prompt
    assert "避免只输出一句短答" in prompt
    assert "450-800 字" not in prompt


def test_selection_query_bypasses_semantic_cache() -> None:
    selection_request = ChatRequest(
        user_input="B树索引",
        selected_text="B树索引",
    )
    normal_request = ChatRequest(user_input="B树索引")
    history_request = ChatRequest(
        user_input="B树索引",
        prior_turns=[{"user": "什么是索引", "assistant": "索引用于加速查询。"}],
    )

    assert not _should_use_semantic_cache(selection_request)
    assert _should_use_semantic_cache(normal_request)
    assert not _should_use_semantic_cache(history_request)
