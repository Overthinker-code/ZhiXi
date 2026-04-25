from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.services.digital_human_tts import ensure_edge_tts_available
from app.worker.celery_app import celery, celery_enabled


class DigitalHumanService:
    allowed_upload_extensions = {".ppt", ".pptx", ".pdf"}

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
        if engine == "musetalk":
            self._ensure_musetalk_ready()
            return
        if engine == "wav2lip":
            self._ensure_wav2lip_ready()
            return
        raise RuntimeError(
            "DIGITAL_HUMAN_ENGINE 配置无效，请使用 musetalk 或 wav2lip。"
        )

    async def _save_source_file(self, file: UploadFile, task_id: str) -> str:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in self.allowed_upload_extensions:
            raise ValueError(
                f"仅支持 {', '.join(sorted(self.allowed_upload_extensions))} 文件"
            )
        job_dir = Path(settings.DIGITAL_HUMAN_INPUT_DIR)
        job_dir.mkdir(parents=True, exist_ok=True)
        target = job_dir / f"{task_id}{suffix}"
        content = await file.read()
        with open(target, "wb") as output:
            output.write(content)
        return str(target)

    def _dispatch(self, *, task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.ensure_worker_ready()
        try:
            task = celery.send_task(
                "digital_human.generate_video",
                kwargs={"task_id": task_id, **payload},
                task_id=task_id,
            )
        except OperationalError as exc:
            raise RuntimeError(f"任务队列不可用：{exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"提交数字人任务失败：{exc}") from exc
        return {"task_id": task.id, "status": "pending", "message": "已加入渲染队列"}

    def create_text_job(
        self,
        *,
        text: str,
        voice_id: str | None = None,
        digital_human_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        return self._dispatch(
            task_id=task_id,
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
        file: UploadFile,
        voice_id: str | None = None,
        digital_human_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        source_path = await self._save_source_file(file, task_id)
        return self._dispatch(
            task_id=task_id,
            payload={
                "job_type": "ppt_to_video",
                "source_path": source_path,
                "voice_id": voice_id,
                "digital_human_id": digital_human_id,
                "title": title or file.filename,
            },
        )


digital_human_service = DigitalHumanService()
