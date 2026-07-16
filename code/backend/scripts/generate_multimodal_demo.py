#!/usr/bin/env python3
"""Generate one small, real, playable database-course video for the A3 demo.

This script deliberately uses the existing production TTS and fallback renderer
instead of checking a sample MP4 into the repository.  The generated manifest
records the renderer, voice and source scope so the UI/demo never presents it
as a fully animated digital human when only the deterministic renderer ran.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models import User
from app.services.digital_human_assets import digital_human_asset_service
from app.services.digital_human_fallback_renderer import digital_human_fallback_renderer
from app.services.digital_human_service import digital_human_service
from app.services.digital_human_tts import synthesize_edge_tts_to_file
from app.services.document_to_script_service import DocumentToScriptService


DEFAULT_TEXT = (
    "事务的 ACID 包含原子性、一致性、隔离性和持久性。原子性要求事务中的操作要么全部成功，"
    "要么全部回滚；持久性要求事务提交后，即使系统故障，结果也不能丢失。"
    "转账时，扣款和入账必须属于同一事务，否则任一步骤失败都要回滚。"
    "隔离性解决并发事务相互干扰的问题，但更高隔离级别通常意味着更高的并发控制成本。"
    "学习后请尝试解释：为什么只完成扣款却没有完成入账，会同时破坏原子性和一致性。"
)

DEMO_VIDEO_TASK_ID = "d0000002-0000-4000-8000-000000000001"


def generate(
    output_name: str,
    *,
    owner_id: UUID,
    voice: str | None = None,
) -> dict[str, object]:
    output_dir = Path(settings.DIGITAL_HUMAN_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = output_dir / "demo_work"
    task_id = Path(output_name).stem
    audio_path = work_dir / f"{task_id}.audio"
    video_path = output_dir / f"{task_id}.mp4"
    manifest_path = output_dir / f"{task_id}_manifest.json"
    script_path = output_dir / f"{task_id}_script.json"

    script = DocumentToScriptService().build_text_script(
        DEFAULT_TEXT,
        title="数据库事务 ACID：转账为什么必须完整执行",
    )
    selected_voice = synthesize_edge_tts_to_file(
        text=script.narration,
        voice_id=voice,
        output_path=audio_path,
        timeout=min(settings.DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS, 300),
    )
    asset = digital_human_asset_service.ensure_default_assets()
    digital_human_fallback_renderer.render(
        task_id=task_id,
        script=script,
        asset=asset,
        audio_path=audio_path,
        output_path=video_path,
        work_dir=work_dir,
    )
    audio_path.unlink(missing_ok=True)
    digital_human_service._register_job_owner(
        task_id=task_id,
        owner_id=owner_id,
    )

    payload: dict[str, object] = {
        "id": task_id,
        "owner_id": str(owner_id),
        "title": script.title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video_file": video_path.name,
        "video_url": f"/api/digital-human/media/{video_path.name}",
        "size_bytes": video_path.stat().st_size,
        "voice": selected_voice,
        "renderer": "deterministic_fallback_v1",
        "content_source": "project-authored database course demo text",
        "course_id": "c1111111-1111-4111-9111-111111111101",
        "knowledge_points": ["事务与原子性", "一致性", "隔离性", "持久性"],
        "gesture_timeline": script.gesture_timeline,
    }
    script_payload = {
        **script.to_dict(),
        "source_kind": "text",
        "renderer": payload["renderer"],
        "content_source": payload["content_source"],
        "course_id": payload["course_id"],
        "knowledge_points": payload["knowledge_points"],
    }
    script_path.write_text(
        json.dumps(script_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the A3 database-course multimodal demo")
    # Digital-human ownership metadata uses UUID task identifiers so media
    # authorization is fail-closed and cannot be confused with file paths.
    parser.add_argument("--output-name", default=DEMO_VIDEO_TASK_ID)
    parser.add_argument("--owner-email", default="student@example.com")
    parser.add_argument("--voice", default=None)
    args = parser.parse_args()
    with Session(engine) as session:
        owner = session.exec(
            select(User).where(User.email == args.owner_email)
        ).first()
    if owner is None:
        raise SystemExit(f"未找到数字人演示归属用户：{args.owner_email}")
    print(
        json.dumps(
            generate(args.output_name, owner_id=owner.id, voice=args.voice),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
