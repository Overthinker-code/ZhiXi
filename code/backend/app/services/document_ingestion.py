"""Document ingestion: Docling primary, legacy extractors + OCR fallback."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from docling.document_converter import DocumentConverter

    _DOCLING_AVAILABLE = True
except Exception:
    DocumentConverter = None  # type: ignore
    _DOCLING_AVAILABLE = False

try:
    import fitz  # pymupdf
except Exception:
    fitz = None  # type: ignore

from app.services.vision_client import ocr_text_from_image_bytes


def _split_text(text: str, metadata: dict[str, Any]) -> list[Document]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        length_function=len,
    )
    return splitter.create_documents([text], metadatas=[metadata])


def _extract_with_docling(file_path: str) -> tuple[str, dict[str, Any]]:
    if not _DOCLING_AVAILABLE or DocumentConverter is None:
        return "", {"extraction_method": "unavailable", "docling": False}
    try:
        converter = DocumentConverter()
        result = converter.convert(file_path)
        md = result.document.export_to_markdown() or ""
        return md.strip(), {"extraction_method": "docling", "docling": True}
    except Exception as exc:
        logger.warning("Docling failed for %s: %s", file_path, exc)
        return "", {"extraction_method": "docling_error", "docling": False, "error": str(exc)[:200]}


def _ocr_pdf_pages(file_path: str, max_pages: int = 8) -> tuple[str, int]:
    if fitz is None:
        return "", 0
    parts: list[str] = []
    ocr_pages = 0
    try:
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            text = ocr_text_from_image_bytes(pix.tobytes("png"))
            if text.strip():
                parts.append(text.strip())
                ocr_pages += 1
        doc.close()
    except Exception as exc:
        logger.warning("PDF OCR fallback failed: %s", exc)
    return "\n\n".join(parts), ocr_pages


class DocumentIngestionPipeline:
    """Unified ingest: Docling -> legacy fallback -> OCR for scanned PDFs."""

    def __init__(self, legacy_processor: Any) -> None:
        self._legacy = legacy_processor

    def ingest(self, file_path: str) -> tuple[list[Document], dict[str, Any]]:
        ext = Path(file_path).suffix.lower()
        meta: dict[str, Any] = {
            "source": Path(file_path).name,
            "type": ext.lstrip(".") or "unknown",
            "extraction_method": "legacy",
            "ocr_pages": 0,
        }

        text = ""
        if ext in {".pdf", ".docx", ".doc", ".pptx", ".ppt"}:
            text, doc_meta = _extract_with_docling(file_path)
            meta.update(doc_meta)

        docs: list[Document] = []
        if text and len(text.strip()) >= 32:
            meta["extraction_method"] = meta.get("extraction_method") or "docling"
            docs = _split_text(text, meta)
        else:
            try:
                docs = self._legacy.process_document_legacy(file_path)
                if docs:
                    meta["extraction_method"] = "legacy"
                    for d in docs:
                        d.metadata = {**(d.metadata or {}), **meta}
            except Exception as exc:
                logger.warning("Legacy extract failed: %s", exc)
                docs = []

        combined = "\n".join((d.page_content or "") for d in docs).strip()
        if ext == ".pdf" and len(combined) < 32:
            ocr_text, ocr_pages = _ocr_pdf_pages(file_path)
            meta["ocr_pages"] = ocr_pages
            if ocr_text.strip():
                meta["extraction_method"] = "ocr"
                docs = _split_text(ocr_text, meta)

        if not docs:
            raise ValueError(
                "文档未提取到可读文本（可能是扫描版 PDF/图片型文档）。请上传可复制文本版，或先做 OCR。"
            )

        preview = (docs[0].page_content or "")[:280] if docs else ""
        meta["preview_snippet"] = preview
        meta["chunk_count"] = len(docs)
        for d in docs:
            d.metadata = {**(d.metadata or {}), **meta}
        return docs, meta
