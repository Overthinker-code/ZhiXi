from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.user_memory_profile_service import user_memory_profile_service
from app.worker.celery_app import celery, celery_enabled

if celery_enabled():

    def _ensure_path(path: str, label: str) -> None:
        if not path or not os.path.exists(path):
            raise RuntimeError(f"{label} 不存在：{path}")


    def _extract_script_text(job_type: str, text: str | None, source_path: str | None) -> str:
        if job_type == "text_to_video":
            body = (text or "").strip()
            if not body:
                raise RuntimeError("文本生成视频任务缺少脚本文本")
            return body
        if not source_path:
            raise RuntimeError("课件生成视频任务缺少源文件")
        processor = DocumentProcessor()
        extracted = processor.extract_text(source_path)
        script = " ".join((extracted or "").split())
        if not script:
            raise RuntimeError("上传的课件未提取到可用文本")
        return script[:6000]


    def _update_progress(task, *, progress: int, message: str, stage: str) -> None:
        task.update_state(
            state="PROGRESS",
            meta={"progress": progress, "message": message, "stage": stage},
        )


    @celery.task(bind=True, name="digital_human.generate_video")
    def generate_video_task(
        self,
        *,
        job_type: str,
        task_id: str,
        text: str | None = None,
        source_path: str | None = None,
        voice_id: str | None = None,
        digital_human_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        output_dir = Path(settings.DIGITAL_HUMAN_OUTPUT_DIR)
        input_dir = Path(settings.DIGITAL_HUMAN_INPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        input_dir.mkdir(parents=True, exist_ok=True)

        audio_path = output_dir / f"{task_id}.wav"
        video_path = output_dir / f"{task_id}.mp4"
        selected_voice = (voice_id or settings.DIGITAL_HUMAN_EDGE_TTS_VOICE).strip()

        _ensure_path(settings.DIGITAL_HUMAN_WAV2LIP_DIR, "Wav2Lip 目录")
        _ensure_path(settings.DIGITAL_HUMAN_WAV2LIP_CHECKPOINT, "Wav2Lip 权重")
        _ensure_path(settings.DIGITAL_HUMAN_FACE_IMAGE, "数字人底图")

        try:
            _update_progress(
                self,
                progress=10,
                message="准备脚本与语音参数",
                stage="prepare",
            )
            script_text = _extract_script_text(job_type, text, source_path)

            _update_progress(
                self,
                progress=35,
                message="正在生成语音",
                stage="tts",
            )
            tts_cmd = [
                "edge-tts",
                "--text",
                script_text,
                "--voice",
                selected_voice,
                "--write-media",
                str(audio_path),
            ]
            subprocess.run(
                tts_cmd,
                check=True,
                timeout=settings.DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS,
            )

            _update_progress(
                self,
                progress=75,
                message="正在驱动数字人唇形",
                stage="wav2lip",
            )
            wav2lip_cmd = [
                sys.executable,
                "inference.py",
                "--checkpoint_path",
                settings.DIGITAL_HUMAN_WAV2LIP_CHECKPOINT,
                "--face",
                settings.DIGITAL_HUMAN_FACE_IMAGE,
                "--audio",
                str(audio_path),
                "--outfile",
                str(video_path),
            ]
            subprocess.run(
                wav2lip_cmd,
                cwd=settings.DIGITAL_HUMAN_WAV2LIP_DIR,
                check=True,
                timeout=settings.DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS,
            )

            if audio_path.exists():
                audio_path.unlink()

            return {
                "status": "success",
                "progress": 100,
                "stage": "done",
                "message": "渲染完成",
                "video_url": f"/api/digital-human/media/{video_path.name}",
                "job_type": job_type,
                "title": title or "",
                "digital_human_id": digital_human_id or "",
            }
        except Exception as exc:
            return {
                "status": "error",
                "progress": 100,
                "stage": "failed",
                "message": str(exc),
            }
        finally:
            if source_path and os.path.exists(source_path):
                try:
                    os.remove(source_path)
                except OSError:
                    pass


    @celery.task(bind=True, name="memory_profile.refresh")
    def refresh_memory_profile_task(self, user_id: str) -> dict[str, Any]:
        _update_progress(
            self,
            progress=20,
            message="正在整理最近聊天记录",
            stage="collect_history",
        )
        result = user_memory_profile_service.refresh_profile(user_id)
        _update_progress(
            self,
            progress=100,
            message="长期记忆画像已刷新",
            stage="done",
        )
        return result
