#!/usr/bin/env python3
"""Real SSE verification: reasoning_token must arrive before answer tokens."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def login(base: str, email: str, password: str) -> str:
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/login/access-token",
        data=f"username={email}&password={password}".encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["access_token"]


def stream_events(base: str, token: str, user_input: str, thread_id: str):
    payload = json.dumps(
        {
            "user_input": user_input,
            "thread_id": thread_id,
            "force_cache": False,
            "max_tokens": 2048,
        }
    ).encode()
    req = urllib.request.Request(
        f"{base.rstrip('/')}/api/v1/chat/stream",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        method="POST",
    )
    events: list[dict] = []
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=300) as resp:
        headers = dict(resp.headers)
        for raw in resp:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data:"):
                continue
            evt = json.loads(line[5:].strip())
            evt["_t"] = round(time.perf_counter() - t0, 3)
            events.append(evt)
    return events, headers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://127.0.0.1:8001"))
    parser.add_argument("--email", default=os.environ.get("EMAIL", "admin@example.com"))
    parser.add_argument("--password", default=os.environ.get("PASSWORD", ""))
    args = parser.parse_args()
    if not args.password:
        print("FAIL: password required via --password or PASSWORD env", file=sys.stderr)
        return 2

    token = login(args.base_url, args.email, args.password)
    events, headers = stream_events(
        args.base_url,
        token,
        "一些高等数学公式详解，写出导数定义与 (x+h)^2-x^2 的展开",
        f"verify-sse-{int(time.time())}",
    )

    reasoning = [e for e in events if e.get("type") == "reasoning_token"]
    tokens = [e for e in events if e.get("type") == "token"]
    errors = [e for e in events if e.get("type") == "error"]
    final = next((e for e in events if e.get("type") == "final"), None)

    print("SSE_HEADERS", {k: headers.get(k) for k in ("Cache-Control", "X-Accel-Buffering", "Content-Type")})
    print("reasoning_events", len(reasoning))
    print("token_events", len(tokens))
    print("errors", errors)

    if errors:
        print("FAIL: stream error", errors[0].get("content"))
        return 1
    if not reasoning:
        print("FAIL: no reasoning_token events")
        return 1
    if not tokens or not final:
        print("FAIL: no answer tokens/final")
        return 1

    first_reason_t = reasoning[0]["_t"]
    first_token_t = tokens[0]["_t"]
    reasoning_text = "".join(e.get("content", "") for e in reasoning)
    print("first_reasoning_s", first_reason_t)
    print("first_token_s", first_token_t)
    print("reasoning_preview", reasoning_text[:120].replace("\n", " "))

    if first_reason_t > first_token_t:
        print("FAIL: reasoning_token arrived after answer token")
        return 1
    if "用户刚发来一个问题" in reasoning_text:
        print("FAIL: pipeline monologue in reasoning")
        return 1
    if first_reason_t > 30:
        print("FAIL: reasoning_token too late (>30s), likely buffered SSE")
        return 1

    content = final.get("content") or ""
    if "rac{" in content and "\\frac" not in content:
        print("FAIL: corrupted frac in final")
        return 1
    if "ext{" in content and "\\text" not in content and "\\lim" not in content:
        print("FAIL: corrupted text/lim in final")
        return 1

    print("PASS: SSE reasoning timing and math integrity OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
