from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from threading import Lock


@dataclass
class CacheItem:
    question: str
    answer: str
    hit_count: int
    updated_at: str


class ChatSemanticCache:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: list[CacheItem] = []

    def _similarity(self, a: str, b: str) -> float:
        return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()

    def get(self, question: str, threshold: float = 0.95) -> CacheItem | None:
        with self._lock:
            best = None
            best_score = 0.0
            for item in self._items:
                score = self._similarity(question, item.question)
                if score > best_score:
                    best = item
                    best_score = score
            if best and best_score >= threshold:
                best.hit_count += 1
                best.updated_at = datetime.utcnow().isoformat()
                return best
            return None

    def put(self, question: str, answer: str) -> None:
        with self._lock:
            for item in self._items:
                if item.question.strip().lower() == question.strip().lower():
                    item.answer = answer
                    item.updated_at = datetime.utcnow().isoformat()
                    return
            self._items.append(
                CacheItem(
                    question=question,
                    answer=answer,
                    hit_count=1,
                    updated_at=datetime.utcnow().isoformat(),
                )
            )

    def hotspots(self, top_k: int = 10) -> list[dict]:
        with self._lock:
            sorted_items = sorted(self._items, key=lambda x: x.hit_count, reverse=True)
            return [
                {
                    "question": item.question,
                    "hit_count": item.hit_count,
                    "updated_at": item.updated_at,
                }
                for item in sorted_items[:top_k]
            ]


chat_semantic_cache = ChatSemanticCache()
