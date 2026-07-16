from typing import List, Optional, AsyncIterator
import asyncio
import os
import uuid
import json
import re
from pathlib import Path
from datetime import datetime, timezone

from fastapi import UploadFile
import aiofiles
from langchain_core.documents import Document

from app.core.config import settings
from app.core.upload_security import read_upload_limited
from .document_processor import DocumentProcessor
from .vector_store import VectorStore


class RAGService:
    _LEXICAL_QUERY_STOP_TEXT = (
        "请帮我请你能否可以一下用一句话简短解释说明概括回答告诉我"
        "并说明依据来自哪一份课程资料课件讲义文档来源引用"
        "什么是什么为什么怎么如何相关关于当前这个知识点内容"
    )
    def __init__(self, upload_dir: Optional[str] = None, vector_db_dir: Optional[str] = None):
        self.upload_dir = upload_dir or settings.RAG_UPLOAD_DIR
        self.vector_db_dir = vector_db_dir or settings.CHROMA_DB_PATH
        self.preview_dir = os.path.join(self.upload_dir, "previews")

        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.preview_dir, exist_ok=True)

        self.doc_processor = DocumentProcessor()
        self.vector_store = VectorStore(persist_directory=self.vector_db_dir)

    @staticmethod
    def _normalize_scope(scope: Optional[str]) -> str:
        normalized = (scope or "system").strip().lower()
        if normalized not in {"system", "personal", "thread"}:
            raise ValueError(f"Unsupported scope: {scope}")
        return normalized

    @staticmethod
    def _normalize_scope_filter(scope_filter: Optional[str]) -> str:
        normalized = (scope_filter or "all").strip().lower()
        if normalized not in {"all", "system", "personal", "thread"}:
            raise ValueError(f"Unsupported scope filter: {scope_filter}")
        return normalized

    @staticmethod
    def _normalize_owner_id(owner_id: Optional[str]) -> str:
        return (owner_id or "").strip()

    def _is_visible_to_user(
        self, metadata: dict, user_id: Optional[str], is_admin: bool
    ) -> bool:
        scope = self._normalize_scope(metadata.get("scope"))
        if scope == "system":
            return True
        if scope == "thread":
            owner_id = self._normalize_owner_id(metadata.get("owner_id"))
            return bool(user_id) and owner_id == self._normalize_owner_id(user_id)
        owner_id = self._normalize_owner_id(metadata.get("owner_id"))
        return bool(user_id) and owner_id == self._normalize_owner_id(user_id)

    def _is_visible_to_knowledge_query(
        self, metadata: dict, user_id: Optional[str], is_admin: bool
    ) -> bool:
        # Thread-scoped uploads are only authoritative through
        # search_uploaded_document(current_file_id). Treating them as normal
        # knowledge-base fallback results can leak a user's other conversations.
        if self._normalize_scope(metadata.get("scope")) == "thread":
            return False
        return self._is_visible_to_user(metadata, user_id, is_admin)

    def _can_manage_file(
        self, metadata: dict, user_id: Optional[str], is_admin: bool
    ) -> bool:
        if is_admin:
            return True
        scope = self._normalize_scope(metadata.get("scope"))
        if scope == "system":
            return False
        if scope == "thread":
            owner_id = self._normalize_owner_id(metadata.get("owner_id"))
            return bool(user_id) and owner_id == self._normalize_owner_id(user_id)
        owner_id = self._normalize_owner_id(metadata.get("owner_id"))
        return bool(user_id) and owner_id == self._normalize_owner_id(user_id)

    def _build_search_filters(
        self,
        *,
        user_id: Optional[str],
        filter_type: Optional[str],
        course_id: Optional[str] = None,
    ) -> List[Optional[dict]]:
        owner_id = self._normalize_owner_id(user_id)
        filters: List[dict] = []

        def build_where(**kwargs) -> dict:
            clauses = [{key: value} for key, value in kwargs.items() if value not in (None, "")]
            if not clauses:
                return {}
            if len(clauses) == 1:
                return clauses[0]
            return {"$and": clauses}

        # System chunks are course content, not a global public corpus. Without
        # an explicit course boundary only the caller's own personal documents
        # may participate. This also quarantines legacy chunks whose missing
        # scope normalizes to ``system``.
        if course_id:
            filters.append(
                build_where(scope="system", type=filter_type, course_id=course_id)
            )

        if owner_id:
            filters.append(
                build_where(
                    scope="personal",
                    owner_id=owner_id,
                    type=filter_type,
                    course_id=course_id,
                )
            )

        return filters

    @staticmethod
    def _doc_match_key(doc: Document) -> tuple:
        metadata = dict(doc.metadata or {})
        return (
            str(metadata.get("file_id") or ""),
            int(metadata.get("chunk_id") or 0),
            str(metadata.get("source") or ""),
            doc.page_content[:128],
        )

    @staticmethod
    def _lexical_tokens(text: str) -> set[str]:
        """Tokenize Chinese and English text without pretending it is semantic."""

        normalized = re.sub(r"\s+", " ", (text or "").lower()).strip()
        terms = set(re.findall(r"[a-z0-9_+.-]{2,}", normalized))
        for run in re.findall(r"[\u4e00-\u9fff]+", normalized):
            if len(run) <= 2:
                terms.add(run)
            else:
                terms.update(run[i : i + 2] for i in range(len(run) - 1))
        return terms

    @classmethod
    def _lexical_query_tokens(cls, text: str) -> set[str]:
        terms = cls._lexical_tokens(text)
        stop_terms = cls._lexical_tokens(cls._LEXICAL_QUERY_STOP_TEXT)
        filtered = terms - stop_terms
        return filtered or terms

    @classmethod
    def _lexical_score(cls, query: str, doc: Document) -> float:
        query_terms = cls._lexical_query_tokens(query)
        if not query_terms:
            return 0.0
        metadata = dict(doc.metadata or {})
        metadata_text = " ".join(
            str(metadata.get(key) or "")
            for key in ("title", "chapter_title", "knowledge_point_ids", "source")
        )
        body_overlap = len(query_terms & cls._lexical_tokens(doc.page_content)) / len(query_terms)
        metadata_overlap = len(query_terms & cls._lexical_tokens(metadata_text)) / len(query_terms)
        phrase_bonus = 0.15 if query.strip().lower() in doc.page_content.lower() else 0.0
        return min(1.0, body_overlap * 0.75 + metadata_overlap * 0.35 + phrase_bonus)

    def _lexical_matches(
        self, *, query: str, where: Optional[dict], limit: int
    ) -> List[tuple[Document, float]]:
        get_documents = getattr(self.vector_store, "get_documents", None)
        if not callable(get_documents):
            return []
        scored = [
            (doc, self._lexical_score(query, doc))
            for doc in get_documents(filter=where)
        ]
        return sorted(
            (item for item in scored if item[1] > 0),
            key=lambda item: item[1],
            reverse=True,
        )[:limit]

    async def process_uploaded_file(
        self,
        file: UploadFile,
        *,
        scope: str = "personal",
        owner_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        course_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        knowledge_point_ids: Optional[List[str]] = None,
    ) -> dict:
        if not file.filename:
            raise ValueError("Missing file name")

        normalized_scope = self._normalize_scope(scope)
        normalized_owner_id = self._normalize_owner_id(owner_id)
        normalized_course_id = str(course_id or "").strip()
        normalized_chapter_id = str(chapter_id or "").strip()
        normalized_knowledge_point_ids = [
            str(item).strip() for item in (knowledge_point_ids or []) if str(item).strip()
        ]

        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{file_id}{ext}"
        file_path = os.path.join(self.upload_dir, temp_filename)

        try:
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await read_upload_limited(file)
                await out_file.write(content)
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        file_size = len(content)
        created_at = datetime.now(timezone.utc).isoformat()

        try:
            documents = await asyncio.to_thread(
                self.doc_processor.process_document, file_path
            )
            non_empty = [
                d for d in documents if (d.page_content or "").strip()
            ]
            if not non_empty:
                raise ValueError(
                    "文档未提取到可读文本（可能是扫描版 PDF/图片型文档）。请上传可复制文本版，或先做 OCR。"
                )
            documents = non_empty

            ingest_meta = dict(documents[0].metadata or {})

            for idx, doc in enumerate(documents):
                metadata = dict(doc.metadata or {})
                metadata["file_id"] = file_id
                metadata["source"] = file.filename
                metadata["chunk_id"] = idx + 1
                metadata["file_size"] = file_size
                metadata["created_at"] = created_at
                metadata["scope"] = normalized_scope
                metadata["owner_id"] = normalized_owner_id
                if normalized_course_id:
                    metadata["course_id"] = normalized_course_id
                if normalized_chapter_id:
                    metadata["chapter_id"] = normalized_chapter_id
                if normalized_knowledge_point_ids:
                    # Chroma metadata values must be scalar. JSON preserves the
                    # complete list without relying on delimiter conventions.
                    metadata["knowledge_point_ids"] = json.dumps(
                        normalized_knowledge_point_ids, ensure_ascii=False
                    )
                if thread_id:
                    metadata["thread_id"] = str(thread_id)
                doc.metadata = metadata

            await asyncio.to_thread(self.vector_store.add_documents, documents)

            return {
                "status": "success",
                "message": f"Successfully processed {file.filename}",
                "file_id": file_id,
                "file_size": file_size,
                "created_at": created_at,
                "chunks": len(documents),
                "scope": normalized_scope,
                "thread_id": str(thread_id or ""),
                "course_id": normalized_course_id,
                "chapter_id": normalized_chapter_id,
                "knowledge_point_ids": normalized_knowledge_point_ids,
                "extraction_method": ingest_meta.get("extraction_method", "legacy"),
                "ocr_pages": int(ingest_meta.get("ocr_pages") or 0),
                "preview_snippet": str(ingest_meta.get("preview_snippet") or "")[:280],
            }
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def query_knowledge_base(
        self,
        query: str,
        k: Optional[int] = None,
        filter_type: Optional[str] = None,
        user_id: Optional[str] = None,
        is_admin: bool = False,
        course_id: Optional[str] = None,
    ) -> List[dict]:
        top_k = k or settings.RAG_TOP_K
        normalized_course_id = str(course_id or "").strip()
        has_lexical_backend = callable(getattr(self.vector_store, "get_documents", None))

        personal_matches: List[tuple[Document, float, float, str]] = []
        system_matches: List[tuple[Document, float, float, str]] = []
        seen_keys: set[tuple] = set()

        def add_match(
            doc: Document,
            score: float,
            lexical_score: float = 0.0,
            retrieval_method: str = "vector",
        ) -> None:
            metadata = dict(doc.metadata or {})
            if (
                not normalized_course_id
                and self._normalize_scope(metadata.get("scope")) == "system"
            ):
                # Filter enforcement belongs here as well as in the vector
                # query: backends and legacy adapters may ignore metadata
                # filters, but an unscoped request must never see course-system
                # content.
                return
            if not self._is_visible_to_knowledge_query(metadata, user_id, is_admin):
                return
            # A course-bound request is a hard tenant boundary. Legacy/unscoped
            # chunks and chunks from another course must never become fallback
            # evidence for a course Agent.
            if normalized_course_id and str(metadata.get("course_id") or "").strip() != normalized_course_id:
                return

            key = self._doc_match_key(doc)
            if key in seen_keys:
                return
            seen_keys.add(key)

            scope = self._normalize_scope(metadata.get("scope"))
            if scope == "personal":
                personal_matches.append((doc, score, lexical_score, retrieval_method))
            else:
                system_matches.append((doc, score, lexical_score, retrieval_method))

        for filter_dict in self._build_search_filters(
            user_id=user_id,
            filter_type=filter_type,
            course_id=normalized_course_id or None,
        ):
            vector_matches = self.vector_store.similarity_search_with_scores(
                query,
                k=max(top_k * 4, 12),
                filter=filter_dict,
            )
            lexical_matches = self._lexical_matches(
                query=query,
                where=filter_dict,
                limit=max(top_k * 4, 12),
            )
            vector_rank = {
                self._doc_match_key(doc): rank
                for rank, (doc, _) in enumerate(vector_matches, 1)
            }
            lexical_rank = {
                self._doc_match_key(doc): rank
                for rank, (doc, _) in enumerate(lexical_matches, 1)
            }
            candidates: dict[tuple, tuple[Document, float, float]] = {}
            for doc, score in vector_matches:
                candidates[self._doc_match_key(doc)] = (
                    doc,
                    float(score),
                    self._lexical_score(query, doc),
                )
            for doc, lexical_score in lexical_matches:
                key = self._doc_match_key(doc)
                previous = candidates.get(key)
                candidates[key] = (
                    doc,
                    previous[1] if previous else 0.0,
                    lexical_score,
                )

            fused = []
            provider = settings.EMBEDDINGS_PROVIDER.lower()
            for key, (doc, vector_score, lexical_score) in candidates.items():
                vector_rrf = 1 / (60 + vector_rank[key]) if key in vector_rank else 0.0
                lexical_rrf = 1 / (60 + lexical_rank[key]) if key in lexical_rank else 0.0
                rrf_score = (vector_rrf + lexical_rrf) * 30.5
                if provider == "hash":
                    if (
                        has_lexical_backend
                        and lexical_score < settings.RAG_HASH_MIN_LEXICAL_SCORE
                    ):
                        # Hash embeddings are only a deterministic fallback. A
                        # zero-overlap candidate is not evidence and must not be
                        # surfaced as a citation.
                        continue
                    final_score = lexical_score * 0.82 + rrf_score * 0.18
                    method = "lexical+hash_fallback"
                else:
                    final_score = vector_score * 0.55 + lexical_score * 0.30 + rrf_score * 0.15
                    method = "hybrid_semantic+lexical"
                    if final_score < settings.RAG_COURSE_SEMANTIC_MIN_SCORE:
                        continue
                fused.append((doc, min(1.0, max(0.0, final_score)), lexical_score, method))
            for doc, score, lexical_score, method in sorted(
                fused, key=lambda item: item[1], reverse=True
            ):
                add_match(doc, score, lexical_score, method)

        if (
            normalized_course_id
            and len(personal_matches) + len(system_matches) < top_k
            and not (
                settings.EMBEDDINGS_PROVIDER.lower() == "hash"
                and has_lexical_backend
            )
        ):
            fallback_clauses = []
            if filter_type:
                fallback_clauses.append({"type": filter_type})
            if normalized_course_id:
                fallback_clauses.append({"course_id": normalized_course_id})
            if not fallback_clauses:
                fallback_filter = None
            elif len(fallback_clauses) == 1:
                fallback_filter = fallback_clauses[0]
            else:
                fallback_filter = {"$and": fallback_clauses}
            fallback_matches = self.vector_store.similarity_search_with_scores(
                query,
                k=max(top_k * 4, 12),
                filter=fallback_filter,
            )
            for doc, score in fallback_matches:
                if float(score) < settings.RAG_COURSE_SEMANTIC_MIN_SCORE:
                    continue
                add_match(
                    doc,
                    score,
                    self._lexical_score(query, doc),
                    "vector_fallback",
                )
                if len(personal_matches) + len(system_matches) >= top_k:
                    break

        personal_sorted = sorted(personal_matches, key=lambda item: item[1], reverse=True)
        system_sorted = sorted(system_matches, key=lambda item: item[1], reverse=True)
        matches = (personal_sorted + system_sorted)[:top_k]

        results = []
        for index, (doc, score, lexical_score, retrieval_method) in enumerate(matches, start=1):
            metadata = dict(doc.metadata or {})
            results.append(
                {
                    "citation_id": index,
                    "content": doc.page_content,
                    "metadata": metadata,
                    "source": metadata.get("source", "unknown"),
                    "chunk_id": metadata.get("chunk_id"),
                    "score": score,
                    "lexical_score": lexical_score,
                    "retrieval_method": retrieval_method,
                    "embedding_provider": settings.EMBEDDINGS_PROVIDER.lower(),
                    "semantic_retrieval": settings.EMBEDDINGS_PROVIDER.lower() != "hash",
                    "locator": metadata.get("locator")
                    or (
                        f"{metadata.get('chapter_title')} · 片段 {metadata.get('chunk_id')}"
                        if metadata.get("chapter_title")
                        else f"片段 {metadata.get('chunk_id')}"
                    ),
                }
            )
        return results

    def search_uploaded_document(
        self,
        *,
        query: str,
        file_id: str,
        thread_id: Optional[str],
        user_id: Optional[str],
        is_admin: bool,
        top_k: int = 3,
        course_id: Optional[str] = None,
    ) -> List[dict]:
        if not query.strip() or not file_id.strip():
            return []
        normalized_course_id = str(course_id or "").strip()
        clauses = [{"file_id": file_id}]
        if normalized_course_id:
            clauses.append({"course_id": normalized_course_id})
        if thread_id:
            clauses.append({"thread_id": str(thread_id)})
        where: dict = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        matches = self.vector_store.similarity_search_with_scores(
            query=query,
            k=max(top_k * 4, 12),
            filter=where,
        )
        lexical_matches = self._lexical_matches(
            query=query,
            where=where,
            limit=max(top_k * 4, 12),
        )
        lexical_by_key = {
            self._doc_match_key(doc): score for doc, score in lexical_matches
        }
        candidates: dict[tuple, tuple[Document, float, float]] = {}
        for doc, score in matches:
            candidates[self._doc_match_key(doc)] = (
                doc,
                float(score),
                lexical_by_key.get(
                    self._doc_match_key(doc), self._lexical_score(query, doc)
                ),
            )
        for doc, lexical_score in lexical_matches:
            key = self._doc_match_key(doc)
            previous = candidates.get(key)
            candidates[key] = (
                doc,
                previous[1] if previous else 0.0,
                lexical_score,
            )

        provider = settings.EMBEDDINGS_PROVIDER.lower()
        ranked: list[tuple[Document, float, float, str]] = []
        for doc, vector_score, lexical_score in candidates.values():
            if provider == "hash":
                if lexical_score < settings.RAG_HASH_MIN_LEXICAL_SCORE:
                    continue
                score = lexical_score
                retrieval_method = "lexical+hash_fallback"
            else:
                score = vector_score * 0.7 + lexical_score * 0.3
                if score < settings.RAG_VECTOR_MIN_SCORE:
                    continue
                retrieval_method = "hybrid_semantic+lexical"
            ranked.append((doc, min(1.0, max(0.0, score)), lexical_score, retrieval_method))

        out: List[dict] = []
        for doc, score, lexical_score, retrieval_method in sorted(
            ranked, key=lambda item: item[1], reverse=True
        ):
            md = dict(doc.metadata or {})
            if not self._is_visible_to_user(md, user_id, is_admin):
                continue
            # Treat vector-store filters as an optimization, never as an
            # authorization boundary. Re-check every requested attachment key
            # because adapters and legacy stores may ignore compound filters.
            if str(md.get("file_id") or "") != str(file_id):
                continue
            if thread_id and str(md.get("thread_id") or "") != str(thread_id):
                continue
            if normalized_course_id and str(md.get("course_id") or "").strip() != normalized_course_id:
                continue
            out.append(
                {
                    "citation_id": len(out) + 1,
                    "content": doc.page_content,
                    "metadata": md,
                    "source": md.get("source", "unknown"),
                    "file_name": md.get("source", "unknown"),
                    "chunk_id": md.get("chunk_id"),
                    "locator": f"片段 {md.get('chunk_id')}" if md.get("chunk_id") else "",
                    "score": score,
                    "lexical_score": lexical_score,
                    "retrieval_method": retrieval_method,
                    "embedding_provider": provider,
                    "semantic_retrieval": provider != "hash",
                }
            )
            if len(out) >= top_k:
                break
        return out

    def reset_knowledge_base(self) -> dict:
        self.vector_store.delete_collection()
        return {"status": "success", "message": "Knowledge base has been reset"}

    def list_reference_files(
        self,
        *,
        user_id: Optional[str] = None,
        is_admin: bool = False,
        scope_filter: str = "all",
    ) -> List[dict]:
        metadatas = self.vector_store.get_all_metadatas()
        by_file: dict[str, dict] = {}
        normalized_scope_filter = self._normalize_scope_filter(scope_filter)

        for meta in metadatas:
            file_id = str(meta.get("file_id") or "")
            if not file_id:
                continue
            if file_id in by_file:
                continue
            if not self._is_visible_to_user(meta, user_id, is_admin):
                continue

            scope = self._normalize_scope(meta.get("scope"))
            if normalized_scope_filter != "all" and scope != normalized_scope_filter:
                continue
            owner_id = self._normalize_owner_id(meta.get("owner_id"))

            by_file[file_id] = {
                "file_id": file_id,
                "name": meta.get("source") or "unknown",
                "size": int(meta.get("file_size") or 0),
                "created": meta.get("created_at") or "",
                "scope": scope,
                "owner_id": owner_id or None,
                "can_manage": self._can_manage_file(meta, user_id, is_admin),
            }

        files = list(by_file.values())
        files.sort(key=lambda x: x.get("created", ""), reverse=True)
        return files

    def delete_reference_file(
        self, file_id: str, *, user_id: Optional[str] = None, is_admin: bool = False
    ) -> dict:
        if not file_id:
            return {"status": "error", "message": "Missing file_id"}

        # Verify existence by metadata first to avoid false "not found"
        metadatas = self.vector_store.get_all_metadatas()
        target_metas = [m for m in metadatas if str(m.get("file_id") or "") == file_id]
        if not target_metas:
            return {"status": "error", "message": "File not found"}
        if not self._can_manage_file(target_metas[0], user_id, is_admin):
            return {"status": "error", "message": "Permission denied"}

        deleted = self.vector_store.delete_by_file_id(file_id)
        if not deleted:
            return {
                "status": "error",
                "message": "Delete failed",
            }

        return {
            "status": "success",
            "message": "File deleted",
            "file_id": file_id,
            "deleted": True,
        }

    async def stream_preview(
        self,
        file: UploadFile,
        preview_chars: int = 800,
        preview_chunks: int = 5,
        chunk_preview_chars: int = 300,
        scope: str = "personal",
        owner_id: Optional[str] = None,
        course_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        knowledge_point_ids: Optional[List[str]] = None,
    ) -> AsyncIterator[dict]:
        if not file.filename:
            raise ValueError("Missing file name")

        normalized_scope = self._normalize_scope(scope)
        normalized_owner_id = self._normalize_owner_id(owner_id)
        normalized_course_id = str(course_id or "").strip()
        normalized_chapter_id = str(chapter_id or "").strip()
        normalized_knowledge_point_ids = [
            str(item).strip() for item in (knowledge_point_ids or []) if str(item).strip()
        ]

        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{file_id}{ext}"
        file_path = os.path.join(self.upload_dir, temp_filename)

        yield {"stage": "saving", "message": "保存临时文件"}
        try:
            async with aiofiles.open(file_path, "wb") as out_file:
                content = await read_upload_limited(file)
                await out_file.write(content)
        except Exception:
            if os.path.exists(file_path):
                os.remove(file_path)
            raise
        file_size = len(content)
        created_at = datetime.now(timezone.utc).isoformat()
        yield {
            "stage": "saved",
            "message": "临时文件已保存",
            "file_id": file_id,
            "file_size": file_size,
            "created_at": created_at,
        }

        try:
            yield {"stage": "parsing", "message": "文档解析中"}
            text = await asyncio.to_thread(self.doc_processor.extract_text, file_path)
            text_preview = text[:preview_chars]
            yield {
                "stage": "parsed",
                "message": "解析完成",
                "text_preview": text_preview,
            }

            yield {"stage": "splitting", "message": "文档切分中"}
            doc_type = self.doc_processor.get_doc_type(file_path)
            metadata = {
                "source": file.filename,
                "type": doc_type,
                "scope": normalized_scope,
                "owner_id": normalized_owner_id,
            }
            if normalized_course_id:
                metadata["course_id"] = normalized_course_id
            if normalized_chapter_id:
                metadata["chapter_id"] = normalized_chapter_id
            if normalized_knowledge_point_ids:
                metadata["knowledge_point_ids"] = json.dumps(
                    normalized_knowledge_point_ids, ensure_ascii=False
                )
            documents = await asyncio.to_thread(
                self.doc_processor.split_text, text, metadata=metadata
            )

            for idx, doc in enumerate(documents):
                meta = dict(doc.metadata or {})
                meta["file_id"] = file_id
                meta["source"] = file.filename
                meta["chunk_id"] = idx + 1
                meta["file_size"] = file_size
                meta["created_at"] = created_at
                doc.metadata = meta

            chunks_total = len(documents)
            chunks_preview = []
            for doc in documents[:preview_chunks]:
                chunk_text = doc.page_content[:chunk_preview_chars]
                chunks_preview.append(
                    {
                        "chunk_id": doc.metadata.get("chunk_id"),
                        "text_preview": chunk_text,
                        "length": len(doc.page_content),
                    }
                )

            self._save_preview_cache(file_id, file.filename, file_size, created_at, documents)

            yield {
                "stage": "ready",
                "message": "切分完成，等待确认",
                "file_id": file_id,
                "file_size": file_size,
                "created_at": created_at,
                "chunks_total": chunks_total,
                "chunks_preview": chunks_preview,
                "text_preview": text_preview,
                "scope": normalized_scope,
                "course_id": normalized_course_id,
                "chapter_id": normalized_chapter_id,
                "knowledge_point_ids": normalized_knowledge_point_ids,
            }
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def commit_preview(
        self, file_id: str, *, user_id: Optional[str] = None, is_admin: bool = False
    ) -> dict:
        preview = self._load_preview_cache(file_id)
        if not preview:
            return {"status": "error", "message": "Preview not found"}
        preview_meta = {
            "scope": preview.get("scope") or "personal",
            "owner_id": preview.get("owner_id") or "",
        }
        if not self._can_manage_file(preview_meta, user_id, is_admin):
            return {"status": "error", "message": "Permission denied"}

        documents = [
            Document(page_content=item["page_content"], metadata=item.get("metadata") or {})
            for item in preview.get("documents", [])
        ]
        if not documents:
            return {"status": "error", "message": "No documents to commit"}

        self.vector_store.add_documents(documents)
        self._delete_preview_cache(file_id)

        return {
            "status": "success",
            "message": "Successfully committed document",
            "file_id": file_id,
            "file_size": preview.get("file_size", 0),
            "created_at": preview.get("created_at", ""),
            "chunks": len(documents),
            "course_id": str(preview.get("course_id") or ""),
            "chapter_id": str(preview.get("chapter_id") or ""),
            "knowledge_point_ids": list(preview.get("knowledge_point_ids") or []),
        }

    def cancel_preview(
        self, file_id: str, *, user_id: Optional[str] = None, is_admin: bool = False
    ) -> dict:
        preview = self._load_preview_cache(file_id)
        if not preview:
            return {"status": "error", "message": "Preview not found"}
        preview_meta = {
            "scope": preview.get("scope") or "personal",
            "owner_id": preview.get("owner_id") or "",
        }
        if not self._can_manage_file(preview_meta, user_id, is_admin):
            return {"status": "error", "message": "Permission denied"}

        deleted = self._delete_preview_cache(file_id)
        if not deleted:
            return {"status": "error", "message": "Preview not found"}
        return {"status": "success", "message": "Preview cancelled", "file_id": file_id}

    def _preview_cache_path(self, file_id: str) -> str:
        try:
            normalized_file_id = str(uuid.UUID(str(file_id)))
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("Invalid preview file_id") from exc
        preview_root = Path(self.preview_dir).resolve()
        candidate = preview_root / f"{normalized_file_id}.json"
        if candidate.is_symlink():
            raise ValueError("Invalid preview cache path")
        path = candidate.resolve(strict=False)
        if path.parent != preview_root:
            raise ValueError("Invalid preview cache path")
        return str(path)

    def _save_preview_cache(
        self,
        file_id: str,
        source: str,
        file_size: int,
        created_at: str,
        documents: List[Document],
    ) -> None:
        payload = {
            "file_id": file_id,
            "source": source,
            "file_size": file_size,
            "created_at": created_at,
            "scope": self._normalize_scope(
                (documents[0].metadata or {}).get("scope") if documents else "personal"
            ),
            "owner_id": self._normalize_owner_id(
                (documents[0].metadata or {}).get("owner_id") if documents else ""
            ),
            "course_id": str(
                (documents[0].metadata or {}).get("course_id") if documents else ""
            ),
            "chapter_id": str(
                (documents[0].metadata or {}).get("chapter_id") if documents else ""
            ),
            "knowledge_point_ids": json.loads(
                str((documents[0].metadata or {}).get("knowledge_point_ids") or "[]")
            ) if documents else [],
            "documents": [
                {"page_content": doc.page_content, "metadata": dict(doc.metadata or {})}
                for doc in documents
            ],
        }
        with open(self._preview_cache_path(file_id), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False)

    def _load_preview_cache(self, file_id: str) -> Optional[dict]:
        path = self._preview_cache_path(file_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _delete_preview_cache(self, file_id: str) -> bool:
        path = self._preview_cache_path(file_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
