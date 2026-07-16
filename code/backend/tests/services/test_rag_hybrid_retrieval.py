import json

from langchain_core.documents import Document

from app.services.rag_service import RAGService


class HybridStore:
    def __init__(self, documents):
        self.documents = documents

    def get_documents(self, filter=None):
        course_id = None
        if filter:
            clauses = filter.get("$and", [filter])
            for clause in clauses:
                if "course_id" in clause:
                    course_id = clause["course_id"]
        return [
            doc
            for doc in self.documents
            if not course_id or doc.metadata.get("course_id") == course_id
        ]

    def similarity_search_with_scores(self, query, k, filter=None):
        # Deliberately wrong hash ranking: lexical retrieval must correct it.
        return [(doc, 0.9 - index * 0.1) for index, doc in enumerate(reversed(self.get_documents(filter)))]


class SemanticNoiseStore(HybridStore):
    def similarity_search_with_scores(self, query, k, filter=None):
        documents = self.get_documents(filter)
        if "量子" in query:
            return [(doc, 0.29 - index * 0.01) for index, doc in enumerate(documents)]
        return [(doc, 0.72 - index * 0.01) for index, doc in enumerate(documents)]


class EmptyRecordingStore:
    def __init__(self):
        self.filters = []

    def similarity_search_with_scores(self, query, k, filter=None):
        self.filters.append(filter)
        return []

    def get_documents(self, filter=None):
        return []


def _doc(content, source, course_id="course-a", kp="acid"):
    return Document(
        page_content=content,
        metadata={
            "scope": "system",
            "course_id": course_id,
            "file_id": source,
            "source": source,
            "chunk_id": 1,
            "chapter_title": "事务",
            "knowledge_point_ids": json.dumps([kp]),
            "source_url": "https://www.postgresql.org/docs/current/",
            "source_license": "PostgreSQL License",
        },
    )


def test_hash_fallback_uses_lexical_evidence_and_reports_degraded(monkeypatch):
    service = object.__new__(RAGService)
    service.vector_store = HybridStore(
        [
            _doc("事务具有原子性，一组操作全部完成或全部撤销", "transaction.md"),
            _doc("B+树索引适合范围检索", "index.md", kp="index"),
        ]
    )
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    results = service.query_knowledge_base("事务原子性", k=2, course_id="course-a")

    assert results[0]["source"] == "transaction.md"
    assert results[0]["retrieval_method"] == "lexical+hash_fallback"
    assert results[0]["semantic_retrieval"] is False


def test_hash_fallback_refuses_zero_overlap_and_isolates_course(monkeypatch):
    service = object.__new__(RAGService)
    service.vector_store = HybridStore(
        [
            _doc("事务具有原子性", "a.md", course_id="course-a"),
            _doc("量子纠缠与贝尔不等式", "b.md", course_id="course-b"),
        ]
    )
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    assert service.query_knowledge_base(
        "量子纠缠", k=4, course_id="course-a"
    ) == []
    assert service.query_knowledge_base(
        "原子性", k=4, course_id="course-b"
    ) == []


def test_unscoped_query_never_reads_system_or_legacy_course_chunks(monkeypatch):
    system_doc = _doc("未授权课程中的事务原子性", "secret.md", course_id="secret-course")
    legacy_doc = _doc("旧数据中的事务原子性", "legacy.md", course_id="secret-course")
    legacy_doc.metadata.pop("scope")
    service = object.__new__(RAGService)
    service.vector_store = HybridStore([system_doc, legacy_doc])
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    assert service.query_knowledge_base(
        "事务原子性", k=4, user_id="unregistered-user"
    ) == []


def test_prompt_scaffolding_does_not_hide_course_terms(monkeypatch):
    service = object.__new__(RAGService)
    service.vector_store = HybridStore(
        [_doc("事务原子性要求一组操作全部完成或全部撤销", "transaction.md")]
    )
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    results = service.query_knowledge_base(
        "请用一句话解释事务原子性，并说明依据来自哪一份课程资料。",
        k=4,
        course_id="course-a",
    )

    assert results
    assert results[0]["source"] == "transaction.md"


def test_uploaded_document_hash_search_requires_lexical_evidence(monkeypatch):
    relevant = _doc("事务原子性要求一组操作全部完成或全部撤销", "paper.pdf")
    relevant.metadata["file_id"] = "file-1"
    service = object.__new__(RAGService)
    service.vector_store = HybridStore([relevant])
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    results = service.search_uploaded_document(
        query="事务原子性",
        file_id="file-1",
        thread_id=None,
        user_id="user-1",
        is_admin=False,
    )
    unrelated = service.search_uploaded_document(
        query="量子纠缠贝尔不等式",
        file_id="file-1",
        thread_id=None,
        user_id="user-1",
        is_admin=False,
    )

    assert results
    assert results[0]["retrieval_method"] == "lexical+hash_fallback"
    assert results[0]["semantic_retrieval"] is False
    assert unrelated == []


def test_uploaded_document_search_never_crosses_owner_boundary(monkeypatch):
    private = _doc("事务原子性课程笔记", "private.pdf")
    private.metadata.update(
        {"file_id": "private-file", "scope": "thread", "owner_id": "user-a"}
    )
    service = object.__new__(RAGService)
    service.vector_store = HybridStore([private])
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    assert service.search_uploaded_document(
        query="事务原子性",
        file_id="private-file",
        thread_id=None,
        user_id="user-b",
        is_admin=False,
    ) == []
    assert service.search_uploaded_document(
        query="事务原子性",
        file_id="private-file",
        thread_id=None,
        user_id="user-a",
        is_admin=False,
    )


def test_thread_attachment_search_never_falls_back_to_file_only(monkeypatch):
    service = object.__new__(RAGService)
    service.vector_store = EmptyRecordingStore()
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    assert service.search_uploaded_document(
        query="事务原子性",
        file_id="file-1",
        thread_id="thread-a",
        user_id="user-a",
        is_admin=False,
        course_id="course-a",
    ) == []
    assert len(service.vector_store.filters) == 1
    assert "thread-a" in json.dumps(service.vector_store.filters[0])


def test_attachment_search_rechecks_file_and_thread_when_store_ignores_filter(
    monkeypatch,
):
    requested = _doc("事务原子性属于目标附件", "requested.pdf")
    requested.metadata.update(
        {
            "scope": "thread",
            "owner_id": "user-a",
            "file_id": "file-a",
            "thread_id": "thread-a",
        }
    )
    foreign_thread = _doc("事务原子性来自另一个对话", "foreign.pdf")
    foreign_thread.metadata.update(
        {
            "scope": "thread",
            "owner_id": "user-a",
            "file_id": "file-b",
            "thread_id": "thread-b",
        }
    )
    service = object.__new__(RAGService)
    service.vector_store = HybridStore([foreign_thread, requested])
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "hash")

    results = service.search_uploaded_document(
        query="事务原子性",
        file_id="file-a",
        thread_id="thread-a",
        user_id="user-a",
        is_admin=False,
        course_id="course-a",
    )

    assert [item["metadata"]["file_id"] for item in results] == ["file-a"]
    assert [item["metadata"]["thread_id"] for item in results] == ["thread-a"]


def test_semantic_course_search_does_not_reintroduce_filtered_noise(monkeypatch):
    service = object.__new__(RAGService)
    service.vector_store = SemanticNoiseStore(
        [_doc("事务原子性要求一组操作全部完成或全部撤销", "transaction.md")]
    )
    monkeypatch.setattr("app.services.rag_service.settings.EMBEDDINGS_PROVIDER", "ollama")

    assert service.query_knowledge_base(
        "量子纠缠贝尔不等式", k=4, course_id="course-a"
    ) == []
    results = service.query_knowledge_base(
        "事务原子性", k=4, course_id="course-a"
    )
    assert results
    assert results[0]["retrieval_method"] == "hybrid_semantic+lexical"
