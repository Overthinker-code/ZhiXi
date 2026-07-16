#!/usr/bin/env python3
"""Repeatably seed the compact Database Systems course knowledge base."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.vector_store import VectorStore  # noqa: E402

DATA_DIR = BACKEND_ROOT / "data" / "course_kb" / "database_systems"


def _split_markdown(text: str) -> list[tuple[str, str]]:
    """Split at level-2 headings while retaining a useful document title."""

    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    document_title = title_match.group(1).strip() if title_match else "课程资料"
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    chunks: list[tuple[str, str]] = []
    for section in sections:
        body = section.strip()
        if not body:
            continue
        heading = re.search(r"^##\s+(.+)$", body, re.MULTILINE)
        section_title = heading.group(1).strip() if heading else document_title
        chunks.append((section_title, body))
    return chunks


def seed_course_kb(data_dir: Path = DATA_DIR) -> dict:
    manifest = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))
    store = VectorStore()
    total_chunks = 0
    seeded_files = []
    seeded_at = datetime.now(timezone.utc).isoformat()

    for entry in manifest["files"]:
        path = data_dir / entry["path"]
        stable_file_id = f"course-kb:{manifest['course_id']}:{entry['path']}"
        store.delete_by_file_id(stable_file_id)
        documents = []
        for chunk_id, (section_title, content) in enumerate(
            _split_markdown(path.read_text(encoding="utf-8")), start=1
        ):
            metadata = {
                "file_id": stable_file_id,
                "source": entry["path"],
                "title": section_title,
                "chunk_id": chunk_id,
                "locator": f"{entry['chapter_title']} · {section_title}",
                "scope": "system",
                "owner_id": "",
                "type": entry["document_type"],
                "course_id": manifest["course_id"],
                "chapter_id": entry["chapter_id"],
                "chapter_title": entry["chapter_title"],
                "knowledge_point_ids": json.dumps(
                    entry["knowledge_point_ids"], ensure_ascii=False
                ),
                "source_url": entry["source_url"],
                "source_title": entry["source_title"],
                "source_license": entry["source_license"],
                "content_license": manifest["content_license"],
                "content_author": manifest["content_author"],
                "seeded_at": seeded_at,
            }
            documents.append(Document(page_content=content, metadata=metadata))
        store.add_documents(documents)
        total_chunks += len(documents)
        seeded_files.append(
            {"path": entry["path"], "file_id": stable_file_id, "chunks": len(documents)}
        )

    return {
        "course_id": manifest["course_id"],
        "embedding_provider": store.embeddings.__class__.__name__,
        "files": seeded_files,
        "total_chunks": total_chunks,
        "seeded_at": seeded_at,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    print(json.dumps(seed_course_kb(args.data_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
