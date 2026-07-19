from __future__ import annotations

from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from app.core.config import settings


GenerationType = Literal["text-to-video", "image-to-video", "reference-to-video"]
AspectRatio = Literal["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"]
Resolution = Literal["480p", "720p", "1080p", "4k"]


class SeedanceVideoRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    generation_type: GenerationType = "text-to-video"
    image_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    audio_urls: list[str] = Field(default_factory=list)
    duration: int | None = Field(default=None, ge=4, le=15)
    aspect_ratio: AspectRatio | None = None
    resolution: Resolution | None = None
    generate_audio: bool = True
    watermark: bool = False
    web_search: bool = False
    return_last_frame: bool = False
    seed: int = Field(default=-1, ge=-1, le=4294967295)
    callback_url: str | None = None
    model: str | None = None

    @model_validator(mode="after")
    def validate_media(self) -> Self:
        if self.generation_type == "text-to-video":
            return self
        if self.generation_type == "image-to-video":
            if not 1 <= len(self.image_urls) <= 2:
                raise ValueError("image-to-video requires 1 or 2 image_urls")
            return self
        has_reference = bool(self.image_urls or self.video_urls)
        if not has_reference:
            raise ValueError("reference-to-video requires at least one image_url or video_url")
        if len(self.image_urls) > 9:
            raise ValueError("reference-to-video supports at most 9 image_urls")
        if len(self.video_urls) > 3:
            raise ValueError("reference-to-video supports at most 3 video_urls")
        if len(self.audio_urls) > 3:
            raise ValueError("reference-to-video supports at most 3 audio_urls")
        if len(self.image_urls) + len(self.video_urls) + len(self.audio_urls) > 12:
            raise ValueError("reference-to-video supports at most 12 media assets")
        return self


class SeedanceVideoService:
    def __init__(self) -> None:
        self.api_base = settings.SEEDANCE_API_BASE.rstrip("/")
        self.api_key = settings.SEEDANCE_API_KEY
        self.timeout = float(settings.SEEDANCE_TIMEOUT_SECONDS)

    def configured(self) -> bool:
        return bool(self.api_base and self.api_key)

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("SEEDANCE_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _raise_seedance_error(exc: httpx.HTTPStatusError) -> None:
        response = exc.response
        detail: Any
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"Seedance API error {response.status_code}: {detail}") from exc

    def build_generation_payload(self, request: SeedanceVideoRequest) -> dict[str, Any]:
        input_payload: dict[str, Any] = {
            "prompt": request.prompt,
            "generation_type": request.generation_type,
            "duration": request.duration or settings.SEEDANCE_DEFAULT_DURATION,
            "aspect_ratio": request.aspect_ratio or settings.SEEDANCE_DEFAULT_ASPECT_RATIO,
            "resolution": request.resolution or settings.SEEDANCE_DEFAULT_RESOLUTION,
            "generate_audio": request.generate_audio,
            "watermark": request.watermark,
            "web_search": request.web_search,
            "return_last_frame": request.return_last_frame,
            "seed": request.seed,
        }
        if request.image_urls:
            input_payload["image_urls"] = request.image_urls
        if request.video_urls:
            input_payload["video_urls"] = request.video_urls
        if request.audio_urls:
            input_payload["audio_urls"] = request.audio_urls

        payload: dict[str, Any] = {
            "model": request.model or settings.SEEDANCE_MODEL,
            "input": input_payload,
        }
        if request.callback_url:
            payload["callback_url"] = request.callback_url
        return payload

    async def create_video_task(self, request: SeedanceVideoRequest) -> dict[str, Any]:
        payload = self.build_generation_payload(request)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.api_base}/v1/videos/generations",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_seedance_error(exc)
            return response.json()

    def create_video_task_sync(self, request: SeedanceVideoRequest) -> dict[str, Any]:
        payload = self.build_generation_payload(request)
        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.post(
                    f"{self.api_base}/v1/videos/generations",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_seedance_error(exc)
            return response.json()

    async def get_task(self, task_id: str) -> dict[str, Any]:
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("task_id is required")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.api_base}/v1/tasks/{task_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_seedance_error(exc)
            return response.json()

    def get_task_sync(self, task_id: str) -> dict[str, Any]:
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("task_id is required")
        with httpx.Client(timeout=self.timeout) as client:
            try:
                response = client.get(
                    f"{self.api_base}/v1/tasks/{task_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._raise_seedance_error(exc)
            return response.json()


seedance_video_service = SeedanceVideoService()
