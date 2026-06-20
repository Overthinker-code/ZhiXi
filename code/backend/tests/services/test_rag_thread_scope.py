from langchain_core.documents import Document

from app.services.rag_service import RAGService


class FakeVectorStore:
    def __init__(self):
        self.calls = []

    def similarity_search_with_scores(self, query, k, filter=None):
        self.calls.append(filter)
        if filter == {"scope": "system"}:
            return []
        if filter == {
            "$and": [
                {"scope": "personal"},
                {"owner_id": "user-1"},
            ]
        }:
            return []
        return [
            (
                Document(
                    page_content="private thread evidence from another chat",
                    metadata={
                        "scope": "thread",
                        "owner_id": "user-1",
                        "thread_id": "other-thread",
                        "file_id": "thread-file",
                        "source": "other-thread.pdf",
                        "chunk_id": 1,
                    },
                ),
                0.99,
            ),
            (
                Document(
                    page_content="personal reusable course note",
                    metadata={
                        "scope": "personal",
                        "owner_id": "user-1",
                        "file_id": "personal-file",
                        "source": "my-note.md",
                        "chunk_id": 2,
                    },
                ),
                0.88,
            ),
        ]


def test_query_knowledge_base_fallback_excludes_thread_uploads():
    service = object.__new__(RAGService)
    service.vector_store = FakeVectorStore()

    results = service.query_knowledge_base(
        "course concept",
        k=2,
        user_id="user-1",
        is_admin=False,
    )

    assert [item["source"] for item in results] == ["my-note.md"]
    assert all(item["metadata"].get("scope") != "thread" for item in results)
