"""Remote media generation with safe, private resource persistence.

Provider URLs are treated as untrusted and are never returned as the student
preview URL.  They are downloaded immediately, validated, and then represented
by the existing authenticated Resource endpoints.
"""
from __future__ import annotations

import ipaddress
import json
import logging
import mimetypes
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse
from uuid import UUID, uuid4

import httpx
from sqlmodel import Session

from app.core.config import settings
from app.models import Resource


logger = logging.getLogger(__name__)


class MediaGenerationError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def is_seedance_credit_error(error: MediaGenerationError) -> bool:
    """Only a rejected Seedance submission due to credits permits local fallback."""
    if error.code == "SEEDANCE_INSUFFICIENT_CREDITS":
        return True
    if error.code != "SEEDANCE_SUBMIT_FAILED":
        return False
    text = error.message.lower()
    return any(marker in text for marker in ("insufficient_credits", "insufficient credits", "credit", "余额不足"))


@dataclass
class GeneratedMedia:
    path: Path
    content_type: str
    provider: str
    revised_prompt: str | None = None


@dataclass
class PersistedMedia:
    resource: Resource
    preview_url: str
    download_url: str


class MediaGenerationService:
    """SiliconFlow image and Seedance video client with SSRF-safe downloads."""

    def __init__(self, *, sleep: Callable[[float], None] = time.sleep) -> None:
        self._sleep = sleep
        self.staging_dir = Path(settings.UPLOAD_DIR) / "resources" / ".media-staging"

    def image_configured(self) -> bool:
        return bool(settings.IMAGE_GENERATION_API_BASE and settings.IMAGE_GENERATION_API_KEY and settings.IMAGE_GENERATION_MODEL)

    def seedance_configured(self) -> bool:
        return bool(settings.SEEDANCE_API_BASE and settings.SEEDANCE_API_KEY and settings.SEEDANCE_MODEL)

    @staticmethod
    def _headers(key: str | None) -> dict[str, str]:
        if not key:
            raise MediaGenerationError("MEDIA_PROVIDER_NOT_CONFIGURED", "媒体生成服务未配置 API Key")
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    @staticmethod
    def _error(code: str, response: httpx.Response) -> MediaGenerationError:
        try:
            detail = response.json()
        except Exception:
            detail = response.text[:500]
        detail_text = str(detail)[:500]
        logger.warning(
            "media provider request failed code=%s status=%s detail=%s",
            code,
            response.status_code,
            detail_text,
        )
        if code == "SEEDANCE_SUBMIT_FAILED" and any(
            marker in detail_text.lower()
            for marker in ("insufficient_credits", "insufficient credits", "credit", "余额不足")
        ):
            return MediaGenerationError(
                "SEEDANCE_INSUFFICIENT_CREDITS",
                "云端视频生成额度不足，已准备切换本地动画引擎",
            )
        return MediaGenerationError(code, f"上游媒体服务暂时不可用（HTTP {response.status_code}）")

    @staticmethod
    def _first_url(payload: Any) -> str:
        if isinstance(payload, dict):
            for key in ("url", "video_url", "videoUrl", "download_url", "downloadUrl", "result_url", "resultUrl"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for key in ("data", "output", "result", "video", "task_result", "taskResult"):
                found = MediaGenerationService._first_url(payload.get(key))
                if found:
                    return found
            for key in ("images", "videos", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    for item in value:
                        found = MediaGenerationService._first_url(item)
                        if found:
                            return found
        if isinstance(payload, list):
            for item in payload:
                found = MediaGenerationService._first_url(item)
                if found:
                    return found
        return ""

    @staticmethod
    def _task_id(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        for key in ("task_id", "taskId", "id"):
            value = payload.get(key)
            if value:
                return str(value)
        for key in ("data", "output", "task"):
            value = MediaGenerationService._task_id(payload.get(key))
            if value:
                return value
        return ""

    @staticmethod
    def _task_status(payload: Any) -> str:
        if not isinstance(payload, dict):
            return ""
        for key in ("status", "task_status", "taskStatus"):
            value = payload.get(key)
            if value:
                return str(value).upper()
        for key in ("data", "output", "task"):
            value = MediaGenerationService._task_status(payload.get(key))
            if value:
                return value
        return ""

    @staticmethod
    def _is_public_host(host: str) -> bool:
        normalized = host.strip().strip("[]").lower()
        if not normalized or normalized == "localhost" or normalized.endswith(".localhost"):
            return False
        try:
            return ipaddress.ip_address(normalized).is_global
        except ValueError:
            pass
        try:
            addresses = socket.getaddrinfo(normalized, None, type=socket.SOCK_STREAM)
        except socket.gaierror:
            return False
        return bool(addresses) and all(ipaddress.ip_address(item[4][0]).is_global for item in addresses)

    def _validate_remote_url(self, url: str) -> None:
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or not self._is_public_host(parsed.hostname)
        ):
            raise MediaGenerationError("UNSAFE_MEDIA_URL", "媒体下载地址必须是可公开访问的 HTTPS 地址")

    @staticmethod
    def _detect_magic(header: bytes) -> str | None:
        """Detect the supported media type without trusting CDN headers."""
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
        if len(header) >= 8 and header[4:8] == b"ftyp":
            return "video/mp4"
        return None

    def _download(
        self,
        url: str,
        *,
        allowed_types: tuple[str, ...],
        max_bytes: int,
        timeout: float,
        suffix: str,
    ) -> tuple[Path, str]:
        current = url
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        for redirect_count in range(4):
            self._validate_remote_url(current)
            with httpx.Client(
                timeout=timeout,
                follow_redirects=False,
                trust_env=settings.MEDIA_HTTP_TRUST_ENV,
            ) as client:
                # ``stream`` is essential here: provider assets can be much
                # larger than the accepted limit, so never call ``get`` first.
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location or redirect_count == 3:
                            raise MediaGenerationError("MEDIA_REDIRECT_REJECTED", "媒体下载重定向不被允许")
                        current = urljoin(current, location)
                        continue
                    if response.is_error:
                        raise MediaGenerationError("MEDIA_DOWNLOAD_FAILED", f"媒体下载返回 HTTP {response.status_code}")
                    declared_content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                    if declared_content_type not in (*allowed_types, "", "application/octet-stream"):
                        raise MediaGenerationError("MEDIA_CONTENT_TYPE_REJECTED", "媒体下载的 Content-Type 不被允许")
                    declared_size = response.headers.get("content-length")
                    if declared_size and declared_size.isdigit() and int(declared_size) > max_bytes:
                        raise MediaGenerationError("MEDIA_TOO_LARGE", "媒体文件超过大小限制")
                    fd, temporary_name = tempfile.mkstemp(prefix="download-", suffix=".part", dir=self.staging_dir)
                    written = 0
                    header = bytearray()
                    try:
                        with os.fdopen(fd, "wb") as handle:
                            for chunk in response.iter_bytes():
                                written += len(chunk)
                                if written > max_bytes:
                                    raise MediaGenerationError("MEDIA_TOO_LARGE", "媒体文件超过大小限制")
                                if len(header) < 16:
                                    header.extend(chunk[: 16 - len(header)])
                                handle.write(chunk)
                            handle.flush()
                            os.fsync(handle.fileno())
                        detected_content_type = self._detect_magic(bytes(header))
                        if detected_content_type not in allowed_types:
                            raise MediaGenerationError("MEDIA_MAGIC_REJECTED", "媒体文件内容与 Content-Type 不匹配")
                        if declared_content_type in allowed_types and declared_content_type != detected_content_type:
                            raise MediaGenerationError("MEDIA_MAGIC_REJECTED", "媒体文件内容与 Content-Type 不匹配")
                        target_suffix = mimetypes.guess_extension(detected_content_type) or suffix
                        if target_suffix == ".jpe":
                            target_suffix = ".jpg"
                        target = self.staging_dir / f"{uuid4().hex}{target_suffix}"
                        os.replace(temporary_name, target)
                        return target, detected_content_type
                    except Exception:
                        Path(temporary_name).unlink(missing_ok=True)
                        raise
        raise MediaGenerationError("MEDIA_REDIRECT_REJECTED", "媒体下载重定向不被允许")

    def generate_image(self, prompt: str) -> GeneratedMedia:
        if not self.image_configured():
            raise MediaGenerationError("IMAGE_GENERATION_NOT_CONFIGURED", "SiliconFlow 图片生成未配置")
        payload = {
            "model": settings.IMAGE_GENERATION_MODEL,
            "prompt": prompt,
            "negative_prompt": settings.IMAGE_GENERATION_NEGATIVE_PROMPT,
            "image_size": settings.IMAGE_GENERATION_SIZE,
            "batch_size": 1,
        }
        with httpx.Client(
            timeout=settings.IMAGE_GENERATION_TIMEOUT_SECONDS,
            trust_env=settings.MEDIA_HTTP_TRUST_ENV,
        ) as client:
            response = client.post(f"{settings.IMAGE_GENERATION_API_BASE.rstrip('/')}/images/generations", headers=self._headers(settings.IMAGE_GENERATION_API_KEY), json=payload)
        if response.is_error:
            raise self._error("IMAGE_GENERATION_UPSTREAM_FAILED", response)
        data = response.json()
        url = self._first_url(data)
        if not url:
            raise MediaGenerationError("IMAGE_GENERATION_INVALID_RESPONSE", "SiliconFlow 未返回图片地址")
        path, content_type = self._download(url, allowed_types=("image/jpeg", "image/png", "image/webp"), max_bytes=settings.MEDIA_IMAGE_MAX_BYTES, timeout=settings.IMAGE_GENERATION_TIMEOUT_SECONDS, suffix=".png")
        revised = ""
        if isinstance(data, dict):
            for collection_key in ("images", "data"):
                collection = data.get(collection_key)
                if isinstance(collection, list) and collection and isinstance(collection[0], dict):
                    revised = str(collection[0].get("revised_prompt") or "")
                    if revised:
                        break
        return GeneratedMedia(path=path, content_type=content_type, provider="siliconflow", revised_prompt=revised or None)

    def generate_video(
        self,
        prompt: str,
        *,
        status_callback: Callable[[str], None] | None = None,
    ) -> GeneratedMedia:
        if not self.seedance_configured():
            raise MediaGenerationError("SEEDANCE_NOT_CONFIGURED", "Seedance 视频生成未配置")
        payload = {"model": settings.SEEDANCE_MODEL, "input": {"prompt": prompt, "generation_type": "text-to-video", "duration": settings.SEEDANCE_DEFAULT_DURATION, "aspect_ratio": settings.SEEDANCE_DEFAULT_ASPECT_RATIO, "resolution": settings.SEEDANCE_DEFAULT_RESOLUTION, "generate_audio": True}}
        headers = self._headers(settings.SEEDANCE_API_KEY)
        base = settings.SEEDANCE_API_BASE.rstrip("/")
        # This provider is currently invoked from an SSE request. Always leave
        # a 30-second margin for secure download, persistence and final events,
        # even when a deployment overrides the provider timeout to a larger
        # value. A future queue worker can remove this cap.
        request_timeout = max(
            30.0,
            min(
                float(settings.SEEDANCE_TIMEOUT_SECONDS),
                float(settings.AI_SSE_TIMEOUT_SECONDS) - 30.0,
            ),
        )
        with httpx.Client(
            timeout=request_timeout,
            trust_env=settings.MEDIA_HTTP_TRUST_ENV,
        ) as client:
            created = client.post(f"{base}/v1/videos/generations", headers=headers, json=payload)
        if created.is_error:
            raise self._error("SEEDANCE_SUBMIT_FAILED", created)
        task_id = self._task_id(created.json())
        if not task_id:
            raise MediaGenerationError("SEEDANCE_INVALID_RESPONSE", "Seedance 未返回任务 ID")
        if status_callback:
            status_callback("submitted")
        deadline = time.monotonic() + request_timeout
        while time.monotonic() < deadline:
            with httpx.Client(
                timeout=request_timeout,
                trust_env=settings.MEDIA_HTTP_TRUST_ENV,
            ) as client:
                polled = client.get(f"{base}/v1/tasks/{task_id}", headers=headers)
            if polled.is_error:
                raise self._error("SEEDANCE_POLL_FAILED", polled)
            result = polled.json()
            status = self._task_status(result)
            if status_callback:
                status_callback(status.lower() or "polling")
            url = self._first_url(result)
            if status in {"SUCCEEDED", "SUCCESS", "COMPLETED", "DONE"}:
                if not url:
                    raise MediaGenerationError("SEEDANCE_INVALID_RESPONSE", "Seedance 成功任务未返回视频地址")
                path, content_type = self._download(url, allowed_types=("video/mp4",), max_bytes=settings.MEDIA_VIDEO_MAX_BYTES, timeout=request_timeout, suffix=".mp4")
                return GeneratedMedia(path=path, content_type=content_type, provider="seedance")
            if status in {"FAILED", "FAILURE", "CANCELED", "CANCELLED", "ERROR"}:
                raise MediaGenerationError("SEEDANCE_TASK_FAILED", f"Seedance 任务失败: {status}")
            self._sleep(max(10.0, settings.SEEDANCE_POLL_INTERVAL_SECONDS))
        raise MediaGenerationError("SEEDANCE_TIMEOUT", "Seedance 视频生成超时")

    def _verify_fallback_video(self, path: Path) -> None:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries",
                    "stream=codec_name,width,height:format=duration",
                    "-of", "json", str(path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            metadata = json.loads(result.stdout)
            stream = next((item for item in metadata.get("streams", []) if isinstance(item, dict)), {})
            duration = float((metadata.get("format") or {}).get("duration") or 0)
        except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
            raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_FAILED", f"本地 MP4 校验失败: {exc}") from exc
        if (
            stream.get("codec_name") != "h264"
            or stream.get("width") != 1280
            or stream.get("height") != 720
            or not 4.8 <= duration <= 5.2
        ):
            raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_FAILED", "本地 MP4 未满足 5 秒、1280x720、H.264 验收")
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_FAILED", "本地 MP4 视觉校验需要 OpenCV") from exc

        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_FAILED", "本地 MP4 无法解码用于视觉校验")
        # These coordinates are deliberately sampled well inside each block,
        # not on antialiased borders. A/B must never disappear; C moves down,
        # remains on stack, then moves upward.
        expected_c_y = {0: 95, 30: 245, 60: 316, 90: 316, 120: 230, 149: 106}
        expected = {
            "A": np.array([248, 189, 56]),  # BGR for #38BDF8
            "B": np.array([250, 139, 167]),  # BGR for #A78BFA
            "C": np.array([36, 191, 251]),   # BGR for #FBBF24
        }
        try:
            for frame_number, c_y in expected_c_y.items():
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ok, frame = capture.read()
                if not ok:
                    raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_FAILED", f"本地 MP4 缺少第 {frame_number} 帧")
                probes = {
                    # Sample away from the centered A/B/C glyphs.
                    "A": frame[561, 550],
                    "B": frame[463, 550],
                    "C": frame[int(c_y + 49), 550],
                }
                for label, pixel in probes.items():
                    if float(np.linalg.norm(pixel.astype(float) - expected[label])) > 95:
                        raise MediaGenerationError(
                            "DETERMINISTIC_STACK_FALLBACK_FAILED",
                            f"本地 MP4 第 {frame_number} 帧的 {label} 色块视觉校验失败",
                        )
        finally:
            capture.release()

    def generate_deterministic_stack_fallback(self) -> GeneratedMedia:
        """Render a deterministic 5s stack push/pop clip without a cloud claim."""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as exc:
            raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_UNAVAILABLE", "本地栈动画需要 Pillow") from exc

        self.staging_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.staging_dir / f"{uuid4().hex}.mp4"
        temporary_path = self.staging_dir / f".{uuid4().hex}.part.mp4"
        try:
            colors = {"A": "#38BDF8", "B": "#A78BFA", "C": "#FBBF24"}
            base_y, block_width, block_height, x = 610, 260, 98, 510
            try:
                label_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 42)
            except OSError:
                label_font = ImageFont.load_default()
            with tempfile.TemporaryDirectory(prefix="stack-frames-", dir=self.staging_dir) as frame_directory:
                frame_root = Path(frame_directory)
                for frame in range(150):
                    canvas = Image.new("RGB", (1280, 720), "#F8FAFC")
                    draw = ImageDraw.Draw(canvas)
                    draw.rounded_rectangle((x - 24, 270, x + block_width + 24, base_y + 18), radius=18, outline="#334155", width=6)
                    draw.line((x - 24, base_y + 18, x + block_width + 24, base_y + 18), fill="#334155", width=8)
                    visible = [("A", base_y - block_height), ("B", base_y - 2 * block_height)]
                    if frame < 45:
                        progress = frame / 44
                        c_y = 95 + (base_y - 3 * block_height - 95) * progress
                        draw.line((x + block_width / 2, 62, x + block_width / 2, c_y - 20), fill="#F59E0B", width=9)
                        draw.polygon([(x + block_width / 2, c_y - 4), (x + block_width / 2 - 15, c_y - 28), (x + block_width / 2 + 15, c_y - 28)], fill="#F59E0B")
                        visible.append(("C", c_y))
                    elif frame < 100:
                        visible.append(("C", base_y - 3 * block_height))
                    else:
                        progress = (frame - 100) / 49
                        c_y = base_y - 3 * block_height - 210 * progress
                        draw.line((x + block_width / 2, c_y + block_height + 20, x + block_width / 2, c_y + block_height + 82), fill="#F59E0B", width=9)
                        draw.polygon([(x + block_width / 2, c_y + block_height + 4), (x + block_width / 2 - 15, c_y + block_height + 28), (x + block_width / 2 + 15, c_y + block_height + 28)], fill="#F59E0B")
                        visible.append(("C", c_y))
                    for label, y in visible:
                        draw.rounded_rectangle((x, y, x + block_width, y + block_height), radius=14, fill=colors[label], outline="#0F172A", width=4)
                        bounds = draw.textbbox((0, 0), label, font=label_font)
                        text_width = bounds[2] - bounds[0]
                        text_height = bounds[3] - bounds[1]
                        draw.text(
                            (x + (block_width - text_width) / 2, y + (block_height - text_height) / 2 - bounds[1]),
                            label,
                            fill="#0F172A",
                            font=label_font,
                        )
                    canvas.save(frame_root / f"frame-{frame:03d}.png", format="PNG")
                result = subprocess.run(
                    [
                        "ffmpeg", "-y", "-loglevel", "error", "-framerate", "30", "-start_number", "0",
                        "-i", str(frame_root / "frame-%03d.png"), "-frames:v", "150", "-an",
                        "-c:v", "h264_videotoolbox", "-b:v", "2M", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(temporary_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if result.returncode != 0:
                    raise RuntimeError((result.stderr or result.stdout)[-600:])
            self._verify_fallback_video(temporary_path)
            os.replace(temporary_path, final_path)
            return GeneratedMedia(path=final_path, content_type="video/mp4", provider="deterministic_stack_fallback")
        except MediaGenerationError:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise MediaGenerationError("DETERMINISTIC_STACK_FALLBACK_FAILED", f"本地栈动画渲染失败: {exc}") from exc

    def persist_resource(
        self, db: Session, *, owner_id: UUID, media: GeneratedMedia, title: str,
        kind: str, subject: str, knowledge_point: str | None, course_id: UUID | None,
    ) -> PersistedMedia:
        root = Path(settings.UPLOAD_DIR) / "resources"
        root.mkdir(parents=True, exist_ok=True)
        suffix = media.path.suffix or mimetypes.guess_extension(media.content_type) or ""
        file_name = f"{uuid4().hex}{suffix}"
        target = root / file_name
        resource = Resource(title=title[:255], type=kind, subject=subject[:80] or "AI生成", file_name=file_name, file_path=f"resources/{file_name}", file_size=media.path.stat().st_size, content_type=media.content_type, course_id=course_id, uploader_id=owner_id, knowledge_point=(knowledge_point or "")[:160] or None, source=media.provider, content={"provider": media.provider, "generation_type": kind})
        temporary_target = root / f".{file_name}.{uuid4().hex}.part"
        try:
            # Always write the final temporary file under ``root`` before the
            # atomic rename. This remains safe when a legacy renderer produced
            # its source on a different filesystem.
            with media.path.open("rb") as source, temporary_target.open("xb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temporary_target, target)
        except Exception:
            temporary_target.unlink(missing_ok=True)
            raise
        try:
            db.add(resource)
            db.commit()
            db.refresh(resource)
        except Exception:
            db.rollback()
            target.unlink(missing_ok=True)
            raise
        media.path.unlink(missing_ok=True)
        base = settings.API_V1_STR
        return PersistedMedia(resource=resource, preview_url=f"{base}/education/resources/{resource.id}/preview", download_url=f"{base}/education/resources/{resource.id}/download")


media_generation_service = MediaGenerationService()
