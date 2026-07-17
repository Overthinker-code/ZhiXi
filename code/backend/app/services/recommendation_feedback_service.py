"""Bounded signed implicit-feedback aggregation for recommendation ranking."""
from __future__ import annotations

import math
import hashlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable


FEEDBACK_METHOD_VERSION = "recommendation_feedback_v1"
FEEDBACK_HALF_LIFE_DAYS = 21
# Values are preference signals, never assessment scores. LearningEvidence
# stores a non-negative weight; the signed value is deliberately in payload.
ACTION_WEIGHTS: dict[str, float] = {
    "recommendation_previewed": 0.20,
    "source_opened": 0.35,
    "resource_previewed": 0.18,
    "resource_downloaded": 0.30,
    "resource_favorited": 0.85,
    "resource_unfavorited": -0.35,
    "resource_added_to_library": 0.75,
    "resource_pinned": 0.55,
    "resource_unpinned": -0.20,
    "recommendation_dismissed": -0.80,
    "resource_removed_from_library": -0.70,
    # Regeneration means the topic still matters, but this presentation did not
    # quite fit. Per-dimension multipliers below preserve that distinction.
    "external_resource_regenerated": 0.20,
    "generated_resource_regenerated": 0.20,
}
# The same action should not update every portrait dimension equally. For
# example, dismissing one resource is weak evidence against its topic and even
# weaker evidence against an entire subject; regenerating keeps a small positive
# topic signal while reducing the modality preference.
ACTION_DIMENSION_MULTIPLIERS: dict[str, dict[str, float]] = {
    "recommendation_dismissed": {
        "modalities": 0.50, "topics": 0.35, "subjects": 0.15, "origins": 0.25,
    },
    "resource_removed_from_library": {
        "modalities": 0.65, "topics": 0.45, "subjects": 0.20, "origins": 0.30,
    },
    "external_resource_regenerated": {
        "modalities": -0.75, "topics": 0.50, "subjects": 0.10, "origins": -0.50,
    },
    "generated_resource_regenerated": {
        "modalities": -0.75, "topics": 0.50, "subjects": 0.10, "origins": -0.25,
    },
    "source_opened": {
        "modalities": 0.70, "topics": 1.00, "subjects": 0.55, "origins": 1.00,
    },
}
DEDUPE_WINDOWS_SECONDS: dict[str, int] = {
    "recommendation_previewed": 30 * 60,
    "source_opened": 30 * 60,
    "resource_previewed": 30 * 60,
    "resource_downloaded": 10 * 60,
}


def signed_weight(event_type: str) -> float:
    return ACTION_WEIGHTS.get(event_type, 0.0)


def dimension_signed_weights(event_type: str) -> dict[str, float]:
    base = signed_weight(event_type)
    multipliers = ACTION_DIMENSION_MULTIPLIERS.get(event_type, {})
    return {
        group: round(base * float(multipliers.get(group, 1.0)), 4)
        for group in ("modalities", "topics", "subjects", "origins")
    }


def feedback_idempotency_key(identity: str, event_type: str, observed_at: datetime) -> str:
    window = DEDUPE_WINDOWS_SECONDS.get(event_type)
    if not window:
        raw_key = f"feedback:{identity}:{event_type}:{observed_at.isoformat()}"
    else:
        timestamp = observed_at.timestamp()
        raw_key = f"feedback:{identity}:{event_type}:{int(timestamp // window)}"
    # LearningEvidence.idempotency_key is varchar(64). Hash both windowed and
    # one-off identities so PostgreSQL and SQLite enforce the same contract.
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _decay(observed_at: datetime, now: datetime) -> float:
    observed_at = _as_utc(observed_at)
    now = _as_utc(now)
    age_days = max(0.0, (now - observed_at).total_seconds() / 86400)
    return math.pow(0.5, age_days / FEEDBACK_HALF_LIFE_DAYS)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def aggregate_feedback(rows: Iterable[Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Aggregate Evidence-like rows into a compact JSON profile field."""
    current = _as_utc(now or datetime.now(timezone.utc))
    buckets: dict[str, dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(lambda: {"positive_weight": 0.0, "negative_weight": 0.0, "sample_count": 0.0})
    )
    for row in rows:
        payload = row.payload if isinstance(getattr(row, "payload", None), dict) else {}
        weight = payload.get("signed_preference_weight")
        try:
            signed = float(weight)
        except (TypeError, ValueError):
            signed = signed_weight(str(getattr(row, "event_type", "")))
        if not signed:
            continue
        decay = _decay(getattr(row, "observed_at", current), current)
        dimension_weights = payload.get("dimension_preference_weights")
        dimension_weights = dimension_weights if isinstance(dimension_weights, dict) else {}
        attributes = {
            "modalities": payload.get("resource_type") or payload.get("modality"),
            "topics": payload.get("topic") or getattr(row, "display_name", None),
            "subjects": payload.get("subject"),
            "origins": payload.get("origin"),
        }
        for group, value in attributes.items():
            label = str(value or "").strip()
            if not label:
                continue
            try:
                group_signed = float(dimension_weights.get(group, signed))
            except (TypeError, ValueError):
                group_signed = signed
            decayed = group_signed * decay
            if not decayed:
                continue
            bucket = buckets[group][label]
            if decayed > 0:
                bucket["positive_weight"] += decayed
            else:
                bucket["negative_weight"] += abs(decayed)
            bucket["sample_count"] += 1
    result: dict[str, Any] = {"method_version": FEEDBACK_METHOD_VERSION, "updated_at": current.isoformat()}
    for group, values in buckets.items():
        serialized: dict[str, dict[str, float | int]] = {}
        for name, item in sorted(
            values.items(),
            key=lambda pair: abs(pair[1]["positive_weight"] - pair[1]["negative_weight"]),
            reverse=True,
        )[:12]:
            positive = round(min(3.0, item["positive_weight"]), 4)
            negative = round(min(3.0, item["negative_weight"]), 4)
            serialized[name] = {
                "positive_weight": positive,
                "negative_weight": negative,
                # Keep the persisted audit fields mathematically consistent.
                "affinity": round(max(-3.0, min(3.0, positive - negative)), 4),
                "sample_count": int(item["sample_count"]),
            }
        result[group] = serialized
    return result
