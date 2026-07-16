from __future__ import annotations

from urllib.parse import urlparse


_OLLAMA_MODEL_ALIASES = {
    "qwen3-14b-instruct": "qwen3:14b",
    "qwen3-vl-8b-instruct": "qwen3-vl:8b",
    "qwen3-vl-4b-instruct": "qwen3-vl:8b",
}


def is_local_ollama_compatible(base_url: str | None) -> bool:
    if not base_url:
        return False
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    return host in {"127.0.0.1", "localhost"} and parsed.port == 11434


def resolve_model_name_for_base_url(model_name: str, base_url: str | None) -> str:
    if not is_local_ollama_compatible(base_url):
        return model_name
    normalized = (model_name or "").strip().lower()
    return _OLLAMA_MODEL_ALIASES.get(normalized, model_name)
