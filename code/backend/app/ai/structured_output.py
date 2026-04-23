from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class StructuredCitation(BaseModel):
    citation_id: int = Field(description="引用的知识库片段编号，对应候选列表中的 citation_id")
    snippet: str = Field(default="", description="引用证据的简短摘要")
    relevance_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="该证据与答案的相关性评分",
    )
    reason: str = Field(default="", description="为何使用该证据")


class StructuredAnswerPayload(BaseModel):
    answer: str = Field(description="面向学生展示的最终回答正文，使用 Markdown")
    confidence: str = Field(
        default="medium",
        description="回答置信等级，只能是 high / medium / low",
    )
    grounding_mode: str = Field(
        default="general",
        description="回答依据类型：rag / general / tool / mixed",
    )
    citations: list[StructuredCitation] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)


_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")


def build_citation_candidates(rag_results: list[dict[str, Any]]) -> str:
    if not rag_results:
        return "（无知识库候选片段）"
    blocks: list[str] = []
    for item in rag_results[:6]:
        citation_id = int(item.get("citation_id") or 0)
        score = float(item.get("score") or 0.0)
        source = str(item.get("source") or "unknown")
        chunk_id = item.get("chunk_id")
        content = str(item.get("content") or "").strip().replace("\n", " ")
        if len(content) > 220:
            content = content[:220] + "…"
        blocks.append(
            f"- citation_id={citation_id} | source={source} | chunk_id={chunk_id} | "
            f"score={score:.3f} | snippet={content}"
        )
    return "\n".join(blocks)


def parse_structured_payload(raw: str) -> StructuredAnswerPayload | None:
    text = (raw or "").strip()
    if not text:
        return None
    candidates = [text]
    match = _JSON_OBJECT_RE.search(text)
    if match and match.group(0) not in candidates:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            return StructuredAnswerPayload.model_validate_json(candidate)
        except Exception:
            pass
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return StructuredAnswerPayload.model_validate(obj)
        except Exception:
            continue
    return None


def normalize_confidence(value: str | None) -> str:
    normalized = str(value or "medium").strip().lower()
    if normalized not in {"high", "medium", "low"}:
        return "medium"
    return normalized


def normalize_grounding_mode(value: str | None, *, has_citations: bool) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"rag", "general", "tool", "mixed"}:
        return normalized
    return "rag" if has_citations else "general"
