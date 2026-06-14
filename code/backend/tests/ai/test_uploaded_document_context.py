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


def test_reasoning_chunk_prefers_model_reasoning_channel():
    chunk = AIMessageChunk(
        content="final text",
        additional_kwargs={"reasoning_content": "real model analysis"},
    )
    assert chat_engine._reasoning_chunk_text(chunk) == "real model analysis"
