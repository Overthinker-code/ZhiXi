from typing import List, Optional, Tuple
import os

from langchain_core.documents import Document

from app.core.config import settings
from .embedding_factory import EmbeddingFactory
from .vector_store_factory import VectorStoreFactory


class VectorStore:
    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_directory = persist_directory or settings.CHROMA_DB_PATH
        self.embeddings = EmbeddingFactory.create()

        os.makedirs(self.persist_directory, exist_ok=True)

        self.db = VectorStoreFactory.create(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
        )

    @staticmethod
    def _persist_if_supported(db) -> None:
        """langchain-chroma >=0.1 auto-persists; older wrappers expose persist()."""
        persist_fn = getattr(db, "persist", None)
        if callable(persist_fn):
            persist_fn()

    def add_documents(self, documents: List[Document]) -> None:
        self.db.add_documents(documents)
        self._persist_if_supported(self.db)

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
    ) -> List[Document]:
        return self.db.similarity_search(query, k=k, filter=filter)

    def similarity_search_with_scores(
        self,
        query: str,
        k: int = 4,
        filter: Optional[dict] = None,
    ) -> List[Tuple[Document, float]]:
        if settings.EMBEDDINGS_PROVIDER.lower() == "hash":
            matches = self.db.similarity_search_with_score(
                query,
                k=k,
                filter=filter,
            )
            return [
                (document, self._hash_distance_to_relevance(distance))
                for document, distance in matches
            ]
        return self.db.similarity_search_with_relevance_scores(
            query,
            k=k,
            filter=filter,
        )

    @staticmethod
    def _hash_distance_to_relevance(distance: float) -> float:
        """Map Chroma squared L2 distance for unit hash vectors to [0, 1]."""

        cosine_similarity = 1.0 - float(distance) / 2.0
        return max(0.0, min(1.0, cosine_similarity))

    def get_all_metadatas(self) -> List[dict]:
        data = self.db.get(include=["metadatas"])
        metadatas = data.get("metadatas") or []
        return [m for m in metadatas if isinstance(m, dict)]

    def get_documents(self, filter: Optional[dict] = None) -> List[Document]:
        """Return persisted documents for an auditable lexical retrieval pass."""

        kwargs = {
            "include": ["documents", "metadatas"],
            "limit": settings.RAG_LEXICAL_MAX_DOCUMENTS,
        }
        if filter:
            kwargs["where"] = filter
        data = self.db.get(**kwargs)
        contents = data.get("documents") or []
        metadatas = data.get("metadatas") or []
        return [
            Document(page_content=str(content or ""), metadata=dict(metadata or {}))
            for content, metadata in zip(contents, metadatas)
            if str(content or "").strip()
        ]

    def delete_collection(self) -> None:
        if hasattr(self.db, "delete_collection"):
            self.db.delete_collection()
        else:
            # Fallback for older wrappers.
            self.db._collection.delete(where={})

        # Recreate an empty collection so subsequent queries/adds still work.
        self.db = VectorStoreFactory.create(
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
        )

    def delete_by_file_id(self, file_id: str) -> bool:
        if not file_id:
            return False

        deleted = None
        # langchain Chroma supports delete(where=...)
        if hasattr(self.db, "delete"):
            result = self.db.delete(where={"file_id": file_id})
            if isinstance(result, int):
                deleted = result
            elif isinstance(result, dict):
                deleted = int(result.get("deleted", 0))
        else:
            # Fallback for older wrappers.
            self.db._collection.delete(where={"file_id": file_id})
        self._persist_if_supported(self.db)
        # Some versions return None; treat as success if delete was attempted.
        if deleted is None:
            return True
        return deleted > 0
