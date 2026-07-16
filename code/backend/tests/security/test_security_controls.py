from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import time
import os
import subprocess
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse
from starlette.requests import Request
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes.behavior_analysis import _extract_ws_token
from app.api.routes.resources import _resolve_resource_file
from app.api.v1.endpoints import health
from app.core.config import Settings, settings
from app.core.http_security import (
    AIRequestBudgetMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.upload_security import sanitize_filename, validate_upload, validate_upload_metadata


def _settings_kwargs() -> dict:
    return {
        "PROJECT_NAME": "test",
        "POSTGRES_SERVER": "localhost",
        "POSTGRES_USER": "test",
        "POSTGRES_PASSWORD": "a-secure-database-password",
        "POSTGRES_DB": "test",
        "FIRST_SUPERUSER": "admin@example.com",
        "FIRST_SUPERUSER_PASSWORD": "a-secure-admin-password",
        "DEVELOPER_PANEL_ENABLED": False,
    }


def test_production_rejects_short_jwt_secret() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(
            _env_file=None,
            **_settings_kwargs(),
            ENVIRONMENT="production",
            SECRET_KEY="short",
            FRONTEND_HOST="https://app.example.com",
            TRUSTED_HOSTS=["api.example.com"],
        )


def test_local_allows_short_secret_with_warning() -> None:
    with pytest.warns(UserWarning, match="SECRET_KEY"):
        result = Settings(
            _env_file=None,
            **_settings_kwargs(),
            ENVIRONMENT="local",
            SECRET_KEY="short",
        )
    assert result.ENVIRONMENT == "local"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("SECRET_KEY", "replace-with-secure-value"),
        ("POSTGRES_PASSWORD", "short"),
        ("POSTGRES_PASSWORD", "your-password-here"),
        ("FIRST_SUPERUSER_PASSWORD", "password123"),
        ("FIRST_SUPERUSER_PASSWORD", "too-short"),
    ],
)
def test_non_local_rejects_weak_or_placeholder_credentials(field: str, value: str) -> None:
    payload = {
        **_settings_kwargs(),
        "ENVIRONMENT": "production",
        "SECRET_KEY": "a-production-jwt-secret-with-more-than-32-characters",
        "FRONTEND_HOST": "https://app.example.com",
        "TRUSTED_HOSTS": ["api.example.com"],
        field: value,
    }
    with pytest.raises(ValidationError, match=field):
        Settings(_env_file=None, **payload)


def test_local_weak_passwords_warn_but_do_not_block_startup() -> None:
    with pytest.warns(UserWarning) as warnings:
        result = Settings(
            _env_file=None,
            **{
                **_settings_kwargs(),
                "POSTGRES_PASSWORD": "short",
                "FIRST_SUPERUSER_PASSWORD": "short",
            },
            ENVIRONMENT="local",
            SECRET_KEY="",
        )
    warning_text = "\n".join(str(item.message) for item in warnings)
    assert "POSTGRES_PASSWORD" in warning_text
    assert "FIRST_SUPERUSER_PASSWORD" in warning_text
    assert len(result.SECRET_KEY) >= 32


async def _ok(_request):
    return PlainTextResponse("ok")


async def _read_body(request: Request):
    await request.body()
    return PlainTextResponse("ok")


def test_security_headers_and_request_size_limit() -> None:
    app = Starlette(routes=[Route("/", _ok, methods=["POST"])])
    app = SecurityHeadersMiddleware(RequestSizeLimitMiddleware(app, max_bytes=4))
    client = TestClient(app)

    accepted = client.post("/", content=b"1234")
    assert accepted.status_code == 200
    assert accepted.headers["x-content-type-options"] == "nosniff"
    assert accepted.headers["x-frame-options"] == "DENY"

    rejected = client.post("/", content=b"12345")
    assert rejected.status_code == 413


def test_chunked_body_returns_exactly_one_413_response() -> None:
    app = RequestSizeLimitMiddleware(
        Starlette(routes=[Route("/", _read_body, methods=["POST"])]),
        max_bytes=4,
    )
    client = TestClient(app)
    response = client.post("/", content=iter([b"12", b"345"]))
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}

    async def direct_receive_test() -> None:
        messages = iter(
            [
                {"type": "http.request", "body": b"12", "more_body": True},
                {"type": "http.request", "body": b"345", "more_body": False},
            ]
        )
        sent: list[dict] = []

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": [],
            "client": ("127.0.0.1", 1),
        }
        await app(scope, receive, send)
        starts = [item for item in sent if item["type"] == "http.response.start"]
        assert [item["status"] for item in starts] == [413]

    asyncio.run(direct_receive_test())


def test_size_limit_never_double_starts_after_downstream_headers() -> None:
    async def early_start_app(_scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await receive()

    app = RequestSizeLimitMiddleware(early_start_app, max_bytes=1)

    async def exercise() -> None:
        sent: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b"12", "more_body": False}

        async def send(message):
            sent.append(message)

        await app(
            {"type": "http", "method": "POST", "path": "/", "headers": []},
            receive,
            send,
        )
        starts = [item for item in sent if item["type"] == "http.response.start"]
        assert [item["status"] for item in starts] == [200]

    asyncio.run(exercise())


def test_trusted_host_and_cors_are_allowlists() -> None:
    app = Starlette(routes=[Route("/", _ok, methods=["GET"])])
    app = CORSMiddleware(
        app,
        allow_origins=["https://app.example.com"],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["Authorization"],
    )
    app = TrustedHostMiddleware(app, allowed_hosts=["api.example.com"])
    client = TestClient(app, base_url="https://api.example.com")

    allowed = client.get("/", headers={"Origin": "https://app.example.com"})
    assert allowed.headers["access-control-allow-origin"] == "https://app.example.com"
    rejected_origin = client.get("/", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in rejected_origin.headers
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_upload_rejects_mime_mismatch_and_sanitizes_name() -> None:
    upload = UploadFile(
        filename="../../unsafe name.pdf",
        file=BytesIO(b"%PDF"),
        headers=Headers({"content-type": "image/png"}),
    )
    with pytest.raises(Exception) as exc_info:
        validate_upload_metadata(upload, allowed_extensions={".pdf"})
    assert getattr(exc_info.value, "status_code", None) == 415
    assert sanitize_filename("../../unsafe name.pdf") == "unsafe_name.pdf"


def test_upload_checks_binary_signature() -> None:
    upload = UploadFile(
        filename="fake.pdf",
        file=BytesIO(b"not-a-pdf"),
        headers=Headers({"content-type": "application/pdf"}),
    )

    async def exercise() -> None:
        with pytest.raises(Exception) as exc_info:
            await validate_upload(upload, allowed_extensions={".pdf"})
        assert getattr(exc_info.value, "status_code", None) == 415

    asyncio.run(exercise())


def test_generated_resource_path_cannot_escape_package_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "BASE_PATH", str(tmp_path))
    resource = SimpleNamespace(
        package_id="package-1",
        file_path="generated_resources/package-1/../../secret.txt",
    )
    with pytest.raises(Exception) as exc_info:
        _resolve_resource_file(resource)
    assert getattr(exc_info.value, "status_code", None) == 404


class _FakeWebSocket:
    def __init__(self, protocols: str = "") -> None:
        self.headers = Headers({"sec-websocket-protocol": protocols})


def test_websocket_token_prefers_subprotocol(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    token, used_subprotocol = _extract_ws_token(
        _FakeWebSocket("authorization, header.jwt.token"), "query-token"
    )
    assert token is None
    assert used_subprotocol is False

    token, used_subprotocol = _extract_ws_token(
        _FakeWebSocket("authorization, header.jwt.token"), None
    )
    assert token == "header.jwt.token"
    assert used_subprotocol is True


def test_production_rejects_code_execution() -> None:
    with pytest.raises(ValidationError, match="CODE_SANDBOX_ENABLED"):
        Settings(
            _env_file=None,
            **_settings_kwargs(),
            ENVIRONMENT="production",
            SECRET_KEY="x" * 48,
            FRONTEND_HOST="https://app.example.com",
            TRUSTED_HOSTS=["api.example.com"],
            CODE_SANDBOX_ENABLED=True,
        )


@pytest.mark.parametrize(
    "field",
    ["ENABLE_MOCK_ROUTES", "DEMO_FAKE_CHAT_CACHE", "DEVELOPER_PANEL_ENABLED"],
)
def test_production_rejects_mock_and_developer_surfaces(field: str) -> None:
    payload = {
        **_settings_kwargs(),
        "ENVIRONMENT": "production",
        "SECRET_KEY": "x" * 48,
        "FRONTEND_HOST": "https://app.example.com",
        "TRUSTED_HOSTS": ["api.example.com"],
        field: True,
    }
    with pytest.raises(ValidationError, match=field):
        Settings(_env_file=None, **payload)


def test_ai_budget_releases_slot_when_request_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_SSE_MAX_CONCURRENT_PER_USER", 1)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 10)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_app(scope, receive, send):
        started.set()
        await release.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = AIRequestBudgetMiddleware(slow_app)
    scope = {
        "type": "http",
        "method": "POST",
        "path": f"{settings.API_V1_STR}/ai/chat/stream",
        "headers": [],
        "client": ("127.0.0.1", 1234),
    }

    async def exercise() -> None:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        first = asyncio.create_task(middleware(scope, receive, send))
        await started.wait()
        second_messages: list[dict] = []

        async def second_send(message):
            second_messages.append(message)

        await middleware(scope, receive, second_send)
        assert second_messages[0]["status"] == 429
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        assert not middleware._active

    asyncio.run(exercise())


def test_ai_budget_identity_cache_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_BUDGET_MAX_IDENTITIES", 3)
    monkeypatch.setattr(settings, "AI_BUDGET_CLEANUP_INTERVAL_SECONDS", 10_000)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 100)

    async def app(_scope, _receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = AIRequestBudgetMiddleware(app)

    async def exercise() -> None:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(_message):
            return None

        for index in range(20):
            scope = {
                "type": "http",
                "method": "POST",
                "path": f"{settings.API_V1_STR}/ai/chat/stream",
                "headers": [],
                "client": (f"192.0.2.{index}", 1234),
            }
            await middleware(scope, receive, send)
        assert len(middleware._recent) <= 3
        assert len(middleware._last_seen) <= 3

    asyncio.run(exercise())


def test_ai_budget_rejects_new_identity_when_capacity_is_active(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "AI_BUDGET_MAX_IDENTITIES", 1)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 100)
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow_app(_scope, _receive, send):
        started.set()
        await release.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = AIRequestBudgetMiddleware(slow_app)

    async def exercise() -> None:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        base_scope = {
            "type": "http",
            "method": "POST",
            "path": f"{settings.API_V1_STR}/ai/chat/stream",
            "headers": [],
        }
        first = asyncio.create_task(
            middleware({**base_scope, "client": ("192.0.2.1", 1)}, receive, send)
        )
        await started.wait()
        second_sent: list[dict] = []

        async def second_send(message):
            second_sent.append(message)

        await middleware(
            {**base_scope, "client": ("192.0.2.2", 2)}, receive, second_send
        )
        assert second_sent[0]["status"] == 429
        assert len(middleware._recent) == 1
        release.set()
        await first

    asyncio.run(exercise())


def test_shallow_health_check_does_not_call_provider_probes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("shallow health check performed a network probe")

    monkeypatch.setattr(health, "_probe_mimo", forbidden)
    monkeypatch.setattr(health, "_probe_ollama", forbidden)
    monkeypatch.setattr(health, "_probe_openai_compatible", forbidden)
    started = time.perf_counter()
    result = health.healthz(deep=False)
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert result["status"] == "ok"
    expected_capability = (
        "degraded"
        if result["models"]["embedding_model"].get("degraded")
        else "available"
    )
    assert result["capability_status"] == expected_capability
    assert elapsed_ms < 50


def test_public_health_and_ready_ignore_deep_probe_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream_calls = 0

    def forbidden(*_args, **_kwargs):
        nonlocal upstream_calls
        upstream_calls += 1
        raise AssertionError("public health endpoint contacted an upstream provider")

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

    connection = MagicMock()
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection
    monkeypatch.setattr(health.engine, "connect", lambda: connection_context)
    monkeypatch.setattr(
        health,
        "schema_revision_status",
        lambda _connection: {
            "status": "current",
            "current": ["025"],
            "expected": ["025"],
        },
    )

    assert health.healthz(deep=True)["status"] == "ok"
    assert health.readyz(deep=True)["status"] == "ready"
    assert upstream_calls == 0


def test_capability_status_never_reports_unconfigured_models_as_available() -> None:
    assert health._capability_status(
        {
            "chat_model": {"configured": False, "reachable": False},
            "embedding_model": {"configured": False, "reachable": False},
        }
    ) == "unavailable"
    assert health._capability_status(
        {
            "chat_model": {"configured": True, "reachable": True},
            "embedding_model": {"configured": False, "reachable": False},
        }
    ) == "degraded"


def test_deep_health_marks_failed_vision_probe_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health,
        "_probe_mimo",
        lambda: {"configured": True, "reachable": True},
    )
    monkeypatch.setattr(
        health,
        "probe_multimodal_health",
        lambda timeout: {
            "configured": True,
            "probe_ok": False,
            "status": "error",
        },
    )
    monkeypatch.setattr(
        health,
        "_embedding_check",
        lambda deep: {"configured": True, "reachable": True},
    )

    models = health._build_model_checks(deep=True)

    assert models["multimodal_model"]["reachable"] is False
    assert health._capability_status(models) == "degraded"


def test_deep_health_marks_vision_probe_exception_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        health,
        "_probe_mimo",
        lambda: {"configured": True, "reachable": True},
    )

    def fail_probe(*_args, **_kwargs):
        raise RuntimeError("vision provider unavailable")

    monkeypatch.setattr(health, "probe_multimodal_health", fail_probe)
    monkeypatch.setattr(
        health,
        "_embedding_check",
        lambda deep: {"configured": True, "reachable": True},
    )

    models = health._build_model_checks(deep=True)

    assert models["multimodal_model"]["reachable"] is False
    assert models["multimodal_model"]["vision_probe"]["probe_ok"] is False
    assert health._capability_status(models) == "degraded"


def test_readyz_rejects_schema_drift_without_exposing_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = MagicMock()
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection
    monkeypatch.setattr(health.engine, "connect", lambda: connection_context)
    monkeypatch.setattr(
        health,
        "schema_revision_status",
        lambda _connection: {
            "status": "outdated",
            "current": ["009"],
            "expected": ["010"],
        },
    )

    with pytest.raises(Exception) as exc_info:
        health.readyz(deep=False)

    assert getattr(exc_info.value, "status_code", None) == 503
    assert getattr(exc_info.value, "detail", None) == "database schema is not current"


def test_competition_script_fails_closed_for_missing_inputs(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_competition.sh"
    syntax = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert syntax.returncode == 0

    missing_env = subprocess.run(
        ["bash", str(script), str(tmp_path / "missing.env")],
        capture_output=True,
        text=True,
    )
    assert missing_env.returncode == 2

    env_file = tmp_path / "competition.env"
    env_file.write_text("ENVIRONMENT=production\n", encoding="utf-8")
    env_file.chmod(0o600)
    process_env = os.environ.copy()
    process_env["PYTHON_BIN"] = str(tmp_path / "missing-python")
    missing_python = subprocess.run(
        ["bash", str(script), str(env_file)],
        capture_output=True,
        text=True,
        env=process_env,
    )
    assert missing_python.returncode == 3

    local_env = tmp_path / "local.env"
    local_env.write_text("ENVIRONMENT=local\n", encoding="utf-8")
    local_env.chmod(0o600)
    wrong_environment = subprocess.run(
        ["bash", str(script), str(local_env)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON_BIN": "/usr/bin/true"},
    )
    assert wrong_environment.returncode == 4
    assert "ENVIRONMENT=production" in wrong_environment.stderr

    weak_env = tmp_path / "weak.env"
    weak_env.write_text(
        "\n".join(
            [
                "ENVIRONMENT=production",
                "PROJECT_NAME=test",
                "SECRET_KEY=replace-with-secure-value",
                "POSTGRES_SERVER=localhost",
                "POSTGRES_USER=test",
                "POSTGRES_PASSWORD=short",
                "POSTGRES_DB=test",
                "FIRST_SUPERUSER=admin@example.com",
                "FIRST_SUPERUSER_PASSWORD=password123",
                "FRONTEND_HOST=https://app.example.com",
                "TRUSTED_HOSTS=api.example.com",
            ]
        ),
        encoding="utf-8",
    )
    weak_env.chmod(0o600)
    weak_credentials = subprocess.run(
        ["bash", str(script), str(weak_env)],
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHON_BIN": str(Path(__file__).resolve().parents[3] / ".venv" / "bin" / "python"),
        },
    )
    assert weak_credentials.returncode != 0
    assert "SECRET_KEY" in weak_credentials.stderr


def test_competition_script_rejects_readable_env_and_multiple_workers(
    tmp_path: Path,
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts" / "run_competition.sh"
    readable_env = tmp_path / "readable.env"
    readable_env.write_text("ENVIRONMENT=production\n", encoding="utf-8")
    readable_env.chmod(0o644)
    readable = subprocess.run(
        ["bash", str(script), str(readable_env)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON_BIN": "/usr/bin/true"},
    )
    assert readable.returncode == 5
    assert "chmod 600" in readable.stderr

    multi_worker_env = tmp_path / "multi-worker.env"
    multi_worker_env.write_text(
        "ENVIRONMENT=production\nBACKEND_WORKERS=2\n",
        encoding="utf-8",
    )
    multi_worker_env.chmod(0o600)
    multiple_workers = subprocess.run(
        ["bash", str(script), str(multi_worker_env)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHON_BIN": "/usr/bin/true"},
    )
    assert multiple_workers.returncode == 6
    assert "BACKEND_WORKERS=1" in multiple_workers.stderr
