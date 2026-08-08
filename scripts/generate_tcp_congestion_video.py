from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "code" / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.services.media_generation_service import media_generation_service  # noqa: E402


PROMPT = (
    "Create a clear 16:9 educational animation explaining the basics of TCP congestion control. "
    "Use a clean white background and stable camera. Show a sender, a network path and a receiver, "
    "plus a large congestion-window curve. First visualize slow start as rapid exponential growth, "
    "then congestion avoidance as steady linear growth. Show packet loss, reduce the threshold and "
    "congestion window, then visualize fast retransmit and fast recovery. Use distinct colored phases, "
    "simple arrows and large readable English phase labels only. No decorative illustration, no people, "
    "no brand logo, no watermark, no dense paragraphs, no random text. Educational infographic animation."
)


def main() -> None:
    if not media_generation_service.seedance_configured():
        raise SystemExit("SEEDANCE_API_KEY is not configured")
    statuses: list[str] = []
    media = media_generation_service.generate_video(PROMPT, status_callback=statuses.append)
    output = ROOT / "output" / "TCP拥塞控制基础知识_Seedance教学视频.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(media.path, output)
    print(f"provider={media.provider}")
    print(f"statuses={statuses}")
    print(output)


if __name__ == "__main__":
    main()
