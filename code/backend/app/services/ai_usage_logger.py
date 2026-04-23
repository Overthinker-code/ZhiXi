from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from langchain_core.messages import AIMessage
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.chat_runtime import get_active_model_name
from app.core.config import settings
from app.models.ai_usage_log import AIUsageLog


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _estimate_tokens_from_text(text: str) -> int:
    compact = (text or "").strip()
    if not compact:
        return 0
    return max(1, round(len(compact) / 2.2))


def collect_usage_from_messages(messages: list[Any]) -> dict[str, Any]:
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    estimated = False

    for message in messages or []:
        if not isinstance(message, AIMessage):
            continue
        usage = getattr(message, "usage_metadata", None) or {}
        response_meta = getattr(message, "response_metadata", None) or {}
        token_usage = response_meta.get("token_usage") if isinstance(response_meta, dict) else {}

        in_tokens = (
            usage.get("input_tokens")
            or token_usage.get("prompt_tokens")
            or token_usage.get("input_tokens")
        )
        out_tokens = (
            usage.get("output_tokens")
            or token_usage.get("completion_tokens")
            or token_usage.get("output_tokens")
        )
        all_tokens = usage.get("total_tokens") or token_usage.get("total_tokens")

        if in_tokens or out_tokens or all_tokens:
            prompt_tokens += int(in_tokens or 0)
            completion_tokens += int(out_tokens or 0)
            total_tokens += int(all_tokens or ((in_tokens or 0) + (out_tokens or 0)))
            continue

        estimated = True
        body = getattr(message, "content", "")
        if isinstance(body, list):
            body = "\n".join(
                str(block.get("text", "")) if isinstance(block, dict) else str(block)
                for block in body
            )
        completion_tokens += _estimate_tokens_from_text(str(body))

    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens or None,
        "completion_tokens": completion_tokens or None,
        "total_tokens": total_tokens or None,
        "estimated": estimated,
    }


def persist_ai_usage(
    db: Session,
    *,
    user_id: str | None,
    thread_id: str,
    prompt_key: str | None,
    status: str,
    cache_hit: bool,
    grounding_mode: str | None,
    confidence: str | None,
    ttft_ms: int | None,
    latency_ms: int | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
    agent_hops: int | None,
    tool_calls_count: int | None,
    rag_hit_count: int | None,
    route_trace: list[str] | None,
    estimated: bool,
    extra: dict[str, Any] | None = None,
) -> AIUsageLog:
    row = AIUsageLog(
        user_id=user_id,
        thread_id=thread_id or "default",
        prompt_key=prompt_key,
        provider=settings.CHAT_PROVIDER.lower(),
        model=get_active_model_name(),
        status=status or "success",
        cache_hit=bool(cache_hit),
        grounding_mode=grounding_mode,
        confidence=confidence,
        ttft_ms=_safe_int(ttft_ms),
        latency_ms=_safe_int(latency_ms),
        prompt_tokens=_safe_int(prompt_tokens),
        completion_tokens=_safe_int(completion_tokens),
        total_tokens=_safe_int(total_tokens),
        agent_hops=_safe_int(agent_hops),
        tool_calls_count=_safe_int(tool_calls_count),
        rag_hit_count=_safe_int(rag_hit_count),
        route_trace=json.dumps(route_trace or [], ensure_ascii=False),
        extra_json=json.dumps(extra or {}, ensure_ascii=False),
        estimated=bool(estimated),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def summarize_recent_metrics(db: Session, *, days: int = 7) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=max(1, days))
    query = db.query(AIUsageLog).filter(AIUsageLog.created_at >= since)
    rows = query.all()
    total = len(rows)
    if total == 0:
        return {
            "window_days": days,
            "requests": 0,
            "avg_ttft_ms": 0,
            "avg_latency_ms": 0,
            "avg_agent_hops": 0,
            "cache_hit_rate": 0,
            "rag_grounded_rate": 0,
            "total_tokens": 0,
        }

    def avg(values: list[int | float | None]) -> float:
        nums = [float(v) for v in values if v is not None]
        if not nums:
            return 0.0
        return round(sum(nums) / len(nums), 2)

    cache_hits = sum(1 for row in rows if row.cache_hit)
    rag_grounded = sum(1 for row in rows if (row.grounding_mode or "").lower() in {"rag", "mixed"})
    total_tokens = sum(int(row.total_tokens or 0) for row in rows)
    return {
        "window_days": days,
        "requests": total,
        "avg_ttft_ms": avg([row.ttft_ms for row in rows]),
        "avg_latency_ms": avg([row.latency_ms for row in rows]),
        "avg_agent_hops": avg([row.agent_hops for row in rows]),
        "cache_hit_rate": round(cache_hits / total, 4),
        "rag_grounded_rate": round(rag_grounded / total, 4),
        "total_tokens": total_tokens,
        "last_updated_at": datetime.utcnow().isoformat(),
    }
