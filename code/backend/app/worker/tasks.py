from __future__ import annotations

import os
import selectors
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.digital_human_tts import ensure_edge_tts_available
from app.services.user_memory_profile_service import user_memory_profile_service
from app.worker.celery_app import celery, celery_enabled

if celery_enabled():
    _MUSE_PROGRESS_PREFIX = "DH_PROGRESS|"
    _MUSE_PROGRESS_RANGES: dict[str, tuple[int, int, str, str]] = {
        "extract_frames": (68, 72, "正在拆分素材帧", "musetalk_extract_frames"),
        "audio_features": (72, 76, "正在分析音频特征", "musetalk_audio_features"),
        "landmarks": (76, 80, "正在定位口型区域", "musetalk_landmarks"),
        "latents": (80, 86, "正在编码驱动特征", "musetalk_latents"),
        "inference": (86, 93, "正在生成口型帧", "musetalk_inference"),
        "compositing": (93, 98, "正在合成数字人画面", "musetalk_compositing"),
        "encode_video": (98, 99, "正在封装视频", "musetalk_encode_video"),
        "mux_audio": (99, 99, "正在合成音视频", "musetalk_mux_audio"),
    }

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


    def _normalize_progress(progress: int | float) -> int:
        try:
            value = int(float(progress))
        except (TypeError, ValueError):
            return 0
        return max(0, min(value, 100))


    def _update_progress(task, *, progress: int, message: str, stage: str) -> None:
        task.update_state(
            state="PROGRESS",
            meta={
                "progress": _normalize_progress(progress),
                "message": message,
                "stage": stage,
            },
        )


    def _map_musetalk_progress(
        raw_stage: str,
        current: str,
        total: str,
        detail: str,
    ) -> tuple[int, str, str] | None:
        stage_config = _MUSE_PROGRESS_RANGES.get(raw_stage)
        if stage_config is None:
            return None

        start, end, fallback_message, mapped_stage = stage_config
        try:
            total_value = max(int(total), 1)
        except (TypeError, ValueError):
            total_value = 1
        try:
            current_value = max(0, min(int(current), total_value))
        except (TypeError, ValueError):
            current_value = 0

        ratio = current_value / total_value
        progress = start + round((end - start) * ratio)
        message = detail.strip() or fallback_message
        return _normalize_progress(progress), message, mapped_stage


    def _stream_subprocess_with_progress(
        task,
        cmd: list[str],
        *,
        cwd: str,
        env: dict[str, str],
        timeout: int,
    ) -> None:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        last_progress = -1
        last_stage = ""
        start_time = time.monotonic()

        def handle_output_line(raw_line: str) -> None:
            nonlocal last_progress, last_stage
            line = raw_line.strip()
            if not line:
                return
            if line.startswith(_MUSE_PROGRESS_PREFIX):
                _, raw_stage, current, total, detail = line.split("|", 4)
                mapped = _map_musetalk_progress(raw_stage, current, total, detail)
                if mapped is None:
                    return
                progress, message, stage = mapped
                if progress > last_progress or stage != last_stage:
                    _update_progress(
                        task,
                        progress=progress,
                        message=message,
                        stage=stage,
                    )
                    last_progress = progress
                    last_stage = stage
                return
            print(line)

        try:
            if process.stdout is not None:
                selector = selectors.DefaultSelector()
                selector.register(process.stdout, selectors.EVENT_READ)
                try:
                    while True:
                        if time.monotonic() - start_time > timeout:
                            raise subprocess.TimeoutExpired(cmd, timeout)

                        if process.poll() is not None:
                            break

                        events = selector.select(timeout=1)
                        for key, _ in events:
                            raw_line = key.fileobj.readline()
                            if raw_line:
                                handle_output_line(raw_line)
                finally:
                    selector.close()

                for raw_line in process.stdout:
                    handle_output_line(raw_line)

            return_code = process.wait()
            if return_code != 0:
                raise subprocess.CalledProcessError(return_code, cmd)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise exc
        finally:
            if process.stdout is not None:
                process.stdout.close()


    def _selected_avatar_source() -> Path:
        idle_video = Path(settings.DIGITAL_HUMAN_IDLE_VIDEO)
        if idle_video.exists():
            return idle_video
        face_image = Path(settings.DIGITAL_HUMAN_FACE_IMAGE)
        if face_image.exists():
            return face_image
        raise RuntimeError("未找到数字人素材，请准备待机视频或正脸图片")


    def _resolve_musetalk_python_command() -> list[str]:
        python_path = settings.DIGITAL_HUMAN_MUSETALK_PYTHON.strip()
        if python_path:
            _ensure_path(python_path, "MuseTalk Python 解释器")
            return [python_path]

        conda_bin = settings.DIGITAL_HUMAN_MUSETALK_CONDA_BIN.strip() or "conda"
        if os.path.sep in conda_bin:
            _ensure_path(conda_bin, "Conda 可执行文件")
        elif shutil.which(conda_bin) is None:
            raise RuntimeError(
                f"未检测到 Conda 命令，请检查：{settings.DIGITAL_HUMAN_MUSETALK_CONDA_BIN}"
            )

        conda_env = settings.DIGITAL_HUMAN_MUSETALK_CONDA_ENV.strip()
        if not conda_env:
            raise RuntimeError("DIGITAL_HUMAN_MUSETALK_CONDA_ENV 未配置")

        return [conda_bin, "run", "--no-capture-output", "-n", conda_env, "python"]


    def _prepare_musetalk_config(
        *,
        task_id: str,
        avatar_source: Path,
        audio_path: Path,
        result_dir: Path,
    ) -> Path:
        template_path = Path(settings.DIGITAL_HUMAN_MUSETALK_TEMPLATE_CONFIG)
        _ensure_path(str(template_path), "MuseTalk 推理配置模板")
        with open(template_path, "r", encoding="utf-8") as file:
            config_data = yaml.safe_load(file) or {}
        if not isinstance(config_data, dict):
            raise RuntimeError("MuseTalk 推理模板格式异常，请检查 YAML 内容")

        if any(str(key).startswith("task_") for key in config_data):
            task_key = next(
                (str(key) for key in config_data if str(key).startswith("task_")),
                "task_0",
            )
            task_config = config_data.get(task_key) or {}
            if not isinstance(task_config, dict):
                task_config = {}
            task_config["video_path"] = str(avatar_source)
            task_config["audio_path"] = str(audio_path)
            task_config["result_name"] = f"{task_id}.mp4"
            config_data = {task_key: task_config}
        else:
            config_data["video_path"] = str(avatar_source)
            config_data["audio_path"] = str(audio_path)
            config_data["result_name"] = f"{task_id}.mp4"

        config_path = result_dir / f"{task_id}_inference.yaml"
        with open(config_path, "w", encoding="utf-8") as file:
            yaml.safe_dump(
                config_data,
                file,
                allow_unicode=True,
                sort_keys=False,
            )
        return config_path


    def _build_musetalk_command(config_path: Path, result_dir: Path) -> list[str]:
        cmd = _resolve_musetalk_python_command()
        cmd.extend(
            [
                "-m",
                "scripts.inference",
                "--inference_config",
                str(config_path),
                "--result_dir",
                str(result_dir),
                "--unet_model_path",
                settings.DIGITAL_HUMAN_MUSETALK_UNET_MODEL_PATH,
                "--unet_config",
                settings.DIGITAL_HUMAN_MUSETALK_UNET_CONFIG_PATH,
                "--version",
                settings.DIGITAL_HUMAN_MUSETALK_VERSION,
            ]
        )
        ffmpeg_path = settings.DIGITAL_HUMAN_FFMPEG_PATH.strip()
        if ffmpeg_path:
            cmd.extend(["--ffmpeg_path", ffmpeg_path])
        extra_args = settings.DIGITAL_HUMAN_MUSETALK_EXTRA_ARGS.strip()
        if extra_args:
            cmd.extend(shlex.split(extra_args))
        return cmd


    def _locate_generated_video(result_dir: Path) -> Path:
        candidates = [path for path in result_dir.rglob("*.mp4") if path.is_file()]
        if not candidates:
            raise RuntimeError(
                "MuseTalk 已执行，但未在结果目录中找到 mp4 文件："
                f"{result_dir}"
            )
        return max(candidates, key=lambda path: (path.stat().st_mtime, path.stat().st_size))


    def _subprocess_env() -> dict[str, str]:
        env = os.environ.copy()
        ffmpeg_path = settings.DIGITAL_HUMAN_FFMPEG_PATH.strip()
        if ffmpeg_path:
            env["FFMPEG_PATH"] = ffmpeg_path
        return env


    def _render_with_musetalk(task, *, task_id: str, audio_path: Path, video_path: Path) -> None:
        _ensure_path(settings.DIGITAL_HUMAN_MUSETALK_DIR, "MuseTalk 目录")
        _ensure_path(settings.DIGITAL_HUMAN_MUSETALK_UNET_MODEL_PATH, "MuseTalk v1.5 权重")
        _ensure_path(
            settings.DIGITAL_HUMAN_MUSETALK_UNET_CONFIG_PATH,
            "MuseTalk UNet 配置",
        )

        avatar_source = _selected_avatar_source()
        result_dir = Path(settings.DIGITAL_HUMAN_MUSETALK_RESULT_DIR) / task_id
        result_dir.mkdir(parents=True, exist_ok=True)

        _update_progress(
            task,
            progress=65,
            message="正在准备 MuseTalk 推理参数",
            stage="musetalk_prepare",
        )
        config_path = _prepare_musetalk_config(
            task_id=task_id,
            avatar_source=avatar_source,
            audio_path=audio_path,
            result_dir=result_dir,
        )

        _update_progress(
            task,
            progress=68,
            message="正在启动 MuseTalk 渲染引擎",
            stage="musetalk",
        )
        musetalk_cmd = _build_musetalk_command(config_path, result_dir)
        _stream_subprocess_with_progress(
            task,
            musetalk_cmd,
            cwd=settings.DIGITAL_HUMAN_MUSETALK_DIR,
            env=_subprocess_env(),
            timeout=settings.DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS,
        )

        generated_video = _locate_generated_video(result_dir)
        shutil.copy2(generated_video, video_path)


    def _render_with_wav2lip(*, audio_path: Path, video_path: Path) -> None:
        _ensure_path(settings.DIGITAL_HUMAN_WAV2LIP_DIR, "Wav2Lip 目录")
        _ensure_path(settings.DIGITAL_HUMAN_WAV2LIP_CHECKPOINT, "Wav2Lip 权重")
        _ensure_path(settings.DIGITAL_HUMAN_FACE_IMAGE, "数字人底图")

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
        engine = settings.DIGITAL_HUMAN_ENGINE.strip().lower()

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
                message="正在合成讲解语音",
                stage="tts",
            )
            tts_cmd = [
                *ensure_edge_tts_available(),
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

            if engine == "musetalk":
                _render_with_musetalk(
                    self,
                    task_id=task_id,
                    audio_path=audio_path,
                    video_path=video_path,
                )
            elif engine == "wav2lip":
                _update_progress(
                    self,
                    progress=75,
                    message="正在驱动数字人唇形",
                    stage="wav2lip",
                )
                _render_with_wav2lip(audio_path=audio_path, video_path=video_path)
            else:
                raise RuntimeError(
                    "DIGITAL_HUMAN_ENGINE 配置无效，请使用 musetalk 或 wav2lip。"
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
