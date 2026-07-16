from __future__ import annotations

from typing import Any


def extract_openai_compatible_content(message: dict[str, Any] | None) -> str:
    """Read assistant text from OpenAI-compatible responses (incl. Ollama Qwen3 reasoning fields)."""
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text") or block.get("content") or ""))
            else:
                parts.append(str(block))
        content = "\n".join(parts)
    text = str(content or "").strip()
    if text:
        return text
    for key in ("reasoning", "reasoning_content", "thinking"):
        alt = message.get(key)
        if isinstance(alt, list):
            alt = "\n".join(str(x) for x in alt)
        alt = str(alt or "").strip()
        if alt:
            return alt
    return ""


def summarize_vision_message_fields(message: dict[str, Any] | None) -> dict[str, Any]:
    """Non-sensitive debug snapshot of which response fields were populated."""
    if not isinstance(message, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("content", "reasoning", "reasoning_content", "thinking"):
        val = message.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            text = "\n".join(str(x) for x in val)
        else:
            text = str(val)
        text = text.strip()
        if text:
            out[key] = len(text)
    return out
