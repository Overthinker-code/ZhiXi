#!/usr/bin/env python3
"""Seed the Software Engineering course knowledge base from 原始资料.

The raw folder already contains curated Markdown notes, exercises, JSONL chunks,
PPT PDFs, and textbook files. This script favors the curated JSONL/Markdown
assets for high-signal retrieval and indexes large PDF/PPT files as source
documents so the system has an auditable complete course document set without
making every startup parse hundreds of megabytes.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.vector_store import VectorStore  # noqa: E402

COURSE_ID = "c1111111-1111-4111-9111-111111111107"
COURSE_TITLE = "软件工程导论"
RAW_DIR = REPO_ROOT / "原始资料"


def _jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _safe_rel(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _chapter_id(value: str) -> str:
    match = re.search(r"(?:第)?\s*(\d{1,2})\s*(?:章|[.\-_])", value or "")
    if match:
        return f"ch{int(match.group(1)):02d}"
    match = re.search(r"SE-(\d{2})-", value or "")
    if match:
        return f"ch{int(match.group(1)):02d}"
    return "course-general"


def _chapter_title_from_file(path_or_title: str, chapter_index: dict[str, str]) -> str:
    chapter_id = _chapter_id(path_or_title)
    return chapter_index.get(chapter_id) or path_or_title or COURSE_TITLE


def _split_markdown_by_heading(path: Path) -> list[tuple[str, str]]:
    text = _read_text(path)
    sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    document_title = title_match.group(1).strip() if title_match else path.stem
    out: list[tuple[str, str]] = []
    for section in sections:
        body = section.strip()
        if not body:
            continue
        heading = re.search(r"^##\s+(.+)$", body, re.MULTILINE)
        title = heading.group(1).strip() if heading else document_title
        out.append((title, body))
    return out


def _load_chapter_index() -> dict[str, str]:
    path = RAW_DIR / "知识库表格" / "chapter_index.csv"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            chapter_no = str(row.get("章号") or "").strip()
            title = str(row.get("原章节标题") or "").strip()
            if chapter_no and title:
                out[f"ch{int(chapter_no):02d}"] = title
    return out


def _find_key(row: dict[str, Any], *needles: str) -> str:
    for key in row:
        if all(needle in key for needle in needles):
            return key
    return ""


def _base_metadata(
    *,
    file_id: str,
    source: str,
    document_type: str,
    chunk_id: int | str,
    chapter_id: str = "course-general",
    chapter_title: str = COURSE_TITLE,
    knowledge_points: list[str] | None = None,
    seeded_at: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = {
        "file_id": file_id,
        "source": source,
        "title": chapter_title,
        "chunk_id": chunk_id,
        "locator": f"{chapter_title} / {source}",
        "scope": "system",
        "owner_id": "",
        "type": document_type,
        "course_id": COURSE_ID,
        "course_title": COURSE_TITLE,
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "knowledge_point_ids": json.dumps(knowledge_points or [], ensure_ascii=False),
        "source_url": _safe_rel(REPO_ROOT / source) if not source.startswith("course-kb:") else source,
        "source_title": source,
        "source_license": "课程自建资料/课堂资料，仅用于本地课程知识库",
        "content_license": "课程自建资料",
        "content_author": "智屿项目组",
        "seeded_at": seeded_at,
    }
    if extra:
        metadata.update(extra)
    return metadata


def _delete_file_ids(store: VectorStore, file_ids: set[str]) -> None:
    for file_id in sorted(file_ids):
        store.delete_by_file_id(file_id)


def seed_software_engineering_course_kb(raw_dir: Path = RAW_DIR) -> dict[str, Any]:
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw course folder not found: {raw_dir}")

    store = VectorStore()
    seeded_at = datetime.now(timezone.utc).isoformat()
    chapter_index = _load_chapter_index()
    documents_by_file: dict[str, list[Document]] = defaultdict(list)

    outline_path = raw_dir / "course_outline.md"
    if outline_path.exists():
        file_id = f"course-kb:{COURSE_ID}:outline"
        for idx, (title, content) in enumerate(_split_markdown_by_heading(outline_path), start=1):
            documents_by_file[file_id].append(
                Document(
                    page_content=content,
                    metadata=_base_metadata(
                        file_id=file_id,
                        source=_safe_rel(outline_path),
                        document_type="course_outline",
                        chunk_id=idx,
                        chapter_id=_chapter_id(title),
                        chapter_title=title,
                        knowledge_points=[title],
                        seeded_at=seeded_at,
                    ),
                )
            )

    chunks_path = raw_dir / "入库数据" / "chunks.jsonl"
    if chunks_path.exists():
        for row in _jsonl(chunks_path):
            chunk_id = str(row.get("chunk_id") or "")
            source_file = str(row.get("source_file") or chunks_path.name)
            chapter_title = str(row.get("source_chapter") or "")
            chapter_id = _chapter_id(chunk_id or source_file or chapter_title)
            knowledge_point = str(row.get("knowledge_point") or "").strip()
            file_id = f"course-kb:{COURSE_ID}:notes:{source_file}"
            documents_by_file[file_id].append(
                Document(
                    page_content=str(row.get("content") or "").strip(),
                    metadata=_base_metadata(
                        file_id=file_id,
                        source=source_file,
                        document_type="lecture_notes",
                        chunk_id=len(documents_by_file[file_id]) + 1,
                        chapter_id=chapter_id,
                        chapter_title=chapter_title or _chapter_title_from_file(source_file, chapter_index),
                        knowledge_points=[knowledge_point] if knowledge_point else [],
                        seeded_at=seeded_at,
                        extra={"original_chunk_id": chunk_id} if chunk_id else None,
                    ),
                )
            )

    questions_path = raw_dir / "入库数据" / "questions.jsonl"
    if questions_path.exists():
        for row in _jsonl(questions_path):
            qid_key = _find_key(row, "题目", "编号")
            chapter_key = _find_key(row, "来源", "章节")
            kp_key = _find_key(row, "知识点")
            type_key = _find_key(row, "题型")
            stem_key = _find_key(row, "题干")
            answer_key = _find_key(row, "答案")
            source_key = _find_key(row, "来源", "文件")
            qid = str(row.get(qid_key) or f"Q-{len(documents_by_file) + 1}")
            source_file = str(row.get(source_key) or questions_path.name)
            chapter_title = str(row.get(chapter_key) or _chapter_title_from_file(source_file, chapter_index))
            knowledge_point = str(row.get(kp_key) or "").strip()
            question_type = str(row.get(type_key) or "").strip()
            stem = str(row.get(stem_key) or "").strip()
            answer = str(row.get(answer_key) or "").strip()
            content = (
                f"题目编号：{qid}\n"
                f"题型：{question_type}\n"
                f"知识点：{knowledge_point}\n"
                f"题干：{stem}\n\n"
                f"答案与解析：{answer}"
            ).strip()
            file_id = f"course-kb:{COURSE_ID}:exercises:{source_file}"
            documents_by_file[file_id].append(
                Document(
                    page_content=content,
                    metadata=_base_metadata(
                        file_id=file_id,
                        source=source_file,
                        document_type="exercise_answers",
                        chunk_id=len(documents_by_file[file_id]) + 1,
                        chapter_id=_chapter_id(qid or source_file),
                        chapter_title=chapter_title,
                        knowledge_points=[knowledge_point] if knowledge_point else [],
                        seeded_at=seeded_at,
                        extra={"original_question_id": qid} if qid else None,
                    ),
                )
            )

    ppt_files = sorted((raw_dir / "PPT").glob("*.pdf"))
    ppt_file_id = f"course-kb:{COURSE_ID}:ppt-index"
    for idx, path in enumerate(ppt_files, start=1):
        title = path.stem
        content = (
            f"PPT课件：{title}\n"
            f"课程：{COURSE_TITLE}\n"
            f"原始文件：{_safe_rel(path)}\n"
            "用途：作为软件工程导论课程的课堂演示资料、案例补充或专题讲解材料。"
        )
        documents_by_file[ppt_file_id].append(
            Document(
                page_content=content,
                metadata=_base_metadata(
                    file_id=ppt_file_id,
                    source=_safe_rel(path),
                    document_type="ppt_index",
                    chunk_id=idx,
                    chapter_title="PPT课件资料索引",
                    knowledge_points=[title],
                    seeded_at=seeded_at,
                ),
            )
        )

    textbook_files = sorted((raw_dir / "教材PDF").glob("*"))
    textbook_file_id = f"course-kb:{COURSE_ID}:textbook-index"
    for idx, path in enumerate(textbook_files, start=1):
        if path.name.startswith("~$") or path.suffix.lower() not in {".pdf", ".docx", ".doc"}:
            continue
        content = (
            f"教材/参考书：{path.stem}\n"
            f"课程：{COURSE_TITLE}\n"
            f"原始文件：{_safe_rel(path)}\n"
            "用途：作为软件工程导论课程的教材、学习辅导或习题讲解参考资料。"
        )
        documents_by_file[textbook_file_id].append(
            Document(
                page_content=content,
                metadata=_base_metadata(
                    file_id=textbook_file_id,
                    source=_safe_rel(path),
                    document_type="textbook_index",
                    chunk_id=idx,
                    chapter_title="教材与参考资料索引",
                    knowledge_points=[path.stem],
                    seeded_at=seeded_at,
                ),
            )
        )

    file_ids = set(documents_by_file)
    _delete_file_ids(store, file_ids)
    seeded_files = []
    total_chunks = 0
    for file_id, docs in sorted(documents_by_file.items()):
        docs = [doc for doc in docs if (doc.page_content or "").strip()]
        if not docs:
            continue
        store.add_documents(docs)
        total_chunks += len(docs)
        seeded_files.append({"file_id": file_id, "chunks": len(docs)})

    return {
        "course_id": COURSE_ID,
        "course_title": COURSE_TITLE,
        "embedding_provider": store.embeddings.__class__.__name__,
        "files": seeded_files,
        "total_chunks": total_chunks,
        "source_counts": {
            "outline": int(outline_path.exists()),
            "knowledge_chunks": len(_jsonl(chunks_path)) if chunks_path.exists() else 0,
            "questions": len(_jsonl(questions_path)) if questions_path.exists() else 0,
            "ppt_pdfs": len(ppt_files),
            "textbook_files": len([p for p in textbook_files if not p.name.startswith("~$")]),
        },
        "seeded_at": seeded_at,
    }


def main() -> None:
    print(json.dumps(seed_software_engineering_course_kb(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
