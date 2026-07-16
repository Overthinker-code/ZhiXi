import asyncio
from io import BytesIO

import pytest
from fastapi import UploadFile
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import Response

from app.api.v1.endpoints import resource_workshop
from app.api.v1.endpoints.resource_workshop import (
    MAX_IMAGE_BASE64_CHARS,
    ImageAnalyzeRequest,
)
from app.core.auth_rate_limit import AuthAttemptLimiter
from app.core.config import Settings, settings
from app.core.upload_security import read_upload_limited
from app.schemas.token import PasswordResetRequest
from app.schemas.user import NewPassword, UserCreate, UserRegister, UserUpdate


_TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        PROJECT_NAME="test",
        ENVIRONMENT="production",
        SECRET_KEY="a-production-jwt-secret-with-more-than-32-characters",
        FRONTEND_HOST="https://app.example.com",
        TRUSTED_HOSTS=["api.example.com"],
        BACKEND_CORS_ORIGINS=["https://app.example.com"],
        POSTGRES_SERVER="localhost",
        POSTGRES_USER="test",
        POSTGRES_PASSWORD="a-secure-database-password",
        POSTGRES_DB="test",
        FIRST_SUPERUSER="admin@example.com",
        FIRST_SUPERUSER_PASSWORD="a-secure-admin-password",
        DEVELOPER_PANEL_ENABLED=False,
    )


def test_competition_security_defaults_use_short_token_and_25mb_upload_limit():
    configured = _settings()
    assert configured.ACCESS_TOKEN_EXPIRE_MINUTES == 60
    assert configured.MAX_UPLOAD_SIZE == 25 * 1024 * 1024
    assert configured.MAX_REQUEST_SIZE == 26 * 1024 * 1024


def test_image_analysis_accepts_image_data_but_rejects_remote_urls():
    request = ImageAnalyzeRequest(image_base64=_TINY_PNG)
    assert request.image_base64 == _TINY_PNG

    with pytest.raises(ValidationError, match="base64 image data"):
        ImageAnalyzeRequest(image_url="https://internal.example/metadata")


def test_image_url_compatibility_field_has_the_same_size_limit_as_base64():
    with pytest.raises(ValidationError, match="at most 10000000"):
        ImageAnalyzeRequest(image_url="A" * (MAX_IMAGE_BASE64_CHARS + 1))


def test_image_provider_failure_returns_stable_code_without_upstream_detail(monkeypatch):
    async def fail_provider(_request):
        raise RuntimeError("provider-secret-host:9443 failed")

    monkeypatch.setattr(resource_workshop, "_call_qwen3_vl", fail_provider)
    monkeypatch.setattr(resource_workshop, "_ocr_text_from_image_bytes", lambda _value: "")
    http_request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/resource-workshop/images/analyze",
            "headers": [(b"x-request-id", b"image-analysis-test")],
            "client": ("127.0.0.1", 1234),
        }
    )
    response = Response()

    result = asyncio.run(
        resource_workshop.analyze_image_problem(
            current_user=object(),
            request=ImageAnalyzeRequest(
                image_base64=_TINY_PNG,
                question_text="解释图片中的题目",
            ),
            http_request=http_request,
            response=response,
        )
    )

    assert result.status == "fallback"
    assert response.headers["x-request-id"] == "image-analysis-test"
    limitations = " ".join(result.limitations)
    assert "VISION_PROVIDER_UNAVAILABLE" in limitations
    assert "image-analysis-test" in limitations
    assert "provider-secret-host" not in limitations


def test_streamed_upload_rejects_the_first_byte_over_the_limit():
    upload = UploadFile(filename="lesson.txt", file=BytesIO(b"12345"))
    with pytest.raises(Exception) as exc_info:
        asyncio.run(read_upload_limited(upload, max_bytes=4))
    assert getattr(exc_info.value, "status_code", None) == 413


def test_auth_limiter_applies_both_account_and_client_dimensions():
    limiter = AuthAttemptLimiter()
    for index in range(settings.AUTH_RATE_LIMIT_ATTEMPTS):
        keys = limiter.keys(
            flow="login",
            client_host=f"192.0.2.{index}",
            account="same-account@example.com",
        )
        limiter.record(keys)
    account_from_new_ip = limiter.keys(
        flow="login",
        client_host="198.51.100.8",
        account="same-account@example.com",
    )
    assert limiter.retry_after(account_from_new_ip) is not None

    limiter.reset()
    for index in range(settings.AUTH_RATE_LIMIT_ATTEMPTS):
        keys = limiter.keys(
            flow="login",
            client_host="203.0.113.9",
            account=f"account-{index}@example.com",
        )
        limiter.record(keys)
    client_with_new_account = limiter.keys(
        flow="login",
        client_host="203.0.113.9",
        account="new-account@example.com",
    )
    assert limiter.retry_after(client_with_new_account) is not None


@pytest.mark.parametrize(
    "factory",
    [
        lambda password: UserCreate(email="student@example.com", password=password),
        lambda password: UserRegister(
            email="student@example.com", username="student", password=password
        ),
        lambda password: UserUpdate(password=password),
        lambda password: NewPassword(
            current_password="legacy-password", new_password=password
        ),
        lambda password: PasswordResetRequest(token="token", new_password=password),
    ],
)
def test_new_password_inputs_require_10_to_128_characters(factory):
    with pytest.raises(ValidationError):
        factory("short123")
    with pytest.raises(ValidationError):
        factory("x" * 129)
    assert factory("long-enough") is not None
