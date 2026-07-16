from app.ai import chat_engine, chat_tools
from app.ai.chat_models import ChatRequest


def test_rag_context_passes_course_scope_to_retrieval(monkeypatch):
    calls = []

    def fake_query(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(chat_engine.rag_service, "query_knowledge_base", fake_query)

    message, results = chat_engine._build_rag_context(
        ChatRequest(
            user_input="解释 ACID",
            user_id="user-1",
            context_refs={
                "courseId": "course-a",
                "chapterId": "chapter-3",
                "knowledgePointIds": ["acid"],
            },
        )
    )

    assert results == []
    assert calls[0]["course_id"] == "course-a"
    assert "未检索到" in str(message.content)


def test_langgraph_knowledge_tool_closes_over_course_context(monkeypatch):
    calls = []

    def fake_query(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(chat_tools.rag_service, "query_knowledge_base", fake_query)
    tool = chat_tools.make_query_knowledge_base_tool(
        "user-1",
        False,
        4,
        {"courseId": "course-a", "chapterId": "chapter-3"},
    )

    tool.invoke({"question": "解释 ACID"})

    assert calls[0]["course_id"] == "course-a"


def test_generic_chat_keeps_unscoped_retrieval(monkeypatch):
    calls = []

    def fake_query(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(chat_engine.rag_service, "query_knowledge_base", fake_query)
    chat_engine._build_rag_context(ChatRequest(user_input="什么是数据库"))

    assert calls[0]["course_id"] is None


def test_course_reader_uses_single_call_direct_path_for_bounded_rag():
    request = ChatRequest(
        user_input="解释 ACID",
        route_context={"mode": "tutor"},
        force_agent="doc_researcher",
        active_tools=["knowledge_base"],
        tool_mode="chat",
    )
    assert chat_engine._should_direct_stream_answer(request) is True


def test_course_reader_keeps_graph_path_when_extra_tool_is_enabled():
    request = ChatRequest(
        user_input="检索课程和网页",
        route_context={"mode": "tutor"},
        force_agent="doc_researcher",
        active_tools=["knowledge_base", "web_search"],
        tool_mode="chat",
    )
    assert chat_engine._should_direct_stream_answer(request) is False
