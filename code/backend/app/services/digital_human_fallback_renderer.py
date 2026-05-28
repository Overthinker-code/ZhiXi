from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.services.digital_human_assets import DigitalHumanAsset
from app.services.document_to_script_service import DigitalHumanScript


class DigitalHumanFallbackRenderer:
    """Deterministic FFmpeg renderer used when heavy avatar models are unavailable."""

    size = (1280, 720)
    fps = 25

    def render(
        self,
        *,
        task_id: str,
        script: DigitalHumanScript,
        asset: DigitalHumanAsset,
        audio_path: Path,
        output_path: Path,
        work_dir: Path,
    ) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        poster_path = work_dir / f"{task_id}_poster.png"
        metadata_path = work_dir / f"{task_id}_script.json"
        metadata_path.write_text(
            json.dumps(script.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._draw_poster(script=script, asset=asset, output_path=poster_path)
        duration = max(self._audio_duration(audio_path), sum(item.duration_seconds for item in script.segments), 8.0)
        self._encode_video(
            poster_path=poster_path,
            audio_path=audio_path,
            output_path=output_path,
            duration=duration,
        )

    def _draw_poster(self, *, script: DigitalHumanScript, asset: DigitalHumanAsset, output_path: Path) -> None:
        width, height = self.size
        canvas = Image.new("RGB", self.size, "#f5f7fb")
        draw = ImageDraw.Draw(canvas)
        title_font = self._font(38, bold=True)
        body_font = self._font(24)
        small_font = self._font(18)

        draw.rectangle((0, 0, width, height), fill="#f5f7fb")
        draw.rectangle((42, 42, 828, 676), fill="#ffffff", outline="#dce5f2", width=2)
        draw.rectangle((866, 42, 1238, 676), fill="#eef4ff", outline="#d7e4f4", width=2)

        draw.text((74, 72), script.title[:28], fill="#172033", font=title_font)
        draw.text((76, 128), "讲解分段与手势时间线", fill="#49627d", font=small_font)

        y = 172
        for segment in script.segments[:5]:
            draw.rounded_rectangle((74, y, 796, y + 78), radius=12, fill="#f8fbff", outline="#e2e9f3")
            draw.text((96, y + 12), segment.title[:26], fill="#18324f", font=body_font)
            detail = f"{segment.source_ref} · {segment.gesture_id} · {segment.duration_seconds:.0f}s"
            draw.text((96, y + 46), detail, fill="#68798f", font=small_font)
            y += 94

        avatar_path = Path(asset.cutout_image or asset.source_image)
        if avatar_path.exists():
            avatar = Image.open(avatar_path).convert("RGBA")
            avatar.thumbnail((330, 580), Image.Resampling.LANCZOS)
            x = 888 + (320 - avatar.width) // 2
            canvas.paste(avatar, (x, 84), avatar if avatar.mode == "RGBA" else None)

        badge_y = 578
        for item in script.gesture_timeline[:3]:
            label = str(item.get("label") or item.get("gesture_id") or "自然讲解")
            draw.rounded_rectangle((894, badge_y, 1210, badge_y + 34), radius=17, fill="#ffffff", outline="#d6e2ef")
            draw.text((912, badge_y + 7), f"{item.get('time', 0)}s  {label}", fill="#39536f", font=small_font)
            badge_y += 42

        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path)

    def _encode_video(
        self,
        *,
        poster_path: Path,
        audio_path: Path,
        output_path: Path,
        duration: float,
    ) -> None:
        ffmpeg = self._ffmpeg_command()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        vf = (
            "scale=1280:720,"
            "zoompan=z='1+0.012*sin(on/28)':d=1:s=1280x720:fps=25,"
            "format=yuv420p"
        )
        base_cmd = [
            ffmpeg,
            "-y",
            "-loop",
            "1",
            "-framerate",
            str(self.fps),
            "-i",
            str(poster_path),
            "-i",
            str(audio_path),
            "-t",
            f"{math.ceil(duration)}",
            "-vf",
            vf,
        ]
        attempts = [
            [
                *base_cmd,
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ],
            [
                *base_cmd,
                "-c:v",
                "mpeg4",
                "-q:v",
                "5",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ],
        ]
        last_error = ""
        for cmd in attempts:
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=settings.DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS,
                )
                if output_path.exists() and output_path.stat().st_size >= 1024:
                    return
            except subprocess.CalledProcessError as exc:
                last_error = (exc.stderr or exc.stdout or str(exc)).strip()[-800:]
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError(f"兜底视频合成失败：未生成有效 MP4。{last_error}")

    @staticmethod
    def _audio_duration(audio_path: Path) -> float:
        try:
            with wave.open(str(audio_path), "rb") as audio:
                frames = audio.getnframes()
                rate = audio.getframerate()
                return frames / float(rate or 1)
        except Exception:
            return 0.0

    @staticmethod
    def _ffmpeg_command() -> str:
        configured = settings.DIGITAL_HUMAN_FFMPEG_PATH.strip()
        if configured and os.path.exists(configured):
            return configured
        resolved = shutil.which(configured or "ffmpeg")
        if resolved:
            return resolved
        raise RuntimeError("未检测到 ffmpeg，无法合成数字人兜底视频")

    @staticmethod
    def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size, index=1 if bold else 0)
                except Exception:
                    continue
        return ImageFont.load_default()


digital_human_fallback_renderer = DigitalHumanFallbackRenderer()
