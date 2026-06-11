"""Tests for DocumentIngestionPipeline with mocked Docling."""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from app.services.document_ingestion import DocumentIngestionPipeline


class _LegacyStub:
    def process_document_legacy(self, file_path: str):
        return [
            Document(
                page_content="legacy paragraph one " * 5,
                metadata={"source": "test.pdf"},
            )
        ]


@patch("app.services.document_ingestion._extract_with_docling")
def test_ingest_uses_docling_when_text_rich(mock_docling, tmp_path):
    mock_docling.return_value = (
        "# Title\n\n" + ("docling extracted text. " * 20),
        {"extraction_method": "docling", "docling": True},
    )
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    pipeline = DocumentIngestionPipeline(_LegacyStub())
    docs, meta = pipeline.ingest(str(pdf))

    assert docs
    assert meta["extraction_method"] == "docling"
    assert meta.get("preview_snippet")
    mock_docling.assert_called_once()


class _LegacyStubEmpty:
    def process_document_legacy(self, file_path: str):
        return []


@patch("app.services.document_ingestion._ocr_pdf_pages")
@patch("app.services.document_ingestion._extract_with_docling")
def test_ingest_ocr_fallback_for_scanned_pdf(mock_docling, mock_ocr, tmp_path):
    mock_docling.return_value = ("", {"extraction_method": "docling_error", "docling": False})
    mock_ocr.return_value = ("ocr text from scan " * 10, 2)

    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    pipeline = DocumentIngestionPipeline(_LegacyStubEmpty())
    docs, meta = pipeline.ingest(str(pdf))

    assert docs
    assert meta["extraction_method"] == "ocr"
    assert meta["ocr_pages"] == 2
