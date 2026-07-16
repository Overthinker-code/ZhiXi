from __future__ import annotations

import hashlib
import math
import time
from collections import deque
from threading import Lock
from typing import Iterable

from app.core.config import settings


class AuthAttemptLimiter:
    """Small bounded in-process limiter for the single-node competition runtime."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._last_seen: dict[str, float] = {}
        self._lock = Lock()

    @staticmethod
    def keys(*, flow: str, client_host: str, account: str) -> tuple[str, str]:
        normalized_account = account.strip().casefold()
        account_digest = hashlib.sha256(normalized_account.encode("utf-8")).hexdigest()
        host = (client_host or "unknown").strip()[:128]
        return (f"{flow}:ip:{host}", f"{flow}:account:{account_digest}")

    def _prune_key(self, key: str, *, now: float) -> deque[float]:
        events = self._events.setdefault(key, deque())
        cutoff = now - settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
        while events and events[0] <= cutoff:
            events.popleft()
        if not events:
            self._events.pop(key, None)
        return events

    def _bound_identities(self, *, now: float) -> None:
        overflow = len(self._last_seen) - settings.AUTH_RATE_LIMIT_MAX_IDENTITIES
        if overflow <= 0:
            return
        for key, _ in sorted(self._last_seen.items(), key=lambda item: item[1])[:overflow]:
            self._last_seen.pop(key, None)
            self._events.pop(key, None)

    def retry_after(self, keys: Iterable[str]) -> int | None:
        now = time.monotonic()
        with self._lock:
            waits: list[int] = []
            for key in keys:
                events = self._prune_key(key, now=now)
                self._last_seen[key] = now
                if len(events) >= settings.AUTH_RATE_LIMIT_ATTEMPTS:
                    waits.append(
                        max(
                            1,
                            math.ceil(
                                settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
                                - (now - events[0])
                            ),
                        )
                    )
            self._bound_identities(now=now)
            return max(waits) if waits else None

    def record(self, keys: Iterable[str]) -> None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                events = self._prune_key(key, now=now)
                events.append(now)
                self._events[key] = events
                self._last_seen[key] = now
            self._bound_identities(now=now)

    def clear(self, keys: Iterable[str]) -> None:
        with self._lock:
            for key in keys:
                self._events.pop(key, None)
                self._last_seen.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._last_seen.clear()


auth_attempt_limiter = AuthAttemptLimiter()
