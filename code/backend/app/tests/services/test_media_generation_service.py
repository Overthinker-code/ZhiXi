from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4

import httpx
import pytest

from app.core.config import settings
from app.services.media_generation_service import (
    GeneratedMedia,
    MediaGenerationError,
    MediaGenerationService,
    is_seedance_credit_error,
)


class _Client:
    def __init__(self, responses: list[httpx.Response], calls: list[tuple[str, str, dict]]) -> None:
        self.responses = responses
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url: str, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url: str, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)

    @contextmanager
    def stream(self, method: str, url: str, **kwargs):
        self.calls.append((method, url, kwargs))
        yield self.responses.pop(0)


def _client_factory(responses, calls):
    return lambda **_kwargs: _Client(responses, calls)


def test_siliconflow_request_and_safe_download(monkeypatch, tmp_path: Path) -> None:
    responses = [
        httpx.Response(200, json={"images": [{"url": "https://cdn.example.test/image.png", "revised_prompt": "revised"}]}),
        httpx.Response(200, content=b"\x89PNG\r\n\x1a\nimage-data", headers={"content-type": "image/png"}),
    ]
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    monkeypatch.setattr(settings, "IMAGE_GENERATION_API_KEY", "test-key")
    monkeypatch.setattr(settings, "IMAGE_GENERATION_API_BASE", "https://api.example.test/v1")
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)

    media = service.generate_image("数据库关系模型")

    assert calls[0][1].endswith("/images/generations")
    assert calls[0][2]["json"] == {
        "model": settings.IMAGE_GENERATION_MODEL,
        "prompt": "数据库关系模型",
        "negative_prompt": settings.IMAGE_GENERATION_NEGATIVE_PROMPT,
        "image_size": settings.IMAGE_GENERATION_SIZE,
        "batch_size": 1,
    }
    assert media.path.read_bytes() == b"\x89PNG\r\n\x1a\nimage-data"
    assert media.provider == "siliconflow"
    assert media.revised_prompt == "revised"


def test_siliconflow_legacy_data_response_remains_compatible(monkeypatch, tmp_path: Path) -> None:
    responses = [
        httpx.Response(200, json={"data": [{"url": "https://cdn.example.test/legacy.png", "revised_prompt": "legacy"}]}),
        httpx.Response(200, content=b"\x89PNG\r\n\x1a\nlegacy", headers={"content-type": "image/png"}),
    ]
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    monkeypatch.setattr(settings, "IMAGE_GENERATION_API_KEY", "test-key")
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)

    media = service.generate_image("legacy")

    assert media.path.read_bytes() == b"\x89PNG\r\n\x1a\nlegacy"
    assert media.revised_prompt == "legacy"


def test_seedance_submit_poll_success_and_minimum_interval(monkeypatch, tmp_path: Path) -> None:
    responses = [
        httpx.Response(200, json={"data": {"task_id": "task-1"}}),
        httpx.Response(200, json={"status": "RUNNING"}),
        httpx.Response(200, json={"status": "SUCCEEDED", "data": {"url": "https://cdn.example.test/video.mp4"}}),
        httpx.Response(200, content=b"\x00\x00\x00\x18ftypisommp4-data", headers={"content-type": "video/mp4"}),
    ]
    calls: list[tuple[str, str, dict]] = []
    sleeps: list[float] = []
    statuses: list[str] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    monkeypatch.setattr(settings, "SEEDANCE_API_KEY", "test-key")
    service = MediaGenerationService(sleep=sleeps.append)
    service.staging_dir = tmp_path
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)

    media = service.generate_video("讲解 ER 模型", status_callback=statuses.append)

    assert calls[0][1].endswith("/v1/videos/generations")
    assert calls[0][2]["json"]["input"]["generation_type"] == "text-to-video"
    assert calls[1][1].endswith("/v1/tasks/task-1")
    assert sleeps == [10.0]
    assert statuses == ["submitted", "running", "succeeded"]
    assert media.path.read_bytes() == b"\x00\x00\x00\x18ftypisommp4-data"


@pytest.mark.parametrize(
    ("responses", "expected_code"),
    [
        ([httpx.Response(200, json={"data": {"task_id": "task-1"}}), httpx.Response(200, json={"status": "FAILED"})], "SEEDANCE_TASK_FAILED"),
    ],
)
def test_seedance_failure_is_not_reported_as_success(monkeypatch, tmp_path: Path, responses, expected_code: str) -> None:
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    monkeypatch.setattr(settings, "SEEDANCE_API_KEY", "test-key")
    service = MediaGenerationService(sleep=lambda _seconds: None)
    service.staging_dir = tmp_path
    with pytest.raises(MediaGenerationError, match="任务失败") as raised:
        service.generate_video("测试")
    assert raised.value.code == expected_code


def test_seedance_timeout_has_explicit_code(monkeypatch, tmp_path: Path) -> None:
    responses = [
        httpx.Response(200, json={"data": {"task_id": "task-1"}}),
        httpx.Response(200, json={"status": "RUNNING"}),
    ]
    calls: list[tuple[str, str, dict]] = []
    ticks = iter([0.0, 1.0, float(settings.SEEDANCE_TIMEOUT_SECONDS) + 1.0])
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    monkeypatch.setattr("app.services.media_generation_service.time.monotonic", lambda: next(ticks))
    monkeypatch.setattr(settings, "SEEDANCE_API_KEY", "test-key")
    service = MediaGenerationService(sleep=lambda _seconds: None)
    service.staging_dir = tmp_path
    with pytest.raises(MediaGenerationError) as raised:
        service.generate_video("测试")
    assert raised.value.code == "SEEDANCE_TIMEOUT"


def test_download_rejects_private_address_and_oversized_content(monkeypatch, tmp_path: Path) -> None:
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    with pytest.raises(MediaGenerationError) as private_error:
        service._download("https://127.0.0.1/private.png", allowed_types=("image/png",), max_bytes=20, timeout=1, suffix=".png")
    assert private_error.value.code == "UNSAFE_MEDIA_URL"

    with pytest.raises(MediaGenerationError) as credential_error:
        service._download(
            "https://student:secret@cdn.example.test/private.png",
            allowed_types=("image/png",),
            max_bytes=20,
            timeout=1,
            suffix=".png",
        )
    assert credential_error.value.code == "UNSAFE_MEDIA_URL"

    responses = [httpx.Response(200, content=b"\x89PNG\r\n\x1a\n" + b"x" * 21, headers={"content-type": "image/png"})]
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)
    with pytest.raises(MediaGenerationError) as size_error:
        service._download("https://cdn.example.test/large.png", allowed_types=("image/png",), max_bytes=20, timeout=1, suffix=".png")
    assert size_error.value.code == "MEDIA_TOO_LARGE"


def test_download_accepts_octet_stream_only_when_magic_is_supported(monkeypatch, tmp_path: Path) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"safe-image"
    responses = [
        httpx.Response(
            200,
            content=png,
            headers={"content-type": "application/octet-stream"},
        )
    ]
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)

    path, content_type = service._download(
        "https://cdn.example.test/image",
        allowed_types=("image/png",),
        max_bytes=1024,
        timeout=1,
        suffix=".png",
    )

    assert content_type == "image/png"
    assert path.suffix == ".png"
    assert path.read_bytes() == png


def test_download_revalidates_each_redirect_target(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str, dict]] = []
    responses = [httpx.Response(302, headers={"location": "https://127.0.0.1/private.png"})]
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory(responses, calls))
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    seen_hosts: list[str] = []

    def validate(url: str) -> None:
        seen_hosts.append(url)
        if "127.0.0.1" in url:
            raise MediaGenerationError("UNSAFE_MEDIA_URL", "private redirect")

    monkeypatch.setattr(service, "_validate_remote_url", validate)
    with pytest.raises(MediaGenerationError) as raised:
        service._download("https://cdn.example.test/original.png", allowed_types=("image/png",), max_bytes=20, timeout=1, suffix=".png")
    assert raised.value.code == "UNSAFE_MEDIA_URL"
    assert seen_hosts == ["https://cdn.example.test/original.png", "https://127.0.0.1/private.png"]


def test_download_streams_body_and_stops_at_limit_before_full_consumption(monkeypatch, tmp_path: Path) -> None:
    class StreamingResponse:
        status_code = 200
        headers = {"content-type": "image/png"}
        is_redirect = False
        is_error = False

        def __init__(self) -> None:
            self.chunks_seen = 0

        @property
        def content(self):  # pragma: no cover - must never be accessed by _download
            raise AssertionError("_download must not pre-buffer response.content")

        def iter_bytes(self):
            for chunk in (b"\x89PNG\r\n\x1a\n", b"x" * 32, b"unread"):
                self.chunks_seen += 1
                yield chunk

    response = StreamingResponse()
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory([response], calls))
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)
    with pytest.raises(MediaGenerationError) as raised:
        service._download("https://cdn.example.test/stream.png", allowed_types=("image/png",), max_bytes=20, timeout=1, suffix=".png")
    assert raised.value.code == "MEDIA_TOO_LARGE"
    assert response.chunks_seen == 2
    assert calls == [("GET", "https://cdn.example.test/stream.png", {})]


@pytest.mark.parametrize(
    ("content_type", "body"),
    [
        ("image/png", b"not-a-png"),
        ("image/jpeg", b"not-a-jpeg"),
        ("image/webp", b"RIFF\x00\x00\x00\x00NOPE"),
        ("video/mp4", b"not-an-mp4"),
    ],
)
def test_download_rejects_content_type_magic_mismatch(monkeypatch, tmp_path: Path, content_type: str, body: bytes) -> None:
    calls: list[tuple[str, str, dict]] = []
    monkeypatch.setattr("app.services.media_generation_service.httpx.Client", _client_factory([httpx.Response(200, content=body, headers={"content-type": content_type})], calls))
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    monkeypatch.setattr(service, "_is_public_host", lambda _host: True)
    with pytest.raises(MediaGenerationError) as raised:
        service._download("https://cdn.example.test/invalid", allowed_types=(content_type,), max_bytes=100, timeout=1, suffix=".bin")
    assert raised.value.code == "MEDIA_MAGIC_REJECTED"


def test_persist_resource_copies_then_atomically_replaces_target(monkeypatch, tmp_path: Path) -> None:
    class FakeSession:
        def add(self, _resource):
            return None

        def commit(self):
            return None

        def refresh(self, _resource):
            return None

        def rollback(self):
            return None

    upload_root = tmp_path / "uploads"
    source = tmp_path / "other-filesystem-simulated-source.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\nimage")
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_root))
    service = MediaGenerationService()
    persisted = service.persist_resource(
        FakeSession(),  # type: ignore[arg-type]
        owner_id=uuid4(),
        media=GeneratedMedia(path=source, content_type="image/png", provider="test"),
        title="asset",
        kind="image",
        subject="AI生成",
        knowledge_point="stack",
        course_id=None,
    )
    target = upload_root / "resources" / persisted.resource.file_name
    assert target.read_bytes() == b"\x89PNG\r\n\x1a\nimage"
    assert not source.exists()
    assert not list((upload_root / "resources").glob("*.part"))


def test_deterministic_stack_fallback_produces_verified_private_mp4(tmp_path: Path) -> None:
    service = MediaGenerationService()
    service.staging_dir = tmp_path
    media = service.generate_deterministic_stack_fallback()
    try:
        assert media.provider == "deterministic_stack_fallback"
        assert media.content_type == "video/mp4"
        assert media.path.is_file()
        service._verify_fallback_video(media.path)
    finally:
        media.path.unlink(missing_ok=True)
    assert not list(tmp_path.glob("stack-frames-*"))


def test_only_seedance_submit_credit_failure_is_eligible_for_fallback() -> None:
    assert is_seedance_credit_error(MediaGenerationError("SEEDANCE_INSUFFICIENT_CREDITS", "额度不足"))
    assert is_seedance_credit_error(MediaGenerationError("SEEDANCE_SUBMIT_FAILED", "HTTP 402: insufficient_credits"))
    assert not is_seedance_credit_error(MediaGenerationError("SEEDANCE_POLL_FAILED", "HTTP 402: insufficient_credits"))
    assert not is_seedance_credit_error(MediaGenerationError("SEEDANCE_SUBMIT_FAILED", "HTTP 500: upstream unavailable"))
