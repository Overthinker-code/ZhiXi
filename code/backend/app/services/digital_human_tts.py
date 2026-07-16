from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from app.core.config import settings


def resolve_edge_tts_command() -> list[str] | None:
    configured = (settings.DIGITAL_HUMAN_EDGE_TTS_BIN or "").strip()
    if configured:
        if os.path.exists(configured):
            return [configured]
        resolved = shutil.which(configured)
        if resolved:
            return [resolved]

    resolved = shutil.which("edge-tts")
    if resolved:
        return [resolved]

    if importlib.util.find_spec("edge_tts") is not None:
        return [sys.executable, "-m", "edge_tts"]

    return None


def ensure_edge_tts_available() -> list[str]:
    command = resolve_edge_tts_command()
    if command:
        return command
    raise RuntimeError(
        "未检测到可用的 edge-tts 运行环境，请安装 edge-tts，"
        "或在 DIGITAL_HUMAN_EDGE_TTS_BIN 中配置可执行文件路径。"
    )


def _split_voice_list(raw: str) -> list[str]:
    voices: list[str] = []
    for item in (raw or "").split(","):
        voice = item.strip()
        if voice and voice not in voices:
            voices.append(voice)
    return voices


def _voice_candidates(preferred_voice: str | None) -> list[str]:
    candidates: list[str] = []
    for voice in [
        preferred_voice,
        settings.DIGITAL_HUMAN_EDGE_TTS_VOICE,
        *_split_voice_list(settings.DIGITAL_HUMAN_EDGE_TTS_FALLBACK_VOICES),
    ]:
        normalized = (voice or "").strip()
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return candidates


def synthesize_edge_tts_to_file(
    *,
    text: str,
    output_path: str | Path,
    voice_id: str | None = None,
    timeout: int | None = None,
) -> str:
    """Run edge-tts with retry and voice fallback, returning the voice that worked."""
    script = (text or "").strip()
    if not script:
        raise RuntimeError("语音合成失败：脚本文本为空")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ensure_edge_tts_available()
    attempts = max(1, int(settings.DIGITAL_HUMAN_EDGE_TTS_RETRIES or 1))
    timeout_seconds = timeout or settings.DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS
    errors: list[str] = []

    for voice in _voice_candidates(voice_id):
        for attempt in range(1, attempts + 1):
            if output.exists():
                output.unlink()
            try:
                subprocess.run(
                    [
                        *command,
                        "--text",
                        script,
                        "--voice",
                        voice,
                        "--write-media",
                        str(output),
                    ],
                    check=True,
                    timeout=timeout_seconds,
                    capture_output=True,
                    text=True,
                )
                if output.exists() and output.stat().st_size > 1024:
                    return voice
                errors.append(f"{voice} 第 {attempt} 次未生成有效音频文件")
            except subprocess.CalledProcessError as exc:
                detail = (exc.stderr or exc.stdout or str(exc)).strip()
                errors.append(f"{voice} 第 {attempt} 次失败：{detail[:240]}")
            except Exception as exc:
                errors.append(f"{voice} 第 {attempt} 次异常：{str(exc)[:240]}")
            time.sleep(0.8)

    summary = "；".join(errors[-4:]) or "未知错误"
    raise RuntimeError(f"语音合成失败，已尝试备用音色仍未成功：{summary}")
