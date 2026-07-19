from __future__ import annotations

import json
import mimetypes
import re
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings


class BailianImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    model: str | None = None
    image_size: str | None = None
    batch_size: int = Field(default=1, ge=1, le=4)


class BailianGeneratedImage(BaseModel):
    url: str
    local_url: str | None = None
    file_name: str | None = None
    revised_prompt: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class BailianService:
    """Shared Qwen/Wanx client for non-ordinary-text capabilities."""

    def __init__(self) -> None:
        self.output_dir = Path(settings.BASE_PATH) / "uploads" / "generated_images"
        self.public_prefix = f"{settings.API_V1_STR}/ai/generated-images"

    def configured(self) -> bool:
        return bool(settings.DASHSCOPE_API_KEY)

    def _headers(self, *, asynchronous: bool = False) -> dict[str, str]:
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured")
        headers = {
            "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        }
        if asynchronous:
            headers["X-DashScope-Async"] = "enable"
        return headers

    @staticmethod
    def _api_error(response: httpx.Response, capability: str) -> RuntimeError:
        try:
            detail: Any = response.json()
        except Exception:
            detail = response.text
        return RuntimeError(
            f"Bailian {capability} API error {response.status_code}: {detail}"
        )

    def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> str:
        payload = {
            "model": model or settings.QWEN_TEXT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        base = settings.DASHSCOPE_OPENAI_BASE.rstrip("/")
        with httpx.Client(timeout=settings.BAILIAN_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{base}/chat/completions", headers=self._headers(), json=payload
            )
        if response.is_error:
            raise self._api_error(response, "Qwen")
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            content = "\n".join(
                str(item.get("text") if isinstance(item, dict) else item)
                for item in content
            )
        text = str(content or "").strip()
        if not text:
            raise RuntimeError("Qwen returned empty content")
        return text

    def structured_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        max_tokens: int = 5000,
    ) -> dict[str, Any]:
        text = self.chat(
            system_prompt=system_prompt + "\n只输出一个合法 JSON 对象，不要输出 Markdown 代码围栏。",
            user_prompt=user_prompt,
            model=model,
            temperature=0.15,
            max_tokens=max_tokens,
        )
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if not match:
                raise RuntimeError("Qwen did not return a JSON object")
            payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise RuntimeError("Qwen structured output must be a JSON object")
        return payload

    def generate_mermaid(self, request_text: str) -> tuple[str, str]:
        response = self.structured_json(
            system_prompt=(
                "你是高校课程图表工程师。根据请求生成 Mermaid 图，保证节点关系准确、"
                "中文标签简短、禁止插画描述。允许 flowchart、mindmap、sequenceDiagram、"
                "stateDiagram-v2、classDiagram、erDiagram。JSON 字段为 diagram_type 和 code。"
            ),
            user_prompt=request_text,
        )
        kind = str(response.get("diagram_type") or "flowchart").strip()
        code = str(response.get("code") or "").strip()
        code = re.sub(r"^```(?:mermaid)?\s*|\s*```$", "", code, flags=re.I)
        code = code.lstrip("\ufeff \t\r\n")
        allowed_starts = (
            "flowchart", "graph", "mindmap", "sequenceDiagram",
            "stateDiagram", "classDiagram", "erDiagram",
        )
        if not code.startswith(allowed_starts):
            # Some models add a one-line prose prefix even when JSON output was
            # requested. Keep only the Mermaid document and reject anything
            # before it instead of passing model prose to the renderer.
            match = re.search(
                r"(?m)^(flowchart|graph|mindmap|sequenceDiagram|stateDiagram(?:-v2)?|classDiagram|erDiagram)\b",
                code,
            )
            if match:
                code = code[match.start():].strip()
        if not code.startswith(allowed_starts):
            raise RuntimeError("Qwen returned unsupported Mermaid syntax")
        if re.search(r"(?im)^\s*(?:click\s+|%%\{init:)", code):
            raise RuntimeError("Qwen returned disallowed interactive Mermaid directives")
        return kind, code

    def generate_image(self, request: BailianImageRequest) -> dict[str, Any]:
        size = (request.image_size or settings.WANX_IMAGE_SIZE).replace("x", "*")
        payload = {
            "model": request.model or settings.WANX_MODEL,
            "input": {"prompt": request.prompt},
            "parameters": {
                "style": "<auto>",
                "size": size,
                "n": request.batch_size,
            },
        }
        base = settings.DASHSCOPE_API_BASE.rstrip("/")
        with httpx.Client(timeout=settings.BAILIAN_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{base}/services/aigc/text2image/image-synthesis",
                headers=self._headers(asynchronous=True),
                json=payload,
            )
            if response.is_error:
                raise self._api_error(response, "Wanx image")
            created = response.json()
            task_id = str((created.get("output") or {}).get("task_id") or "").strip()
            if not task_id:
                raise RuntimeError(f"Wanx did not return task_id: {created}")
            deadline = time.monotonic() + settings.BAILIAN_TIMEOUT_SECONDS
            while time.monotonic() < deadline:
                result = client.get(f"{base}/tasks/{task_id}", headers=self._headers())
                if result.is_error:
                    raise self._api_error(result, "Wanx task")
                data = result.json()
                output = data.get("output") or {}
                status = str(output.get("task_status") or "").upper()
                if status == "SUCCEEDED":
                    return data
                if status in {"FAILED", "CANCELED", "UNKNOWN"}:
                    raise RuntimeError(f"Wanx task {status}: {output.get('message') or data}")
                time.sleep(max(0.5, settings.BAILIAN_POLL_INTERVAL_SECONDS))
        raise RuntimeError("Wanx image generation timed out")

    def generate_and_store(self, request: BailianImageRequest) -> list[BailianGeneratedImage]:
        data = self.generate_image(request)
        output = data.get("output") or {}
        raw_items = output.get("results") or output.get("task_results") or []
        images: list[BailianGeneratedImage] = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or item.get("result_url") or "").strip()
            if url:
                images.append(BailianGeneratedImage(url=url, raw=item))
        if not images:
            raise RuntimeError("Wanx task succeeded but returned no image URL")
        with httpx.Client(timeout=settings.BAILIAN_TIMEOUT_SECONDS) as client:
            return [self._store_image(image, client) for image in images]

    def _store_image(
        self, image: BailianGeneratedImage, client: httpx.Client
    ) -> BailianGeneratedImage:
        response = client.get(image.url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "image/png").split(";", 1)[0]
        suffix = mimetypes.guess_extension(content_type) or ".png"
        if suffix == ".jpe":
            suffix = ".jpg"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid4().hex}{suffix}"
        (self.output_dir / file_name).write_bytes(response.content)
        image.file_name = file_name
        image.local_url = f"{self.public_prefix}/{file_name}"
        return image


bailian_service = BailianService()
