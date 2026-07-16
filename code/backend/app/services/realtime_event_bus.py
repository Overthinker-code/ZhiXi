from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass
class RealtimeEvent:
    user_id: str
    event_type: str
    content: str
    created_at: str
    payload: dict[str, Any]


class RealtimeEventBus:
    def __init__(self) -> None:
        self._lock = Lock()
        self._queues: dict[str, list[RealtimeEvent]] = defaultdict(list)

    def publish(self, user_id: str, event_type: str, content: str, payload: dict[str, Any] | None = None) -> None:
        event = RealtimeEvent(
            user_id=user_id,
            event_type=event_type,
            content=content,
            created_at=datetime.utcnow().isoformat(),
            payload=payload or {},
        )
        with self._lock:
            self._queues[user_id].append(event)

    def pop_all(self, user_id: str) -> list[RealtimeEvent]:
        with self._lock:
            events = list(self._queues.get(user_id, []))
            self._queues[user_id].clear()
            return events


realtime_event_bus = RealtimeEventBus()
