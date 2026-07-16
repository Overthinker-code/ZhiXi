from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from threading import Lock
from typing import Optional
from uuid import uuid4


@dataclass
class PendingAction:
    action_id: str
    user_id: str
    thread_id: str
    plan_text: str
    status: str
    created_at: str


class PendingActionStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._items: dict[str, PendingAction] = {}

    def create(self, user_id: str, thread_id: str, plan_text: str) -> PendingAction:
        action = PendingAction(
            action_id=uuid4().hex,
            user_id=user_id,
            thread_id=thread_id,
            plan_text=plan_text,
            status="pending",
            created_at=datetime.utcnow().isoformat(),
        )
        with self._lock:
            self._items[action.action_id] = action
        return action

    def get(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            return self._items.get(action_id)

    def confirm(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._items.get(action_id)
            if not item:
                return None
            item.status = "confirmed"
            return item

    def reject(self, action_id: str) -> Optional[PendingAction]:
        with self._lock:
            item = self._items.get(action_id)
            if not item:
                return None
            item.status = "rejected"
            return item

    def as_dict(self, item: PendingAction) -> dict:
        return asdict(item)


pending_action_store = PendingActionStore()
