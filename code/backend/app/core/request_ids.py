from __future__ import annotations

import re
from uuid import uuid4

from fastapi import Request


_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def resolve_request_id(request: Request) -> str:
    """Return a log-safe caller request id or generate a new opaque id."""

    candidate = (request.headers.get("X-Request-ID") or "").strip()
    if candidate and _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return uuid4().hex


def error_detail(*, code: str, message: str, request_id: str) -> dict[str, str]:
    return {"code": code, "message": message, "request_id": request_id}


def request_id_headers(request_id: str) -> dict[str, str]:
    return {"X-Request-ID": request_id}
