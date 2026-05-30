import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine

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


def _build_model_checks() -> dict:
    chat_provider = settings.CHAT_PROVIDER.lower()
    chat_check = {
        "provider": settings.CHAT_PROVIDER,
        "model": settings.OLLAMA_MODEL if chat_provider == "ollama" else settings.CHAT_MODEL,
    }
    if chat_provider == "ollama":
        chat_check.update(_probe_ollama(settings.OLLAMA_BASE_URL))
    elif chat_provider in {"openai", "openai_compatible"}:
        chat_check.update(_probe_openai_compatible(settings.OPENAI_API_BASE))
    else:
        chat_check.update({"reachable": False, "detail": "unsupported provider"})

    multimodal_check = {
        "provider": settings.MULTIMODAL_PROVIDER,
        "model": settings.MULTIMODAL_MODEL,
        "fallback_model": settings.MULTIMODAL_FALLBACK_MODEL,
    }
    multimodal_check.update(_probe_openai_compatible(settings.MULTIMODAL_API_BASE))
    return {"chat_model": chat_check, "multimodal_model": multimodal_check}


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
