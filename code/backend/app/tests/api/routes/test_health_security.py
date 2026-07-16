from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import health
from app.core.config import settings


@pytest.mark.parametrize("path", ["/healthz", "/readyz"])
def test_anonymous_deep_query_never_calls_ai_upstreams(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    upstream_calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal upstream_calls
        upstream_calls += 1
        raise AssertionError("anonymous health check called an AI upstream")

    for name in (
        "_probe_mimo",
        "_probe_ollama",
        "_probe_ollama_embedding",
        "_probe_openai_embedding",
        "_probe_openai_compatible",
        "probe_multimodal_health",
    ):
        monkeypatch.setattr(health, name, forbidden)
    monkeypatch.setattr(settings, "CHAT_PROVIDER", "mimo")
    monkeypatch.setattr(settings, "MULTIMODAL_PROVIDER", "mimo")
    monkeypatch.setattr(settings, "EMBEDDINGS_PROVIDER", "ollama")

    response = client.get(
        f"{settings.API_V1_STR}{path}",
        params={"deep": "true"},
    )

    assert response.status_code == 200
    assert upstream_calls == 0
    assert response.json()["models"]["chat_model"]["reachable"] is None
