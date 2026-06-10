"""Tests for vector store persistence compatibility."""

from unittest.mock import MagicMock

from langchain_core.documents import Document

from app.services.vector_store import VectorStore


def test_persist_if_supported_skips_missing_method():
    db = MagicMock()
    del db.persist
    db.add_documents = MagicMock()
    vs = VectorStore.__new__(VectorStore)
    vs.db = db
    vs.add_documents([Document(page_content="x", metadata={})])
    db.add_documents.assert_called_once()


def test_persist_if_supported_calls_legacy_method():
    db = MagicMock()
    db.persist = MagicMock()
    vs = VectorStore.__new__(VectorStore)
    vs.db = db
    VectorStore._persist_if_supported(db)
    db.persist.assert_called_once()
