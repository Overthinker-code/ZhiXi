import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.services.model_aliases import resolve_model_name_for_base_url
from app.services.vision_client import probe_multimodal_health

router = APIRouter()


def _probe_ollama(base_url: str) -> dict:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.0)
        response.raise_for_status()
        return {"reachable": True, "base_url": base_url}
    except Exception as exc:
        return {"reachable": False, "base_url": base_url, "detail": str(exc)}


def _probe_openai_compatible(base_url: str | None) -> dict:
    if not base_url:
        return {"configured": False, "reachable": False}
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=2.0)
        response.raise_for_status()
        return {"configured": True, "reachable": True, "base_url": base_url}
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "base_url": base_url,
            "detail": str(exc),
        }


def _probe_mimo() -> dict:
    base_url = settings.MIMO_API_BASE
    if not settings.MIMO_API_KEY:
        return {"configured": False, "reachable": False, "base_url": base_url}
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.MIMO_API_KEY}",
                "api-key": settings.MIMO_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": settings.MIMO_FAST_MODEL or settings.MIMO_CHAT_MODEL,
                "messages": [{"role": "user", "content": "ping"}],
                "max_completion_tokens": 8,
                "temperature": 0,
                "stream": False,
                "thinking": {"type": "disabled"},
            },
            timeout=10.0,
        )
        response.raise_for_status()
        return {"configured": True, "reachable": True, "base_url": base_url}
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "base_url": base_url,
            "detail": str(exc)[:240],
        }


def _embedding_check() -> dict:
    provider = settings.EMBEDDINGS_PROVIDER.lower()
    out = {"provider": settings.EMBEDDINGS_PROVIDER}
    if provider == "ollama":
        out.update(
            {
                "model": settings.OLLAMA_EMBEDDINGS_MODEL,
                "default_local_model": True,
                **_probe_ollama(settings.OLLAMA_BASE_URL),
            }
        )
    elif provider in {"openai", "openai_compatible", "cloud"}:
        out.update(
            {
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "configured": bool(
                    settings.OPENAI_API_KEY and settings.OPENAI_API_BASE
                ),
                "base_url": settings.OPENAI_API_BASE,
            }
        )
    elif provider == "hash":
        out.update(
            {
                "configured": True,
                "reachable": True,
                "degraded": True,
                "detail": (
                    "deterministic fallback; configure a cloud embedding "
                    "provider for semantic RAG"
                ),
            }
        )
    else:
        out.update(
            {"configured": False, "reachable": False, "detail": "unsupported provider"}
        )
    return out


def _chat_model_name(provider: str) -> str:
    if provider == "ollama":
        return settings.OLLAMA_MODEL
    if provider == "mimo":
        return settings.MIMO_CHAT_MODEL
    return settings.CHAT_MODEL


def _multimodal_base_url() -> str | None:
    if settings.MULTIMODAL_PROVIDER.lower() == "mimo":
        return settings.MULTIMODAL_API_BASE or settings.MIMO_API_BASE
    return settings.MULTIMODAL_API_BASE


def _build_model_checks() -> dict:
    chat_provider = settings.CHAT_PROVIDER.lower()
    chat_check = {
        "provider": settings.CHAT_PROVIDER,
        "model": _chat_model_name(chat_provider),
    }
    if chat_provider == "ollama":
        chat_check.update(_probe_ollama(settings.OLLAMA_BASE_URL))
    elif chat_provider == "mimo":
        chat_check.update(_probe_mimo())
    elif chat_provider in {"openai", "openai_compatible"}:
        chat_check.update(_probe_openai_compatible(settings.OPENAI_API_BASE))
    else:
        chat_check.update({"reachable": False, "detail": "unsupported provider"})

    multimodal_check = {
        "provider": settings.MULTIMODAL_PROVIDER,
        "model": settings.MULTIMODAL_MODEL,
        "runtime_model": resolve_model_name_for_base_url(
            settings.MULTIMODAL_MODEL,
            _multimodal_base_url(),
        ),
        "fallback_model": settings.MULTIMODAL_FALLBACK_MODEL,
    }
    multimodal_base = _multimodal_base_url()
    if settings.MULTIMODAL_PROVIDER.lower() == "mimo":
        multimodal_check.update(_probe_mimo())
    else:
        multimodal_check.update(_probe_openai_compatible(multimodal_base))
    try:
        multimodal_check["vision_probe"] = probe_multimodal_health(timeout=30.0)
        if multimodal_check["vision_probe"].get("probe_ok"):
            multimodal_check["reachable"] = True
    except Exception as exc:
        multimodal_check["vision_probe"] = {
            "configured": bool(multimodal_base),
            "probe_ok": False,
            "detail": str(exc)[:240],
        }
    return {
        "chat_model": chat_check,
        "multimodal_model": multimodal_check,
        "embedding_model": _embedding_check(),
    }


@router.get('/healthz')
def healthz():
    return {'service': 'backend', 'status': 'ok', 'models': _build_model_checks()}


@router.get('/readyz')
def readyz():
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return {
            'service': 'backend',
            'status': 'ready',
            'db': 'ok',
            'models': _build_model_checks(),
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f'ready check failed: {exc}')
