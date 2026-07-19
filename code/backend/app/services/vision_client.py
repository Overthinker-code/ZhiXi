from __future__ import annotations

import base64
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Literal

import httpx
from PIL import Image

from app.core.config import settings
from app.services.model_aliases import is_local_ollama_compatible, resolve_model_name_for_base_url
from app.services.vision_response import (
    extract_openai_compatible_content,
    summarize_vision_message_fields,
)

VisionStatus = Literal["ok", "empty", "error", "ocr_fallback", "unconfigured"]

TINY_PROBE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@dataclass
class VisionCallResult:
    text: str = ""
    status: VisionStatus = "empty"
    source: str = ""
    error: str = ""
    model: str = ""
    field_summary: dict[str, Any] = field(default_factory=dict)


def normalize_image_ref(image_ref: str) -> str:
    ref = (image_ref or "").strip()
    if not ref:
        return ref
    if ref.startswith("data:"):
        return _ensure_min_image_size(ref)
    return _ensure_min_image_size(f"data:image/png;base64,{ref}")


def _ensure_min_image_size(image_ref: str, min_size: int = 64) -> str:
    """Qwen3-VL via Ollama rejects 1x1 images; upscale tiny probes/uploads."""
    image_bytes = decode_image_bytes(image_ref)
    if not image_bytes:
        return image_ref
    try:
        image = Image.open(BytesIO(image_bytes))
        width, height = image.size
        if width >= min_size and height >= min_size:
            return image_ref
        scale = max(min_size / max(width, 1), min_size / max(height, 1))
        new_size = (max(int(width * scale), min_size), max(int(height * scale), min_size))
        resized = image.convert("RGB").resize(new_size)
        buf = BytesIO()
        resized.save(buf, format="PNG")
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return image_ref


def decode_image_bytes(image_ref: str | None) -> bytes | None:
    if not image_ref:
        return None
    raw = image_ref
    if "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        return base64.b64decode(raw)
    except Exception:
        return None


def ocr_text_from_image_bytes(image_bytes: bytes | None) -> str:
    if not image_bytes:
        return ""
    tesseract_bin = shutil.which("tesseract")
    if not tesseract_bin:
        return ""
    temp_path = ""
    try:
        image = Image.open(BytesIO(image_bytes)).convert("L")
        image = image.resize((max(image.width * 2, 1), max(image.height * 2, 1)))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = tmp.name
            image.save(temp_path, format="PNG")
        result = subprocess.run(
            [tesseract_bin, temp_path, "stdout", "-l", "eng+chi_sim"],
            check=False,
            capture_output=True,
            text=True,
            timeout=12,
        )
        text = (result.stdout or "").strip()
        return re.sub(r"\s+", " ", text)
    except Exception:
        return ""
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass


def _multimodal_models() -> list[str]:
    base_url = _multimodal_api_base() or ""
    models: list[str] = []
    primary = (
        settings.MIMO_MULTIMODAL_MODEL
        if settings.MULTIMODAL_PROVIDER.lower() == "mimo"
        else settings.MULTIMODAL_MODEL
    )
    for candidate in (primary, settings.MULTIMODAL_FALLBACK_MODEL):
        resolved = resolve_model_name_for_base_url(candidate, base_url)
        if resolved and resolved not in models:
            models.append(resolved)
    return models


def _multimodal_api_base() -> str | None:
    if settings.MULTIMODAL_PROVIDER.lower() == "mimo":
        return settings.MULTIMODAL_API_BASE or settings.MIMO_API_BASE
    return settings.MULTIMODAL_API_BASE


def _multimodal_api_key() -> str | None:
    if settings.MULTIMODAL_PROVIDER.lower() == "mimo":
        return settings.MULTIMODAL_API_KEY or settings.MIMO_API_KEY
    if settings.MULTIMODAL_PROVIDER.lower() in {"qwen", "dashscope", "bailian"}:
        return settings.DASHSCOPE_API_KEY or settings.MULTIMODAL_API_KEY
    return settings.MULTIMODAL_API_KEY


def vision_request_payload(model: str, prompt: str, image_ref: str) -> dict[str, Any]:
    return _vision_request_payload(model, prompt, image_ref)


def _vision_request_payload(model: str, prompt: str, image_ref: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_ref}},
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 900,
    }
    return payload


def call_vision_model(
    image_ref: str,
    prompt: str,
    *,
    timeout: float | None = None,
) -> VisionCallResult:
    api_base = _multimodal_api_base()
    if not api_base:
        return VisionCallResult(status="unconfigured", error="MULTIMODAL_API_BASE not set")

    normalized_ref = normalize_image_ref(image_ref)
    models = _multimodal_models()
    if not models:
        return VisionCallResult(status="error", error="no multimodal model configured")

    last_error = ""
    last_fields: dict[str, Any] = {}
    timeout_seconds = float(timeout or settings.MULTIMODAL_TIMEOUT_SECONDS)
    headers = {
        "Authorization": f"Bearer {_multimodal_api_key() or 'local-placeholder'}"
    }
    if settings.MULTIMODAL_PROVIDER.lower() == "mimo":
        headers["api-key"] = _multimodal_api_key() or "local-placeholder"
    base = api_base.rstrip("/")
    use_think_flag = is_local_ollama_compatible(api_base)

    with httpx.Client(timeout=timeout_seconds) as client:
        for model in models:
            for with_think in ([True, False] if use_think_flag else [False]):
                payload = _vision_request_payload(model, prompt, normalized_ref)
                if settings.MULTIMODAL_PROVIDER.lower() == "mimo":
                    payload["thinking"] = {"type": "disabled"}
                if use_think_flag:
                    if with_think:
                        payload["think"] = False
                    else:
                        payload.pop("think", None)
                try:
                    resp = client.post(
                        f"{base}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    try:
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        body = (resp.text or "").strip()
                        body = re.sub(r"\s+", " ", body)
                        last_error = (
                            f"{model} request failed with HTTP {resp.status_code}: "
                            f"{body[:180] or exc.response.reason_phrase}"
                        )
                        if resp.status_code == 403:
                            last_error += (
                                "；403 通常表示当前 API Key 无权访问该模型、模型名不可用，"
                                "或账户未开通对应的视觉模型权限"
                            )
                        break
                    data = resp.json()
                    message = data.get("choices", [{}])[0].get("message", {})
                    if not isinstance(message, dict):
                        message = {}
                    text = extract_openai_compatible_content(message)
                    last_fields = summarize_vision_message_fields(message)
                    if text:
                        return VisionCallResult(
                            text=text,
                            status="ok",
                            source="multimodal",
                            model=model,
                            field_summary=last_fields,
                        )
                    last_error = f"{model} returned empty content"
                except Exception as exc:
                    last_error = str(exc)
                    if use_think_flag and with_think:
                        continue
                    break

    return VisionCallResult(
        status="empty" if not last_error.startswith("http") else "error",
        error=last_error[:240],
        field_summary=last_fields,
    )


def probe_multimodal_health(*, timeout: float = 45.0) -> dict[str, Any]:
    """Run a tiny vision inference probe (not just GET /models)."""
    if not _multimodal_api_base():
        return {"configured": False, "probe_ok": False, "detail": "not configured"}
    image_ref = normalize_image_ref(TINY_PROBE_PNG_B64)
    result = call_vision_model(
        image_ref,
        "Describe this image in one short Chinese sentence.",
        timeout=timeout,
    )
    out: dict[str, Any] = {
        "configured": True,
        "probe_ok": result.status == "ok",
        "status": result.status,
        "model": result.model,
        "field_summary": result.field_summary,
    }
    if result.error:
        out["detail"] = result.error
    if result.text:
        out["sample"] = result.text[:120]
    return out


def build_chat_image_context(
    images: list[str],
    *,
    user_hint: str = "",
) -> tuple[str, VisionCallResult]:
    cleaned = [img for img in images if img]
    if not cleaned:
        return "", VisionCallResult(status="empty")

    if not _multimodal_api_base():
        return (
            f"【图片上下文】学生上传了 {len(cleaned)} 张图片。当前后端尚未配置视觉模型服务，"
            "请结合学生补充文字进行讲解，并明确提示图片细节需要学生确认。",
            VisionCallResult(status="unconfigured"),
        )

    prompt = (
        "你是本地视觉题目识别助手。请识别图片中的题干、图表、选项、公式和已知条件；"
        "只输出中文要点，不要编造看不清的内容。"
    )
    if user_hint.strip():
        prompt += f"\n学生补充说明：{user_hint.strip()[:400]}"

    result = call_vision_model(cleaned[0], prompt)
    if result.status == "ok" and result.text:
        return f"【视觉模型识别结果】\n{result.text[:2500]}", result

    image_bytes = decode_image_bytes(cleaned[0])
    ocr_text = ocr_text_from_image_bytes(image_bytes)
    if ocr_text:
        ocr_result = VisionCallResult(
            text=ocr_text,
            status="ocr_fallback",
            source="tesseract",
            error=result.error,
            field_summary=result.field_summary,
        )
        return (
            f"【图片 OCR 识别结果】\n{ocr_text[:2500]}\n"
            "（视觉模型未返回稳定结果，已使用 OCR 作为补充证据。）",
            ocr_result,
        )

    if result.error:
        return (
            f"【图片上下文】学生上传了 {len(cleaned)} 张图片，但视觉模型调用失败：{result.error}。"
            "请基于学生补充文字继续回答，并明确说明图片细节未能稳定识别。",
            VisionCallResult(status="error", error=result.error, field_summary=result.field_summary),
        )

    return (
        "【图片上下文】已收到图片，但视觉模型未返回有效内容。请要求学生补充题干文字。",
        VisionCallResult(status="empty", field_summary=result.field_summary, error=result.error),
    )
