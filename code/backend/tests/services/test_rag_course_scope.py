import io
import json
import asyncio
from uuid import uuid4

import pytest
from fastapi import UploadFile
from langchain_core.documents import Document

from app.services.rag_service import RAGService


class CourseVectorStore:
    def __init__(self, matches=None):
        self.matches = matches or []
        self.calls = []
        self.added = []

    def similarity_search_with_scores(self, query, k, filter=None):
        self.calls.append(filter)
        return list(self.matches)

    def add_documents(self, documents):
        self.added.extend(documents)


def _doc(content: str, course_id: str | None, source: str):
    metadata = {
        "scope": "personal",
        "owner_id": "user-1",
        "file_id": source,
        "source": source,
        "chunk_id": 1,
    }
    if course_id is not None:
        metadata["course_id"] = course_id
    return Document(page_content=content, metadata=metadata)


def test_course_query_never_returns_other_or_unscoped_chunks():
    service = object.__new__(RAGService)
    service.vector_store = CourseVectorStore(
        [
            (_doc("target evidence", "course-a", "a.md"), 0.91),
            (_doc("other evidence", "course-b", "b.md"), 0.99),
            (_doc("legacy evidence", None, "legacy.md"), 0.98),
        ]
    )

    results = service.query_knowledge_base(
        "transaction",
        k=4,
        user_id="user-1",
        course_id="course-a",
    )

    assert [item["source"] for item in results] == ["a.md"]
    assert service.vector_store.calls
    assert all("course-a" in json.dumps(call) for call in service.vector_store.calls)


def test_course_query_returns_empty_when_only_cross_course_evidence_exists():
    service = object.__new__(RAGService)
    service.vector_store = CourseVectorStore(
        [
            (_doc("other evidence", "course-b", "b.md"), 0.99),
            (_doc("legacy evidence", None, "legacy.md"), 0.98),
        ]
    )

    assert service.query_knowledge_base(
        "transaction", k=4, user_id="user-1", course_id="course-a"
    ) == []


class PreviewProcessor:
    def extract_text(self, _path):
        return "ACID transaction evidence"

    def get_doc_type(self, _path):
        return "txt"

    def split_text(self, text, metadata):
        return [Document(page_content=text, metadata=dict(metadata))]


def test_preview_and_commit_preserve_course_metadata(tmp_path):
    service = object.__new__(RAGService)
    service.upload_dir = str(tmp_path)
    service.preview_dir = str(tmp_path / "previews")
    service.doc_processor = PreviewProcessor()
    service.vector_store = CourseVectorStore()
    (tmp_path / "previews").mkdir()
    upload = UploadFile(filename="acid.txt", file=io.BytesIO(b"ACID transaction evidence"))

    async def collect_events():
        return [
            event
            async for event in service.stream_preview(
                upload,
                owner_id="user-1",
                course_id="course-a",
                chapter_id="chapter-3",
                knowledge_point_ids=["acid", "transaction"],
            )
        ]

    events = asyncio.run(collect_events())
    ready = events[-1]
    assert ready["course_id"] == "course-a"
    assert ready["chapter_id"] == "chapter-3"
    assert ready["knowledge_point_ids"] == ["acid", "transaction"]

    result = service.commit_preview(ready["file_id"], user_id="user-1")

    assert result["status"] == "success"
    assert result["course_id"] == "course-a"
    metadata = service.vector_store.added[0].metadata
    assert metadata["course_id"] == "course-a"
    assert metadata["chapter_id"] == "chapter-3"
    assert json.loads(metadata["knowledge_point_ids"]) == ["acid", "transaction"]


def test_preview_cache_rejects_traversal_and_symlink(tmp_path):
    service = object.__new__(RAGService)
    service.preview_dir = str(tmp_path / "previews")
    (tmp_path / "previews").mkdir()

    with pytest.raises(ValueError, match="Invalid preview file_id"):
        service._preview_cache_path("../../outside")

    file_id = str(uuid4())
    target = tmp_path / "outside.json"
    target.write_text('{"secret": true}', encoding="utf-8")
    (tmp_path / "previews" / f"{file_id}.json").symlink_to(target)
    with pytest.raises(ValueError, match="Invalid preview cache path"):
        service._preview_cache_path(file_id)
