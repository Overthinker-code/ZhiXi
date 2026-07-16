#!/usr/bin/env python3
"""Golden Path rehearsal — wraps smoke_functional_test with demo credentials."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.smoke_functional_test import run_smoke  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="ZhiXi Golden Path HTTP rehearsal")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--email", default="student@example.com")
    parser.add_argument("--password", default="student123456")
    parser.add_argument(
        "--output",
        default=str(BACKEND_ROOT.parent.parent / "docs" / "smoke_report_golden_path.json"),
    )
    args = parser.parse_args()
    started = time.perf_counter()
    report = run_smoke(
        args.base_url,
        args.email,
        args.password,
        chat_timeout=120.0,
    )
    payload = {
        "generated_at": report.generated_at,
        "base_url": report.base_url,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
        "summary": report.summary(),
        "environment": report.environment,
        "results": [asdict(r) for r in report.results],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Golden Path smoke: {payload['summary']}")
    print(f"Wrote {out}")
    return 0 if payload["summary"].get("fail", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
