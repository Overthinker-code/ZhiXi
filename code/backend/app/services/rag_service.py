from typing import List, Optional, AsyncIterator
import os
import uuid
import json
from datetime import datetime, timezone

from fastapi import UploadFile
import aiofiles
from langchain_core.documents import Document

from app.core.config import settings
from .document_processor import DocumentProcessor
from .vector_store import VectorStore


class RAGService:
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

        filters.append(build_where(scope="system", type=filter_type))

        if owner_id:
            filters.append(
                build_where(scope="personal", owner_id=owner_id, type=filter_type)
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

    async def process_uploaded_file(
        self,
        file: UploadFile,
        *,
        scope: str = "personal",
        owner_id: Optional[str] = None,
        thread_id: Optional[str] = None,
    ) -> dict:
        if not file.filename:
            raise ValueError("Missing file name")

        normalized_scope = self._normalize_scope(scope)
        normalized_owner_id = self._normalize_owner_id(owner_id)

        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{file_id}{ext}"
        file_path = os.path.join(self.upload_dir, temp_filename)

        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
        file_size = len(content)
        created_at = datetime.now(timezone.utc).isoformat()

        try:
            documents = self.doc_processor.process_document(file_path)

            for idx, doc in enumerate(documents):
                metadata = dict(doc.metadata or {})
                metadata["file_id"] = file_id
                metadata["source"] = file.filename
                metadata["chunk_id"] = idx + 1
                metadata["file_size"] = file_size
                metadata["created_at"] = created_at
                metadata["scope"] = normalized_scope
                metadata["owner_id"] = normalized_owner_id
                if thread_id:
                    metadata["thread_id"] = str(thread_id)
                doc.metadata = metadata

            self.vector_store.add_documents(documents)

            return {
                "status": "success",
                "message": f"Successfully processed {file.filename}",
                "file_id": file_id,
                "file_size": file_size,
                "created_at": created_at,
                "chunks": len(documents),
                "scope": normalized_scope,
                "thread_id": str(thread_id or ""),
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
    ) -> List[dict]:
        top_k = k or settings.RAG_TOP_K

        personal_matches: List[tuple[Document, float]] = []
        system_matches: List[tuple[Document, float]] = []
        seen_keys: set[tuple] = set()

        def add_match(doc: Document, score: float) -> None:
            metadata = dict(doc.metadata or {})
            if not self._is_visible_to_user(metadata, user_id, is_admin):
                return

            key = self._doc_match_key(doc)
            if key in seen_keys:
                return
            seen_keys.add(key)

            scope = self._normalize_scope(metadata.get("scope"))
            if scope == "personal":
                personal_matches.append((doc, score))
            else:
                system_matches.append((doc, score))

        for filter_dict in self._build_search_filters(
            user_id=user_id, filter_type=filter_type
        ):
            matches = self.vector_store.similarity_search_with_scores(
                query,
                k=top_k,
                filter=filter_dict,
            )
            for doc, score in matches:
                add_match(doc, score)

        if len(personal_matches) + len(system_matches) < top_k:
            fallback_filter = {"type": filter_type} if filter_type else None
            fallback_matches = self.vector_store.similarity_search_with_scores(
                query,
                k=max(top_k * 4, 12),
                filter=fallback_filter,
            )
            for doc, score in fallback_matches:
                add_match(doc, score)
                if len(personal_matches) + len(system_matches) >= top_k:
                    break

        personal_sorted = sorted(personal_matches, key=lambda item: item[1], reverse=True)
        system_sorted = sorted(system_matches, key=lambda item: item[1], reverse=True)
        matches = (personal_sorted + system_sorted)[:top_k]

        results = []
        for index, (doc, score) in enumerate(matches, start=1):
            metadata = dict(doc.metadata or {})
            results.append(
                {
                    "citation_id": index,
                    "content": doc.page_content,
                    "metadata": metadata,
                    "source": metadata.get("source", "unknown"),
                    "chunk_id": metadata.get("chunk_id"),
                    "score": score,
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
    ) -> List[dict]:
        if not query.strip() or not file_id.strip():
            return []
        where: dict = {"$and": [{"file_id": file_id}]}
        if thread_id:
            where["$and"].append({"thread_id": str(thread_id)})
        matches = self.vector_store.similarity_search_with_scores(
            query=query,
            k=top_k,
            filter=where,
        )
        out: List[dict] = []
        for i, (doc, score) in enumerate(matches, start=1):
            md = dict(doc.metadata or {})
            if not self._is_visible_to_user(md, user_id, is_admin):
                continue
            out.append(
                {
                    "citation_id": i,
                    "content": doc.page_content,
                    "metadata": md,
                    "source": md.get("source", "unknown"),
                    "chunk_id": md.get("chunk_id"),
                    "score": score,
                }
            )
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
    ) -> AsyncIterator[dict]:
        if not file.filename:
            raise ValueError("Missing file name")

        normalized_scope = self._normalize_scope(scope)
        normalized_owner_id = self._normalize_owner_id(owner_id)

        file_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1]
        temp_filename = f"{file_id}{ext}"
        file_path = os.path.join(self.upload_dir, temp_filename)

        yield {"stage": "saving", "message": "保存临时文件"}
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
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
            text = self.doc_processor.extract_text(file_path)
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
            documents = self.doc_processor.split_text(text, metadata=metadata)

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
        return os.path.join(self.preview_dir, f"{file_id}.json")

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
