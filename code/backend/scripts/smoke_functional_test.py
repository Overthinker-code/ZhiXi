#!/usr/bin/env python3
"""Functional smoke tests against a running ZhiXi backend."""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ResultStatus = Literal["pass", "fail", "degraded", "skip"]

TINY_PNG_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@dataclass
class CaseResult:
    name: str
    status: ResultStatus
    detail: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SmokeReport:
    generated_at: str
    base_url: str
    environment: dict[str, Any] = field(default_factory=dict)
    results: list[CaseResult] = field(default_factory=list)

    def add(self, result: CaseResult) -> None:
        self.results.append(result)

    def summary(self) -> dict[str, int]:
        counts = {"pass": 0, "fail": 0, "degraded": 0, "skip": 0}
        for item in self.results:
            counts[item.status] = counts.get(item.status, 0) + 1
        return counts


def _request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    form: dict[str, str] | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> tuple[int, Any]:
    req_headers = dict(headers or {})
    payload = data
    if json_body is not None:
        payload = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")
    if form is not None:
        payload = urlencode(form).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = Request(url, data=payload, headers=req_headers, method=method.upper())
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(str(exc)) from exc
    try:
        body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        body = raw
    return status, body


def _api(base: str, path: str) -> str:
    return f"{base.rstrip('/')}{path}"


def _login(base: str, email: str, password: str) -> str:
    status, body = _request(
        "POST",
        _api(base, "/api/v1/login/access-token"),
        form={"username": email, "password": password},
        timeout=20,
    )
    if status != 200 or not isinstance(body, dict) or not body.get("access_token"):
        raise RuntimeError(f"login failed ({status}): {body}")
    return str(body["access_token"])


def _register_if_needed(base: str, email: str, password: str) -> None:
    username = email.split("@", 1)[0].replace(".", "")[:20] or "smokeuser"
    status, body = _request(
        "POST",
        _api(base, "/api/v1/users/signup"),
        json_body={"email": email, "password": password, "username": username},
        timeout=20,
    )
    if status not in (200, 400):
        raise RuntimeError(f"signup unexpected ({status}): {body}")


def _consume_sse(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> dict[str, Any]:
    import httpx

    final_text = ""
    thoughts: list[str] = []
    error = ""
    with httpx.Client(timeout=timeout) as client:
        with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code >= 400:
                return {"status_code": resp.status_code, "error": resp.text[:500]}
            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue
                et = event.get("type")
                if et == "thought" and event.get("content"):
                    thoughts.append(str(event["content"]))
                elif et == "token":
                    final_text += str(event.get("content") or "")
                elif et == "final":
                    final_text = str(event.get("content") or final_text)
                elif et == "error":
                    error = str(event.get("content") or "stream error")
    return {
        "status_code": 200,
        "final": final_text,
        "thoughts": thoughts,
        "error": error,
    }


def run_smoke(base_url: str, email: str, password: str, *, chat_timeout: float) -> SmokeReport:
    report = SmokeReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
    )

    # Environment probes (no auth)
    try:
        status, body = _request("GET", _api(base_url, "/api/v1/healthz"), timeout=10)
        report.environment["healthz"] = {"status": status, "body": body}
        report.add(
            CaseResult(
                "healthz",
                "pass" if status == 200 else "fail",
                detail=f"http {status}",
            )
        )
    except Exception as exc:
        report.add(CaseResult("healthz", "fail", detail=str(exc)))

    try:
        status, body = _request("GET", _api(base_url, "/api/v1/readyz"), timeout=15)
        report.environment["readyz"] = {"status": status, "body": body}
        report.add(
            CaseResult(
                "readyz",
                "pass" if status == 200 and isinstance(body, dict) and body.get("db") == "ok" else "fail",
                detail=f"http {status} db={body.get('db') if isinstance(body, dict) else 'n/a'}",
            )
        )
    except Exception as exc:
        report.add(CaseResult("readyz", "fail", detail=str(exc)))

    try:
        _register_if_needed(base_url, email, password)
    except Exception as exc:
        report.add(CaseResult("signup", "skip", detail=str(exc)))

    try:
        token = _login(base_url, email, password)
        report.add(CaseResult("login", "pass", detail="token acquired"))
    except Exception as exc:
        report.add(CaseResult("login", "fail", detail=str(exc)))
        return report

    headers = {"Authorization": f"Bearer {token}"}

    status, me = _request("GET", _api(base_url, "/api/v1/users/me"), headers=headers, timeout=15)
    report.add(
        CaseResult(
            "users/me",
            "pass" if status == 200 else "fail",
            detail=f"http {status}",
            meta={"email": me.get("email") if isinstance(me, dict) else None},
        )
    )

    thread_id = f"smoke_{uuid.uuid4().hex[:10]}"

    # Text chat stream
    try:
        import httpx  # noqa: F401

        stream = _consume_sse(
            _api(base_url, "/api/v1/chat/stream"),
            {
                "user_input": "用一句话解释什么是索引。",
                "thread_id": thread_id,
                "prompt_key": "tutor",
                "max_tokens": 256,
                "tool_mode": "chat",
            },
            headers,
            timeout=chat_timeout,
        )
        ok = stream["status_code"] == 200 and len((stream.get("final") or "").strip()) > 20
        report.add(
            CaseResult(
                "chat_stream_text",
                "pass" if ok else "fail",
                detail=(stream.get("final") or stream.get("error") or "")[:240],
                meta={"thoughts": len(stream.get("thoughts") or [])},
            )
        )
    except ImportError:
        report.add(CaseResult("chat_stream_text", "skip", detail="httpx not installed"))
    except Exception as exc:
        report.add(CaseResult("chat_stream_text", "fail", detail=str(exc)))

    # Multimodal chat stream
    try:
        stream = _consume_sse(
            _api(base_url, "/api/v1/chat/stream"),
            {
                "user_input": "请说明这张图片里有什么内容。",
                "thread_id": f"{thread_id}_img",
                "prompt_key": "tutor",
                "max_tokens": 512,
                "tool_mode": "image_tutoring",
                "image_base64_list": [TINY_PNG_DATA_URL],
                "debug_mode": True,
            },
            headers,
            timeout=max(chat_timeout, 180),
        )
        final = (stream.get("final") or "").strip()
        bad = any(
            k in final
            for k in (
                "无法被识别",
                "无法识别",
                "未能稳定识别",
                "无法稳定识别",
                "未返回有效内容",
                "500 Internal Server Error",
            )
        )
        vision_thoughts = [
            t for t in (stream.get("thoughts") or []) if "视觉识别" in t or "vision" in t.lower()
        ]
        status_label: ResultStatus = "pass"
        if not final:
            status_label = "fail"
        elif bad:
            status_label = "fail"
        report.add(
            CaseResult(
                "chat_stream_multimodal",
                status_label,
                detail=final[:240] or stream.get("error", ""),
                meta={
                    "vision_thoughts": vision_thoughts[:2],
                    "unrecognized_template": bad,
                },
            )
        )
    except Exception as exc:
        report.add(CaseResult("chat_stream_multimodal", "fail", detail=str(exc)))

    # Learning report
    status, lr = _request(
        "GET", _api(base_url, "/api/v1/learning-report/me"), headers=headers, timeout=30
    )
    report.add(
        CaseResult(
            "learning_report_me",
            "pass" if status == 200 else "fail",
            detail=f"http {status}",
            meta={
                "has_summary": bool(isinstance(lr, dict) and (lr.get("summary") or lr.get("overall_summary")))
            },
        )
    )

    for action in ("diagnose", "review-plan", "mistake-digest"):
        try:
            st, body = _request(
                "POST",
                _api(base_url, f"/api/v1/learning-report/actions/{action}"),
                headers=headers,
                json_body={},
                timeout=45,
            )
            degraded = isinstance(body, dict) and body.get("risk_level") == "medium"
            report.add(
                CaseResult(
                    f"learning_report_{action}",
                    "pass" if st == 200 else "fail",
                    detail=f"http {st}",
                    meta={"possibly_template": degraded},
                )
            )
        except Exception as exc:
            report.add(CaseResult(f"learning_report_{action}", "fail", detail=str(exc)))

    status, path = _request(
        "GET", _api(base_url, "/api/v1/learning-path/me"), headers=headers, timeout=20
    )
    has_path = isinstance(path, dict) and bool(path)
    if status == 404:
        report.add(
            CaseResult(
                "learning_path_me",
                "skip",
                detail="endpoint not deployed (404)",
            )
        )
    else:
        report.add(
            CaseResult(
                "learning_path_me",
                "pass" if status == 200 else "fail",
                detail="has_path" if has_path else "null_or_empty",
                meta={"degraded": status == 200 and not has_path},
            )
        )

    # Resource workshop
    try:
        st, pkg = _request(
            "POST",
            _api(base_url, "/api/v1/resource-workshop/packages"),
            headers=headers,
            json_body={"topic": "索引优化", "subject": "数据库", "resource_types": ["concept_card"]},
            timeout=60,
        )
        mode = pkg.get("generation_mode") if isinstance(pkg, dict) else None
        report.add(
            CaseResult(
                "resource_workshop_packages",
                "pass" if st == 200 else "fail",
                detail=f"http {st} mode={mode}",
                meta={"generation_mode": mode},
            )
        )
    except Exception as exc:
        report.add(CaseResult("resource_workshop_packages", "fail", detail=str(exc)))

    try:
        st, grade = _request(
            "POST",
            _api(base_url, "/api/v1/resource-workshop/exercises/grade"),
            headers=headers,
            json_body={
                "subject": "数据库",
                "topic": "索引",
                "question": "什么是覆盖索引？",
                "student_answer": "覆盖索引包含查询所需全部列。",
                "max_score": 10,
            },
            timeout=60,
        )
        report.add(
            CaseResult(
                "resource_workshop_grade",
                "pass" if st == 200 else "fail",
                detail=f"http {st} score={grade.get('score') if isinstance(grade, dict) else 'n/a'}",
            )
        )
    except Exception as exc:
        report.add(CaseResult("resource_workshop_grade", "fail", detail=str(exc)))

    try:
        st, img = _request(
            "POST",
            _api(base_url, "/api/v1/resource-workshop/images/analyze"),
            headers=headers,
            json_body={
                "image_base64": TINY_PNG_DATA_URL.split(",", 1)[1],
                "subject": "通用",
                "question_text": "描述图片",
            },
            timeout=120,
        )
        source = img.get("source") if isinstance(img, dict) else None
        img_status = img.get("status") if isinstance(img, dict) else None
        label: ResultStatus = "pass"
        if st != 200:
            label = "fail"
        elif source == "fallback" or img_status == "fallback":
            label = "degraded"
        report.add(
            CaseResult(
                "resource_workshop_image",
                label,
                detail=f"http {st} source={source} status={img_status}",
            )
        )
    except Exception as exc:
        report.add(CaseResult("resource_workshop_image", "fail", detail=str(exc)))

    # RAG upload (tiny txt)
    try:
        import httpx

        files = {"file": ("smoke.txt", b"ZhiXi smoke test document about database indexes.", "text/plain")}
        data = {"scope": "personal", "title": "smoke"}
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                _api(base_url, "/api/v1/rag/upload"),
                headers=headers,
                files=files,
                data=data,
            )
        body = resp.json() if resp.content else {}
        report.add(
            CaseResult(
                "rag_upload",
                "pass" if resp.status_code == 200 else "fail",
                detail=f"http {resp.status_code}",
                meta={"file_id": body.get("file_id") if isinstance(body, dict) else None},
            )
        )
    except Exception as exc:
        report.add(CaseResult("rag_upload", "fail", detail=str(exc)))

    # Behavior (multipart upload)
    try:
        import httpx

        tiny_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                _api(base_url, "/api/v1/behavior/analyze/image"),
                headers=headers,
                files={"file": ("smoke.png", tiny_bytes, "image/png")},
                data={"course_id": str(uuid.uuid4())},
            )
        body = resp.json() if resp.content else {}
        label: ResultStatus = "pass" if resp.status_code == 200 else "fail"
        if isinstance(body, dict) and body.get("source") == "local_face_fallback":
            label = "degraded"
        report.add(
            CaseResult(
                "behavior_analyze_image",
                label,
                detail=f"http {resp.status_code}",
                meta={"source": body.get("source") if isinstance(body, dict) else None},
            )
        )
    except Exception as exc:
        report.add(CaseResult("behavior_analyze_image", "fail", detail=str(exc)))

    # Teacher dashboard
    for ep in ("stats", "alerts-trend", "popular", "content-distribution"):
        try:
            st, body = _request(
                "GET",
                _api(base_url, f"/api/v1/dashboard/teacher/{ep}"),
                headers=headers,
                timeout=20,
            )
            report.add(
                CaseResult(
                    f"dashboard_teacher_{ep}",
                    "pass" if st == 200 else "fail",
                    detail=f"http {st}",
                )
            )
        except Exception as exc:
            report.add(CaseResult(f"dashboard_teacher_{ep}", "fail", detail=str(exc)))

    # Digital human health (auth required on some deployments)
    try:
        st, body = _request(
            "GET",
            _api(base_url, "/api/v1/digital-human/health"),
            headers=headers,
            timeout=15,
        )
        label: ResultStatus = "pass" if st == 200 else ("skip" if st == 404 else "fail")
        report.add(CaseResult("digital_human_health", label, detail=f"http {st}", meta={"body": body}))
    except Exception as exc:
        report.add(CaseResult("digital_human_health", "skip", detail=str(exc)))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="ZhiXi functional smoke tests")
    parser.add_argument("--base-url", default="http://127.0.0.1:18001")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--chat-timeout", type=float, default=120.0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    started = time.perf_counter()
    report = run_smoke(args.base_url, args.email, args.password, chat_timeout=args.chat_timeout)
    elapsed = round(time.perf_counter() - started, 2)

    payload = {
        "generated_at": report.generated_at,
        "base_url": report.base_url,
        "elapsed_seconds": elapsed,
        "summary": report.summary(),
        "environment": report.environment,
        "results": [asdict(r) for r in report.results],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Wrote report to {args.output}")
    else:
        print(text)

    return 0 if payload["summary"].get("fail", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
