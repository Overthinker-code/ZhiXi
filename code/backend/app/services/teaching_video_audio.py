from __future__ import annotations

import tempfile
from fractions import Fraction
from pathlib import Path

from app.services.digital_human_tts import synthesize_edge_tts_to_file


def _media_duration_seconds(path: Path) -> float:
    import av

    with av.open(str(path)) as container:
        return float(container.duration or 0) / float(av.time_base)


def add_chinese_narration(
    *,
    video_path: str | Path,
    narration: str,
    output_path: str | Path,
    voice_id: str = "zh-CN-YunxiNeural",
) -> str:
    """Synthesize Chinese speech and mux it into an MP4.

    If narration runs longer than the animation, the final frame is held so the
    explanation is never cut off. The returned value is the TTS voice used.
    """
    import av

    source = Path(video_path)
    target = Path(output_path)
    if not source.exists():
        raise RuntimeError(f"待配音视频不存在：{source}")
    if not narration.strip():
        raise RuntimeError("教学视频旁白不能为空")
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="zhiyu-video-audio-") as temp_dir:
        audio_path = Path(temp_dir) / "narration.mp3"
        voice = synthesize_edge_tts_to_file(
            text=narration.strip(),
            output_path=audio_path,
            voice_id=voice_id,
        )
        audio_seconds = _media_duration_seconds(audio_path)

        with (
            av.open(str(source)) as video_in,
            av.open(str(audio_path)) as audio_in,
            av.open(str(target), "w") as output,
        ):
            video_stream = video_in.streams.video[0]
            fps = video_stream.average_rate or Fraction(15, 1)
            target_frames = max(1, int(audio_seconds * float(fps) + 0.999))

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
                raise RuntimeError("待配音视频没有可用画面")
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

    return voice
