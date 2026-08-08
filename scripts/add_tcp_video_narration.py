from __future__ import annotations

import os
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import av


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "code" / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.services.digital_human_tts import synthesize_edge_tts_to_file  # noqa: E402


SOURCE = ROOT / "output" / "TCP拥塞控制基础知识_千问Manim教学视频.mp4"
OUTPUT = ROOT / "output" / "TCP拥塞控制基础知识_中文配音版.mp4"
NARRATION = (
    "TCP拥塞控制通过调整拥塞窗口，避免网络过载。"
    "慢启动阶段，窗口快速增长；达到阈值后，进入拥塞避免，改为线性增长。"
    "发生超时时，窗口降到一；收到三个重复确认时，则快速重传，并进入快速恢复。"
)


def audio_duration(path: Path) -> float:
    with av.open(str(path)) as container:
        return float(container.duration or 0) / float(av.time_base)


def mux_with_extended_last_frame(video_path: Path, audio_path: Path, output_path: Path) -> None:
    with av.open(str(video_path)) as video_in, av.open(str(audio_path)) as audio_in, av.open(str(output_path), "w") as output:
        video_stream = video_in.streams.video[0]
        fps = video_stream.average_rate or Fraction(15, 1)
        fps_float = float(fps)
        target_frames = max(1, int(audio_duration(audio_path) * fps_float + .999))

        video_out = output.add_stream("libx264", rate=fps)
        video_out.width = video_stream.codec_context.width
        video_out.height = video_stream.codec_context.height
        video_out.pix_fmt = "yuv420p"
        video_out.options = {"crf": "20", "preset": "medium"}

        audio_out = output.add_stream("aac", rate=48000)
        audio_out.layout = "stereo"
        resampler = av.AudioResampler(format="fltp", layout="stereo", rate=48000)

        frame_index = 0
        last_rgb = None
        for frame in video_in.decode(video=0):
            last_rgb = frame.to_ndarray(format="rgb24")
            frame.pts = frame_index
            frame.time_base = Fraction(fps.denominator, fps.numerator)
            for packet in video_out.encode(frame):
                output.mux(packet)
            frame_index += 1

        if last_rgb is None:
            raise RuntimeError("原视频没有可用画面")
        while frame_index < target_frames:
            frame = av.VideoFrame.from_ndarray(last_rgb, format="rgb24")
            frame.pts = frame_index
            frame.time_base = Fraction(fps.denominator, fps.numerator)
            for packet in video_out.encode(frame):
                output.mux(packet)
            frame_index += 1
        for packet in video_out.encode(None):
            output.mux(packet)

        for frame in audio_in.decode(audio=0):
            for converted in resampler.resample(frame):
                for packet in audio_out.encode(converted):
                    output.mux(packet)
        for converted in resampler.resample(None):
            for packet in audio_out.encode(converted):
                output.mux(packet)
        for packet in audio_out.encode(None):
            output.mux(packet)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"source video not found: {SOURCE}")
    with tempfile.TemporaryDirectory(prefix="zhiyu-tcp-narration-") as temp_dir:
        audio_path = Path(temp_dir) / "narration.mp3"
        voice = synthesize_edge_tts_to_file(
            text=NARRATION,
            output_path=audio_path,
            voice_id="zh-CN-YunxiNeural",
        )
        mux_with_extended_last_frame(SOURCE, audio_path, OUTPUT)
    print(f"voice={voice}")
    print(OUTPUT)


if __name__ == "__main__":
    main()
