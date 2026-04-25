from __future__ import annotations

import importlib.util
import os
import shutil
import sys

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
