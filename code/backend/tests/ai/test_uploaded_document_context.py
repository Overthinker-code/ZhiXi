from langchain_core.messages import AIMessageChunk

from app.ai import chat_engine
from app.ai.chat_models import ChatRequest


def test_current_file_context_is_injected_before_general_rag(monkeypatch):
    monkeypatch.setattr(
        chat_engine.rag_service,
        "search_uploaded_document",
        lambda **_kwargs: [
            {
                "content": "paper sentinel motivation and method",
                "source": "paper.pdf",
                "chunk_id": 2,
                "score": 0.98,
                "metadata": {"file_id": "file-1", "thread_id": "thread-1"},
            }
        ],
    )
    monkeypatch.setattr(
        chat_engine.rag_service,
        "query_knowledge_base",
        lambda **_kwargs: [
            {
                "content": "general course material",
                "source": "course.md",
                "chunk_id": 1,
                "score": 0.8,
                "metadata": {},
            }
        ],
    )

    message, results = chat_engine._build_rag_context(
        ChatRequest(
            user_input="总结论文 motivation 和 method",
            thread_id="thread-1",
            user_id="user-1",
            current_file_id="file-1",
            file_name="paper.pdf",
        )
    )

    assert results[0]["source"] == "paper.pdf"
    assert results[0]["context_scope"] == "uploaded_document"
    assert results[0]["citation_id"] == 1
    assert "paper sentinel motivation and method" in str(message.content)


def test_current_file_routes_to_document_researcher_without_keyword_hint():
    route = chat_engine._rule_based_route(
        {
            "messages": [chat_engine.HumanMessage(content="帮我判断这部分最重要的三个点")],
            "tool_mode": "chat",
            "active_tools": ["knowledge_base"],
            "current_file_id": "file-1",
            "current_file_name": "paper.pdf",
            "image_context": "",
        }
    )

    assert route is not None
    assert route[0] == "doc_researcher"
    assert "paper.pdf" in route[1]


def test_reasoning_chunk_prefers_model_reasoning_channel():
    chunk = AIMessageChunk(
        content="final text",
        additional_kwargs={"reasoning_content": "real model analysis"},
    )
    assert chat_engine._reasoning_chunk_text(chunk) == "real model analysis"


def test_document_reasoning_stream_uses_native_channels_and_citations(monkeypatch):
    class FakeModel:
        def stream(self, messages):
            assert "禁止使用" in str(messages[0].content)
            assert "模板开场" in str(messages[0].content)
            yield AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": "好的，我现在需要处理用户上传的论文。"
                },
            )
            yield AIMessageChunk(
                content="",
                additional_kwargs={
                    "reasoning_content": (
                        "好的，我现在需要处理用户上传的论文。"
                        "首先，我需要仔细阅读文档。"
                        "论文证据表明，$W=A^T A$ 建模二阶注意力。"
                    )
                },
            )
            yield AIMessageChunk(content="结论见 $W=A^T A$ [citation:1]。")

    monkeypatch.setattr(
        chat_engine.ChatModelFactory,
        "create",
        lambda **_kwargs: FakeModel(),
    )
    request = ChatRequest(
        user_input="讲解论文方法",
        thread_id="thread-1",
        user_id="user-1",
        current_file_id="file-1",
        file_name="paper.pdf",
        reasoning_enabled=True,
    )
    rag_results = [
        {
            "content": "paper method evidence",
            "source": "paper.pdf",
            "chunk_id": 3,
            "score": 0.98,
            "citation_id": 1,
            "context_scope": "uploaded_document",
            "metadata": {"file_id": "file-1"},
        }
    ]

    events = list(
        chat_engine._stream_grounded_document_answer(
            request,
            chat_engine.SystemMessage(content="[citation:1] paper method evidence"),
            rag_results,
        )
    )

    reasoning = "".join(
        event["content"] for event in events if event["type"] == "reasoning_token"
    )
    assert reasoning == "论文证据表明，$W=A^T A$ 建模二阶注意力。"
    assert "好的，我现在需要" not in reasoning
    assert "首先，我需要" not in reasoning
    assert any(event["type"] == "token" for event in events)
    assert events[-1]["grounding_mode"] == "rag"
    assert events[-1]["citations"][0]["source"] == "paper.pdf"


def test_document_reasoning_stream_flushes_meaningful_partial_sentence(monkeypatch):
    class FakeModel:
        def stream(self, _messages):
            yield AIMessageChunk(
                content="",
                additional_kwargs={"reasoning_content": "文档证据显示方法复杂度降低"},
            )
            yield AIMessageChunk(content="最终回答。")

    monkeypatch.setattr(
        chat_engine.ChatModelFactory,
        "create",
        lambda **_kwargs: FakeModel(),
    )
    events = list(
        chat_engine._stream_grounded_document_answer(
            ChatRequest(
                user_input="讲解论文",
                current_file_id="file-1",
                reasoning_enabled=True,
            ),
            chat_engine.SystemMessage(content="paper evidence"),
            [],
        )
    )

    reasoning = "".join(
        event["content"] for event in events if event["type"] == "reasoning_token"
    )
    assert reasoning == "文档证据显示方法复杂度降低"
