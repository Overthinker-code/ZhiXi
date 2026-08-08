from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "code" / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.core.config import settings  # noqa: E402
from app.services.teaching_artifact_service import teaching_artifact_service  # noqa: E402


REQUEST = (
    "生成一个面向计算机网络初学者的TCP拥塞控制基础知识教学动画。"
    "依次讲清慢启动、拥塞避免、超时后的窗口调整、三次重复ACK触发的快速重传和快速恢复；"
    "突出cwnd与ssthresh的变化，并在结尾概括核心目标是避免网络拥塞同时提高带宽利用率。"
)


def main() -> None:
    artifact = teaching_artifact_service.generate_manim_video("TCP拥塞控制基础知识", REQUEST)
    source = Path(settings.BASE_PATH) / "uploads" / "generated_artifacts" / artifact["file_name"]
    output = ROOT / "output" / "TCP拥塞控制基础知识_千问Manim教学视频.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    print(output)


if __name__ == "__main__":
    main()
