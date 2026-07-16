import httpx
import logging
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from app.backend_pre_start import schema_revision_status
from app.core.config import settings
from app.core.db import engine
from app.services.model_aliases import resolve_model_name_for_base_url
from app.services.vision_client import probe_multimodal_health

router = APIRouter()
logger = logging.getLogger(__name__)


def _probe_ollama(base_url: str) -> dict:
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.0)
        response.raise_for_status()
        return {"reachable": True, "base_url": base_url}
    except Exception as exc:
        return {"reachable": False, "base_url": base_url, "detail": str(exc)}


def _probe_ollama_embedding(base_url: str, model: str) -> dict:
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/api/embed",
            json={"model": model, "input": "health check"},
            timeout=10.0,
        )
        response.raise_for_status()
        embeddings = response.json().get("embeddings") or []
        if not embeddings or not embeddings[0]:
            raise ValueError("embedding provider returned no vector")
        return {"configured": True, "reachable": True, "base_url": base_url}
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "base_url": base_url,
            "detail": str(exc)[:240],
        }


def _probe_openai_embedding(base_url: str | None) -> dict:
    configured = bool(
        base_url and settings.OPENAI_API_KEY and settings.OPENAI_EMBEDDING_MODEL
    )
    if not configured:
        return {"configured": False, "reachable": False, "base_url": base_url}
    try:
        response = httpx.post(
            f"{base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "input": ["health check"],
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json().get("data") or []
        if not data or not data[0].get("embedding"):
            raise ValueError("embedding provider returned no vector")
        return {"configured": True, "reachable": True, "base_url": base_url}
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "base_url": base_url,
            "detail": str(exc)[:240],
        }


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


def _embedding_check(deep: bool = False) -> dict:
    provider = settings.EMBEDDINGS_PROVIDER.lower()
    out = {"provider": settings.EMBEDDINGS_PROVIDER}
    if provider == "ollama":
        probe = (
            _probe_ollama_embedding(
                settings.OLLAMA_BASE_URL, settings.OLLAMA_EMBEDDINGS_MODEL
            )
            if deep
            else {
                "configured": True,
                "reachable": None,
                "base_url": settings.OLLAMA_BASE_URL,
            }
        )
        out.update(
            {
                "model": settings.OLLAMA_EMBEDDINGS_MODEL,
                "default_local_model": True,
                **probe,
            }
        )
    elif provider in {"openai", "openai_compatible", "cloud"}:
        probe = (
            _probe_openai_embedding(settings.OPENAI_API_BASE)
            if deep
            else {
                "configured": bool(
                    settings.OPENAI_API_KEY and settings.OPENAI_API_BASE
                ),
                "reachable": None,
                "base_url": settings.OPENAI_API_BASE,
            }
        )
        out.update({"model": settings.OPENAI_EMBEDDING_MODEL, **probe})
    elif provider == "hash":
        out.update(
            {
                "configured": True,
                "reachable": True,
                "degraded": True,
                "detail": (
                    "deterministic fallback; configure a semantic embedding "
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


def _build_model_checks(deep: bool = False) -> dict:
    chat_provider = settings.CHAT_PROVIDER.lower()
    chat_check = {
        "provider": settings.CHAT_PROVIDER,
        "model": _chat_model_name(chat_provider),
    }
    if not deep:
        if chat_provider == "mimo":
            chat_check.update(
                {
                    "configured": bool(settings.MIMO_API_KEY),
                    "reachable": None,
                    "base_url": settings.MIMO_API_BASE,
                    "detail": "provider reachability is not exposed by the public health endpoint",
                }
            )
        elif chat_provider == "ollama":
            chat_check.update(
                {
                    "configured": True,
                    "reachable": None,
                    "base_url": settings.OLLAMA_BASE_URL,
                    "detail": "provider reachability is not exposed by the public health endpoint",
                }
            )
        elif chat_provider in {"openai", "openai_compatible"}:
            chat_check.update(
                {
                    "configured": bool(settings.OPENAI_API_KEY and settings.OPENAI_API_BASE),
                    "reachable": None,
                    "base_url": settings.OPENAI_API_BASE,
                    "detail": "provider reachability is not exposed by the public health endpoint",
                }
            )
        else:
            chat_check.update({"configured": False, "reachable": False, "detail": "unsupported provider"})
    elif chat_provider == "ollama":
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
    if not deep:
        multimodal_check.update(
            {
                "configured": bool(
                    (settings.MULTIMODAL_API_KEY or settings.MIMO_API_KEY)
                    and _multimodal_base_url()
                ),
                "reachable": None,
                "base_url": multimodal_base,
                "detail": "provider reachability is not exposed by the public health endpoint",
            }
        )
    elif settings.MULTIMODAL_PROVIDER.lower() == "mimo":
        multimodal_check.update(_probe_mimo())
    else:
        multimodal_check.update(_probe_openai_compatible(multimodal_base))
    if deep:
        try:
            multimodal_check["vision_probe"] = probe_multimodal_health(timeout=30.0)
            # The deep image probe is authoritative for the multimodal
            # capability. A successful text/models probe must not mask a
            # failed vision request.
            multimodal_check["reachable"] = bool(
                multimodal_check["vision_probe"].get("probe_ok")
            )
        except Exception as exc:
            multimodal_check["vision_probe"] = {
                "configured": bool(multimodal_base),
                "probe_ok": False,
                "detail": str(exc)[:240],
            }
            multimodal_check["reachable"] = False
    return {
        "chat_model": chat_check,
        "multimodal_model": multimodal_check,
        "embedding_model": _embedding_check(deep=deep),
    }


def _capability_status(models: dict) -> str:
    """Separate infrastructure readiness from optional AI capability quality."""

    checks = {
        name: check for name, check in models.items() if isinstance(check, dict)
    }
    chat = checks.get("chat_model", {})
    if chat.get("configured") is False or chat.get("reachable") is False:
        return "unavailable"
    if any(
        bool(check.get("degraded"))
        or check.get("configured") is False
        or check.get("reachable") is False
        for check in checks.values()
    ):
        return "degraded"
    return "available"


@router.get('/healthz')
def healthz(deep: bool = Query(False, deprecated=True)):
    # Keep the old query parameter parseable for rollout compatibility, but a
    # public request must never be able to trigger paid/slow upstream probes.
    _ = deep
    models = _build_model_checks(deep=False)
    return {
        'service': 'backend',
        'status': 'ok',
        'capability_status': _capability_status(models),
        'models': models,
    }


@router.get('/readyz')
def readyz(deep: bool = Query(False, deprecated=True)):
    try:
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
            schema = schema_revision_status(conn)
        if schema["status"] != "current":
            logger.error(
                "Readiness rejected an outdated database schema: current=%s expected=%s",
                schema["current"],
                schema["expected"],
            )
            raise HTTPException(status_code=503, detail='database schema is not current')
        _ = deep
        models = _build_model_checks(deep=False)
        return {
            'service': 'backend',
            'status': 'ready',
            'capability_status': _capability_status(models),
            'db': 'ok',
            'schema': schema,
            'models': models,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Backend readiness check failed")
        raise HTTPException(status_code=503, detail='ready check failed')
