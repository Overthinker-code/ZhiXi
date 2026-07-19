from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str | None = None
    image_size: str | None = None
    batch_size: int = Field(default=1, ge=1, le=4)
    num_inference_steps: int | None = Field(default=None, ge=1, le=100)
    guidance_scale: float | None = Field(default=None, ge=0, le=20)
    seed: int | None = None
    prompt_enhancement: bool = True


class GeneratedImage(BaseModel):
    url: str
    local_url: str | None = None
    file_name: str | None = None
    revised_prompt: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SiliconFlowImageService:
    def __init__(self) -> None:
        self.api_base = settings.IMAGE_GENERATION_API_BASE.rstrip("/")
        self.api_key = settings.IMAGE_GENERATION_API_KEY
        self.timeout = float(settings.IMAGE_GENERATION_TIMEOUT_SECONDS)
        self.output_dir = Path(settings.BASE_PATH) / "uploads" / "generated_images"
        self.public_prefix = f"{settings.API_V1_STR}/ai/generated-images"

    def configured(self) -> bool:
        return bool(self.api_base and self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("IMAGE_GENERATION_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _raise_api_error(exc: httpx.HTTPStatusError) -> None:
        response = exc.response
        try:
            detail: Any = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"SiliconFlow image API error {response.status_code}: {detail}") from exc

    def build_payload(self, request: ImageGenerationRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": request.model or settings.IMAGE_GENERATION_MODEL,
            "prompt": request.prompt,
            "image_size": request.image_size or settings.IMAGE_GENERATION_SIZE,
            "batch_size": request.batch_size,
            "prompt_enhancement": request.prompt_enhancement,
        }
        if request.num_inference_steps is not None:
            payload["num_inference_steps"] = request.num_inference_steps
        if request.guidance_scale is not None:
            payload["guidance_scale"] = request.guidance_scale
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    def generate(self, request: ImageGenerationRequest) -> dict[str, Any]:
        payload = self.build_payload(request)
        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.post(
                    f"{self.api_base}/images/generations",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_api_error(exc)
            return response.json()

    def generate_and_store(self, request: ImageGenerationRequest) -> list[GeneratedImage]:
        data = self.generate(request)
        images = self._extract_images(data)
        stored: list[GeneratedImage] = []
        with httpx.Client(timeout=self.timeout) as client:
            for image in images:
                stored.append(self._store_image(image, client=client))
        return stored

    def _extract_images(self, payload: dict[str, Any]) -> list[GeneratedImage]:
        raw_items: list[Any] = []
        if isinstance(payload.get("images"), list):
            raw_items = payload["images"]
        elif isinstance(payload.get("data"), list):
            raw_items = payload["data"]

        out: list[GeneratedImage] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            b64_json = str(item.get("b64_json") or item.get("base64") or "").strip()
            revised_prompt = str(item.get("revised_prompt") or "").strip() or None
            if url:
                out.append(GeneratedImage(url=url, revised_prompt=revised_prompt, raw=item))
            elif b64_json:
                out.append(GeneratedImage(url=f"data:image/png;base64,{b64_json}", revised_prompt=revised_prompt, raw=item))
        return out

    def _store_image(self, image: GeneratedImage, *, client: httpx.Client) -> GeneratedImage:
        content: bytes | None = None
        content_type = "image/png"
        if image.url.startswith("data:"):
            header, encoded = image.url.split(",", 1)
            if ";" in header:
                content_type = header.split(":", 1)[1].split(";", 1)[0] or content_type
            content = base64.b64decode(encoded)
        else:
            try:
                response = client.get(image.url)
                response.raise_for_status()
                content = response.content
                content_type = response.headers.get("content-type", content_type).split(";", 1)[0]
            except Exception:
                content = None

        if not content:
            return image

        suffix = mimetypes.guess_extension(content_type) or ".png"
        if suffix == ".jpe":
            suffix = ".jpg"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid4().hex}{suffix}"
        path = self.output_dir / file_name
        path.write_bytes(content)
        image.file_name = file_name
        image.local_url = f"{self.public_prefix}/{file_name}"
        return image


siliconflow_image_service = SiliconFlowImageService()
