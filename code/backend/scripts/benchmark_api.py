#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import httpx


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return round(ordered[index], 2)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "p50_ms": round(statistics.median(values), 2) if values else None,
        "p95_ms": percentile(values, 0.95),
        "min_ms": round(min(values), 2) if values else None,
        "max_ms": round(max(values), 2) if values else None,
    }


def benchmark_health(client: httpx.Client, base_url: str, iterations: int) -> dict[str, Any]:
    timings: list[float] = []
    failures = 0
    for _ in range(iterations):
        started = time.perf_counter()
        try:
            response = client.get(f"{base_url}/api/v1/healthz")
            response.raise_for_status()
        except Exception:
            failures += 1
        else:
            timings.append((time.perf_counter() - started) * 1000)
    return {
        **summarize(timings),
        "failures": failures,
        "failure_rate": round(failures / max(iterations, 1), 4),
    }


def benchmark_sse(
    client: httpx.Client,
    url: str,
    token: str,
    payload: dict[str, Any],
    iterations: int,
) -> dict[str, Any]:
    first_tokens: list[float] = []
    totals: list[float] = []
    failures = 0
    headers = {"Authorization": f"Bearer {token}", "Accept": "text/event-stream"}
    for _ in range(iterations):
        started = time.perf_counter()
        first_token: float | None = None
        try:
            with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                current_event = ""
                for line in response.iter_lines():
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:") and first_token is None:
                        if current_event in {"answer_delta", "token", "message"}:
                            first_token = (time.perf_counter() - started) * 1000
            if first_token is None:
                raise RuntimeError("stream completed without an answer token")
        except Exception:
            failures += 1
        else:
            first_tokens.append(first_token)
            totals.append((time.perf_counter() - started) * 1000)
    return {
        "first_token": summarize(first_tokens),
        "generation": summarize(totals),
        "failures": failures,
        "failure_rate": round(failures / max(iterations, 1), 4),
    }


def benchmark_sync(
    client: httpx.Client,
    url: str,
    token: str,
    payload: dict[str, Any],
    iterations: int,
) -> dict[str, Any]:
    timings: list[float] = []
    failures = 0
    headers = {"Authorization": f"Bearer {token}"}
    for _ in range(iterations):
        started = time.perf_counter()
        try:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except Exception:
            failures += 1
        else:
            timings.append((time.perf_counter() - started) * 1000)
    return {
        "generation": summarize(timings),
        "failures": failures,
        "failure_rate": round(failures / max(iterations, 1), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproducible ZhiXi API latency benchmark")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--health-iterations", type=int, default=20)
    parser.add_argument("--ai-iterations", type=int, default=0)
    parser.add_argument("--token", default="")
    parser.add_argument("--ai-payload", type=Path)
    parser.add_argument("--sync-iterations", type=int, default=0)
    parser.add_argument("--sync-url", default="/api/v1/resource-generation/packages")
    parser.add_argument("--sync-payload", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report: dict[str, Any] = {"base_url": args.base_url, "timestamp_epoch": time.time()}
    with httpx.Client(timeout=httpx.Timeout(300, connect=5)) as client:
        report["healthz"] = benchmark_health(client, args.base_url.rstrip("/"), args.health_iterations)
        if args.ai_iterations:
            if not args.token or not args.ai_payload:
                parser.error("--ai-iterations requires --token and --ai-payload")
            payload = json.loads(args.ai_payload.read_text(encoding="utf-8"))
            report["ai_sse"] = benchmark_sse(
                client,
                f"{args.base_url.rstrip('/')}/api/v1/ai/chat/stream",
                args.token,
                payload,
                args.ai_iterations,
            )
        else:
            report["ai_sse"] = {"status": "skipped", "reason": "--ai-iterations=0"}
        if args.sync_iterations:
            if not args.token or not args.sync_payload:
                parser.error("--sync-iterations requires --token and --sync-payload")
            sync_payload = json.loads(args.sync_payload.read_text(encoding="utf-8"))
            report["sync_generation"] = benchmark_sync(
                client,
                f"{args.base_url.rstrip('/')}{args.sync_url}",
                args.token,
                sync_payload,
                args.sync_iterations,
            )
        else:
            report["sync_generation"] = {
                "status": "skipped",
                "reason": "--sync-iterations=0",
            }

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
