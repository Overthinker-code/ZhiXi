from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

import jwt

from app.core import security
from app.core.config import settings

ASGIApp = Callable[[dict[str, Any], Callable[..., Awaitable[dict]], Callable[..., Awaitable[None]]], Awaitable[None]]


class RequestSizeLimitMiddleware:
    """Reject oversized HTTP bodies before multipart/JSON parsing allocates them."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        try:
            content_length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            await _json_response(send, 400, "Invalid Content-Length header")
            return
        if content_length > self.max_bytes:
            await _json_response(send, 413, "Request body too large")
            return

        received = 0
        exceeded = False
        response_started = False
        limit_body_sent = False

        def limit_response() -> tuple[bytes, list[tuple[bytes, bytes]]]:
            body = json.dumps({"detail": "Request body too large"}).encode()
            headers = [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ]
            return body, headers

        async def tracked_send(message: dict) -> None:
            nonlocal response_started, limit_body_sent
            if exceeded and not response_started:
                body, headers = limit_response()
                if message["type"] == "http.response.start":
                    response_started = True
                    await send(
                        {"type": "http.response.start", "status": 413, "headers": headers}
                    )
                    return
                if message["type"] == "http.response.body":
                    response_started = True
                    limit_body_sent = True
                    await send(
                        {"type": "http.response.start", "status": 413, "headers": headers}
                    )
                    await send({"type": "http.response.body", "body": body})
                    return
            if exceeded and response_started and message["type"] == "http.response.body":
                if not limit_body_sent:
                    body, _ = limit_response()
                    limit_body_sent = True
                    await send({"type": "http.response.body", "body": body})
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        async def limited_receive() -> dict:
            nonlocal received, exceeded
            message = await receive()
            if message.get("type") == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        try:
            await self.app(scope, limited_receive, tracked_send)
        except Exception:
            if not exceeded:
                raise
            if not response_started:
                await _json_response(send, 413, "Request body too large")


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    [
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"strict-origin-when-cross-origin"),
                        (b"permissions-policy", b"camera=(self), microphone=(), geolocation=()"),
                        (b"cache-control", b"no-store"),
                    ]
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


class AIRequestBudgetMiddleware:
    """Bound expensive authenticated work per user for a single-node deployment."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._active: defaultdict[str, int] = defaultdict(int)
        self._recent: dict[str, deque[float]] = {}
        self._last_seen: dict[str, float] = {}
        self._last_cleanup = 0.0
        self._lock = asyncio.Lock()

    def _cleanup_identities(self, now: float) -> None:
        window = settings.AI_RATE_LIMIT_WINDOW_SECONDS
        stale = [
            identity
            for identity, seen_at in self._last_seen.items()
            if identity not in self._active and seen_at <= now - window
        ]
        for identity in stale:
            self._recent.pop(identity, None)
            self._last_seen.pop(identity, None)

        maximum = max(1, settings.AI_BUDGET_MAX_IDENTITIES)
        overflow = len(self._recent) - maximum + 1
        if overflow > 0:
            inactive = sorted(
                (
                    (seen_at, identity)
                    for identity, seen_at in self._last_seen.items()
                    if identity not in self._active
                ),
                key=lambda item: item[0],
            )
            for _, identity in inactive[:overflow]:
                self._recent.pop(identity, None)
                self._last_seen.pop(identity, None)
        self._last_cleanup = now

    @staticmethod
    def _budget_class(path: str, method: str) -> tuple[str, bool] | None:
        if method not in {"POST", "PUT"}:
            return None
        sse_prefixes = (
            f"{settings.API_V1_STR}/ai/chat/stream",
            f"{settings.API_V1_STR}/chat/stream",
            f"{settings.API_V1_STR}/chat/selection-query",
            f"{settings.API_V1_STR}/chat/resume",
        )
        for prefix in sse_prefixes:
            if path.startswith(prefix):
                return (prefix, True)
        sync_prefixes = (
            f"{settings.API_V1_STR}/resource-generation/",
            f"{settings.API_V1_STR}/resource-workshop/",
            f"{settings.API_V1_STR}/digital-human/",
            f"{settings.API_V1_STR}/behavior/analyze/",
        )
        for prefix in sync_prefixes:
            if path.startswith(prefix):
                return (prefix, False)
        return None

    @staticmethod
    def _identity(scope: dict) -> str:
        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        if authorization.lower().startswith("bearer "):
            token = authorization[7:].strip()
            try:
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[security.ALGORITHM],
                )
                if payload.get("sub"):
                    return f"user:{payload['sub']}"
            except jwt.PyJWTError:
                pass
        client = scope.get("client") or ("unknown", 0)
        return f"ip:{client[0]}"

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        budget_class = self._budget_class(
            scope.get("path", ""), scope.get("method", "GET")
        )
        if scope["type"] != "http" or budget_class is None:
            await self.app(scope, receive, send)
            return

        endpoint_class, is_sse = budget_class
        identity = f"{self._identity(scope)}:{endpoint_class}"
        concurrency_limit = (
            settings.AI_SSE_MAX_CONCURRENT_PER_USER
            if is_sse
            else settings.AI_SYNC_MAX_CONCURRENT_PER_USER
        )
        window = settings.AI_RATE_LIMIT_WINDOW_SECONDS
        wait_seconds = max(0.0, float(settings.AI_CONCURRENCY_WAIT_SECONDS))
        wait_until = time.monotonic() + wait_seconds
        while True:
            now = time.monotonic()
            async with self._lock:
                cleanup_due = (
                    now - self._last_cleanup
                    >= settings.AI_BUDGET_CLEANUP_INTERVAL_SECONDS
                    or identity not in self._recent
                    and len(self._recent) >= settings.AI_BUDGET_MAX_IDENTITIES
                )
                if cleanup_due:
                    self._cleanup_identities(now)
                identity_capacity = max(1, settings.AI_BUDGET_MAX_IDENTITIES)
                if identity not in self._recent and len(self._recent) >= identity_capacity:
                    await _json_response(
                        send,
                        429,
                        "AI request identity capacity exceeded",
                        [(b"retry-after", b"1")],
                    )
                    return
                recent = self._recent.setdefault(identity, deque())
                while recent and recent[0] <= now - window:
                    recent.popleft()
                if len(recent) >= settings.AI_RATE_LIMIT_REQUESTS:
                    retry_after = max(1, int(window - (now - recent[0])))
                    await _json_response(
                        send,
                        429,
                        "AI request rate limit exceeded",
                        [(b"retry-after", str(retry_after).encode())],
                    )
                    return
                if self._active[identity] < concurrency_limit:
                    recent.append(now)
                    self._last_seen[identity] = now
                    self._active[identity] += 1
                    break
                if now >= wait_until:
                    await _json_response(
                        send,
                        429,
                        "AI concurrency limit exceeded",
                        [(b"retry-after", b"1")],
                    )
                    return
            await asyncio.sleep(min(0.25, max(0.0, wait_until - time.monotonic())))

        response_started = False

        async def tracked_send(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            timeout = (
                settings.AI_SSE_TIMEOUT_SECONDS
                if is_sse
                else settings.AI_SYNC_TIMEOUT_SECONDS
            )
            async with asyncio.timeout(timeout):
                await self.app(scope, receive, tracked_send)
        except TimeoutError:
            if not response_started:
                await _json_response(send, 504, "AI request timed out")
        finally:
            async with self._lock:
                self._active[identity] -= 1
                if self._active[identity] <= 0:
                    self._active.pop(identity, None)


async def _json_response(
    send: Callable,
    status: int,
    detail: str,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    body = json.dumps({"detail": detail}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    headers.extend(extra_headers or [])
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})
