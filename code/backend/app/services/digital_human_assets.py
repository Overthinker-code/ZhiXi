from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class GestureTemplate:
    id: str
    label: str
    use_cases: list[str]
    default_duration: float
    fallback_motion: str


@dataclass(frozen=True)
class DigitalHumanAsset:
    id: str
    label: str
    source_image: str
    cutout_image: str
    idle_video: str | None
    default_voice: str
    gestures: list[GestureTemplate]


DEFAULT_GESTURES: list[GestureTemplate] = [
    GestureTemplate("idle", "自然讲解", ["过渡", "铺垫", "普通讲解"], 3.0, "breath"),
    GestureTemplate("explain_open", "展开解释", ["概念解释", "定义说明"], 4.0, "open-hands"),
    GestureTemplate("emphasis_one_hand", "单手强调", ["重点", "关键", "注意"], 3.0, "emphasis"),
    GestureTemplate("point_left", "指向左侧", ["左侧知识卡", "目录", "第一步"], 3.0, "point-left"),
    GestureTemplate("point_right", "指向右侧", ["公式", "步骤", "右侧图表"], 3.0, "point-right"),
    GestureTemplate("compare_two_sides", "左右对比", ["对比", "区别", "相同点"], 4.0, "compare"),
    GestureTemplate("nod_summary", "点头总结", ["总结", "归纳", "回顾"], 3.0, "nod"),
    GestureTemplate("encourage_forward", "前倾鼓励", ["批改反馈", "鼓励", "继续练习"], 3.0, "encourage"),
]


class DigitalHumanAssetService:
    """Local registry for avatar assets and teaching gesture templates."""

    manifest_name = "digital_human_assets.json"

    def __init__(self) -> None:
        self.asset_dir = Path(settings.DIGITAL_HUMAN_ASSET_DIR)
        self.manifest_path = self.asset_dir / self.manifest_name

    def ensure_default_assets(self) -> DigitalHumanAsset:
        self.asset_dir.mkdir(parents=True, exist_ok=True)
        source = self.asset_dir / "teacher_default_source.png"
        cutout = self.asset_dir / "teacher_default_cutout.png"

        legacy_face = Path(settings.DIGITAL_HUMAN_FACE_IMAGE)
        if not source.exists() and legacy_face.exists():
            shutil.copy2(legacy_face, source)
        if not cutout.exists() and source.exists():
            shutil.copy2(source, cutout)

        asset = DigitalHumanAsset(
            id="teacher-default",
            label="默认教师数字人",
            source_image=str(source),
            cutout_image=str(cutout if cutout.exists() else source),
            idle_video=(
                settings.DIGITAL_HUMAN_IDLE_VIDEO
                if os.path.exists(settings.DIGITAL_HUMAN_IDLE_VIDEO)
                else None
            ),
            default_voice=settings.DIGITAL_HUMAN_EDGE_TTS_VOICE,
            gestures=DEFAULT_GESTURES,
        )
        self._write_manifest(asset)
        return asset

    def get_asset(self, digital_human_id: str | None = None) -> DigitalHumanAsset:
        target_id = (digital_human_id or "teacher-default").strip() or "teacher-default"
        default_asset = self.ensure_default_assets()
        if target_id == default_asset.id:
            return default_asset

        manifest = self._read_manifest()
        for item in manifest.get("assets", []):
            if item.get("id") == target_id:
                return self._asset_from_dict(item)
        return default_asset

    def list_assets(self) -> list[dict[str, Any]]:
        default_asset = self.ensure_default_assets()
        return [self._asset_to_public_dict(default_asset)]

    def gesture_manifest(self) -> list[dict[str, Any]]:
        return [asdict(item) for item in DEFAULT_GESTURES]

    def _write_manifest(self, default_asset: DigitalHumanAsset) -> None:
        payload = {"assets": [self._asset_to_dict(default_asset)]}
        self.manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _read_manifest(self) -> dict[str, Any]:
        if not self.manifest_path.exists():
            return {"assets": []}
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"assets": []}

    @staticmethod
    def _asset_to_dict(asset: DigitalHumanAsset) -> dict[str, Any]:
        return {
            "id": asset.id,
            "label": asset.label,
            "source_image": asset.source_image,
            "cutout_image": asset.cutout_image,
            "idle_video": asset.idle_video,
            "default_voice": asset.default_voice,
            "gestures": [asdict(item) for item in asset.gestures],
        }

    @staticmethod
    def _asset_to_public_dict(asset: DigitalHumanAsset) -> dict[str, Any]:
        data = DigitalHumanAssetService._asset_to_dict(asset)
        data["source_image_exists"] = bool(data["source_image"] and os.path.exists(data["source_image"]))
        data["cutout_image_exists"] = bool(data["cutout_image"] and os.path.exists(data["cutout_image"]))
        data["idle_video_exists"] = bool(data["idle_video"] and os.path.exists(data["idle_video"]))
        return data

    @staticmethod
    def _asset_from_dict(data: dict[str, Any]) -> DigitalHumanAsset:
        gestures = [
            GestureTemplate(
                id=str(item.get("id") or "idle"),
                label=str(item.get("label") or "自然讲解"),
                use_cases=list(item.get("use_cases") or []),
                default_duration=float(item.get("default_duration") or 3.0),
                fallback_motion=str(item.get("fallback_motion") or "breath"),
            )
            for item in data.get("gestures", [])
        ]
        return DigitalHumanAsset(
            id=str(data.get("id") or "teacher-default"),
            label=str(data.get("label") or "默认教师数字人"),
            source_image=str(data.get("source_image") or settings.DIGITAL_HUMAN_FACE_IMAGE),
            cutout_image=str(data.get("cutout_image") or data.get("source_image") or settings.DIGITAL_HUMAN_FACE_IMAGE),
            idle_video=data.get("idle_video"),
            default_voice=str(data.get("default_voice") or settings.DIGITAL_HUMAN_EDGE_TTS_VOICE),
            gestures=gestures or DEFAULT_GESTURES,
        )


digital_human_asset_service = DigitalHumanAssetService()
