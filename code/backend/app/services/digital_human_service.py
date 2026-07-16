from __future__ import annotations

import asyncio
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import UUID

import jwt
from fastapi import UploadFile
from jwt.exceptions import InvalidTokenError
from sqlalchemy.exc import OperationalError

from app.core import security
from app.core.config import settings
from app.core.upload_security import read_upload_limited, validate_upload
from app.services.digital_human_assets import digital_human_asset_service
from app.services.digital_human_tts import ensure_edge_tts_available
from app.worker.celery_app import celery, celery_enabled


class DigitalHumanService:
    allowed_upload_extensions = {".ppt", ".pptx", ".pdf"}
    artifact_ticket_minutes = 10

    @staticmethod
    def _canonical_task_id(task_id: str) -> str | None:
        try:
            return str(UUID(str(task_id)))
        except (TypeError, ValueError):
            return None

    def _ownership_dir(self) -> Path:
        path = Path(settings.DIGITAL_HUMAN_INPUT_DIR) / ".job_owners"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ownership_path(self, task_id: str) -> Path | None:
        canonical = self._canonical_task_id(task_id)
        if canonical is None:
            return None
        return self._ownership_dir() / f"{canonical}.json"

    def _register_job_owner(self, *, task_id: str, owner_id: UUID) -> None:
        ownership_path = self._ownership_path(task_id)
        if ownership_path is None:
            raise RuntimeError("数字人任务标识无效")
        payload = {
            "task_id": str(UUID(task_id)),
            "owner_id": str(owner_id),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        temporary_path = ownership_path.with_name(
            f".{ownership_path.name}.{uuid.uuid4().hex}.tmp"
        )
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )
        os.chmod(temporary_path, 0o600)
        temporary_path.replace(ownership_path)

    def _remove_job_owner(self, task_id: str) -> None:
        ownership_path = self._ownership_path(task_id)
        if ownership_path is not None:
            ownership_path.unlink(missing_ok=True)

    def job_owner_id(self, task_id: str) -> UUID | None:
        ownership_path = self._ownership_path(task_id)
        if ownership_path is None or not ownership_path.is_file():
            return None
        try:
            payload = json.loads(ownership_path.read_text(encoding="utf-8"))
            if payload.get("task_id") != self._canonical_task_id(task_id):
                return None
            return UUID(str(payload["owner_id"]))
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            # Corrupt or legacy metadata is denied rather than guessed.
            return None

    def is_job_owned_by(self, *, task_id: str, owner_id: UUID) -> bool:
        return self.job_owner_id(task_id) == owner_id

    def artifact_task_id(self, filename: str) -> str | None:
        if not filename or Path(filename).name != filename:
            return None
        if filename.endswith("_script.json"):
            task_id = filename.removesuffix("_script.json")
        elif filename.endswith(".mp4"):
            task_id = filename.removesuffix(".mp4")
        else:
            return None
        return self._canonical_task_id(task_id)

    def artifact_owner_id(self, filename: str) -> UUID | None:
        task_id = self.artifact_task_id(filename)
        return self.job_owner_id(task_id) if task_id else None

    def create_artifact_ticket(self, *, filename: str, owner_id: UUID) -> str:
        if self.artifact_owner_id(filename) != owner_id:
            raise ValueError("数字人作品不存在")
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.artifact_ticket_minutes
        )
        return jwt.encode(
            {
                "sub": str(owner_id),
                "artifact": filename,
                "scope": "digital_human_artifact",
                "exp": expires_at,
            },
            settings.SECRET_KEY,
            algorithm=security.ALGORITHM,
        )

    def verify_artifact_ticket(self, *, filename: str, ticket: str) -> UUID | None:
        try:
            payload = jwt.decode(
                ticket,
                settings.SECRET_KEY,
                algorithms=[security.ALGORITHM],
            )
            if (
                payload.get("scope") != "digital_human_artifact"
                or payload.get("artifact") != filename
            ):
                return None
            owner_id = UUID(str(payload["sub"]))
        except (InvalidTokenError, KeyError, TypeError, ValueError):
            return None
        return owner_id if self.artifact_owner_id(filename) == owner_id else None

    def signed_artifact_url(self, *, filename: str, owner_id: UUID) -> str:
        if filename.endswith("_script.json"):
            route = "scripts"
        elif filename.endswith(".mp4"):
            route = "media"
        else:
            raise ValueError("不支持的数字人作品类型")
        ticket = self.create_artifact_ticket(filename=filename, owner_id=owner_id)
        return (
            f"{settings.API_V1_STR}/digital-human/{route}/{filename}"
            f"?ticket={quote(ticket)}"
        )

    @staticmethod
    def _ensure_exists(path: str, label: str) -> None:
        if not path or not os.path.exists(path):
            raise RuntimeError(f"{label} 不存在：{path}")

    @staticmethod
    def _ensure_command_available(command: str, label: str) -> None:
        if command and shutil.which(command):
            return
        if command and os.path.exists(command):
            return
        raise RuntimeError(f"未检测到 {label} 命令，请检查：{command}")

    def _ensure_musetalk_ready(self) -> None:
        self._ensure_exists(settings.DIGITAL_HUMAN_MUSETALK_DIR, "MuseTalk 目录")
        self._ensure_exists(
            settings.DIGITAL_HUMAN_MUSETALK_TEMPLATE_CONFIG,
            "MuseTalk 推理配置模板",
        )
        self._ensure_exists(
            settings.DIGITAL_HUMAN_MUSETALK_UNET_MODEL_PATH,
            "MuseTalk v1.5 权重",
        )
        self._ensure_exists(
            settings.DIGITAL_HUMAN_MUSETALK_UNET_CONFIG_PATH,
            "MuseTalk UNet 配置",
        )
        if settings.DIGITAL_HUMAN_MUSETALK_PYTHON:
            self._ensure_exists(
                settings.DIGITAL_HUMAN_MUSETALK_PYTHON,
                "MuseTalk Python 解释器",
            )
        else:
            self._ensure_command_available(
                settings.DIGITAL_HUMAN_MUSETALK_CONDA_BIN,
                "Conda",
            )
        if not (
            os.path.exists(settings.DIGITAL_HUMAN_IDLE_VIDEO)
            or os.path.exists(settings.DIGITAL_HUMAN_FACE_IMAGE)
        ):
            raise RuntimeError(
                "未检测到数字人素材，请至少准备一份待机视频或正脸图片："
                f"{settings.DIGITAL_HUMAN_IDLE_VIDEO} / "
                f"{settings.DIGITAL_HUMAN_FACE_IMAGE}"
            )

    def _ensure_wav2lip_ready(self) -> None:
        self._ensure_exists(settings.DIGITAL_HUMAN_WAV2LIP_DIR, "Wav2Lip 目录")
        self._ensure_exists(settings.DIGITAL_HUMAN_FACE_IMAGE, "数字人底图")
        self._ensure_exists(
            settings.DIGITAL_HUMAN_WAV2LIP_CHECKPOINT,
            "Wav2Lip 权重",
        )

    def ensure_worker_ready(self) -> None:
        if not celery_enabled() or celery is None:
            raise RuntimeError(
                "Celery/Redis 未启用，请先安装 celery、redis 并启动队列服务。"
            )
        ensure_edge_tts_available()
        engine = settings.DIGITAL_HUMAN_ENGINE.strip().lower()
        if engine == "fallback":
            digital_human_asset_service.ensure_default_assets()
            return
        if engine == "musetalk":
            try:
                self._ensure_musetalk_ready()
            except RuntimeError:
                if not settings.DIGITAL_HUMAN_ALLOW_FALLBACK_RENDERER:
                    raise
                digital_human_asset_service.ensure_default_assets()
            return
        if engine == "wav2lip":
            try:
                self._ensure_wav2lip_ready()
            except RuntimeError:
                if not settings.DIGITAL_HUMAN_ALLOW_FALLBACK_RENDERER:
                    raise
                digital_human_asset_service.ensure_default_assets()
            return
        raise RuntimeError(
            "DIGITAL_HUMAN_ENGINE 配置无效，请使用 musetalk、wav2lip 或 fallback。"
        )

    async def _save_source_file(self, file: UploadFile, task_id: str) -> str:
        _, suffix = await validate_upload(
            file, allowed_extensions=self.allowed_upload_extensions
        )
        job_dir = Path(settings.DIGITAL_HUMAN_INPUT_DIR)
        job_dir.mkdir(parents=True, exist_ok=True)
        target = job_dir / f"{task_id}{suffix}"
        content = await read_upload_limited(file)
        await asyncio.to_thread(target.write_bytes, content)
        return str(target)

    def _dispatch(
        self, *, task_id: str, owner_id: UUID, payload: dict[str, Any]
    ) -> dict[str, Any]:
        self.ensure_worker_ready()
        self._register_job_owner(task_id=task_id, owner_id=owner_id)
        try:
            task = celery.send_task(
                "digital_human.generate_video",
                kwargs={"task_id": task_id, **payload},
                task_id=task_id,
            )
        except OperationalError as exc:
            self._remove_job_owner(task_id)
            raise RuntimeError(f"任务队列不可用：{exc}") from exc
        except Exception as exc:
            self._remove_job_owner(task_id)
            raise RuntimeError(f"提交数字人任务失败：{exc}") from exc
        return {"task_id": task.id, "status": "pending", "message": "已加入渲染队列"}

    def create_text_job(
        self,
        *,
        owner_id: UUID,
        text: str,
        voice_id: str | None = None,
        digital_human_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        return self._dispatch(
            task_id=task_id,
            owner_id=owner_id,
            payload={
                "job_type": "text_to_video",
                "text": text,
                "voice_id": voice_id,
                "digital_human_id": digital_human_id,
                "title": title,
            },
        )

    async def create_ppt_job(
        self,
        *,
        owner_id: UUID,
        file: UploadFile,
        voice_id: str | None = None,
        digital_human_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        source_path = await self._save_source_file(file, task_id)
        try:
            return self._dispatch(
                task_id=task_id,
                owner_id=owner_id,
                payload={
                    "job_type": "ppt_to_video",
                    "source_path": source_path,
                    "voice_id": voice_id,
                    "digital_human_id": digital_human_id,
                    "title": title or file.filename,
                },
            )
        except Exception:
            Path(source_path).unlink(missing_ok=True)
            raise


digital_human_service = DigitalHumanService()
