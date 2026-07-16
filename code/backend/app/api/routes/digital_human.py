from __future__ import annotations

import os
import shutil
from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api import deps
from app.api.deps import CurrentUser
from app.models import User
from app.core.config import settings
from app.services.digital_human_assets import digital_human_asset_service
from app.services.digital_human_service import digital_human_service
from app.worker.celery_app import celery, celery_enabled

try:
    from celery.result import AsyncResult
except Exception:  # pragma: no cover - optional runtime dependency
    AsyncResult = None  # type: ignore[assignment]

router = APIRouter()


class TextToVideoRequest(BaseModel):
    text: str
    voice_id: str | None = None
    digital_human_id: str | None = None
    title: str | None = None


def _normalize_progress(raw: object, *, success: bool = False) -> int:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 100 if success else 0

    if 0 < value <= 1:
        value *= 100
    elif value > 100 and value <= 10000 and value % 100 == 0:
        value /= 100

    if success:
        return 100
    return max(0, min(int(round(value)), 100))


def _ensure_async_result():
    if AsyncResult is None or celery is None or not celery_enabled():
        raise HTTPException(
            status_code=503,
            detail="Celery/Redis 未就绪，请先启动数字人队列服务。",
        )


def _require_job_access(task_id: str, current_user: User) -> UUID:
    owner_id = digital_human_service.job_owner_id(task_id)
    if owner_id is None or (
        not current_user.is_superuser and owner_id != current_user.id
    ):
        raise HTTPException(status_code=404, detail="未找到数字人任务")
    return owner_id


def _require_artifact_access(
    *,
    filename: str,
    current_user: User | None,
    ticket: str | None,
) -> UUID:
    owner_id = digital_human_service.artifact_owner_id(filename)
    if owner_id is None:
        raise HTTPException(status_code=404, detail="未找到数字人作品")
    if current_user is not None and (
        current_user.is_superuser or current_user.id == owner_id
    ):
        return owner_id
    if ticket and digital_human_service.verify_artifact_ticket(
        filename=filename, ticket=ticket
    ) == owner_id:
        return owner_id
    raise HTTPException(status_code=404, detail="未找到数字人作品")


@router.post("/jobs/text-to-video")
def create_text_to_video_job(
    request: TextToVideoRequest,
    current_user: CurrentUser,
):
    try:
        return digital_human_service.create_text_job(
            owner_id=current_user.id,
            text=request.text,
            voice_id=request.voice_id,
            digital_human_id=request.digital_human_id,
            title=request.title,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/jobs/ppt-to-video")
async def create_ppt_to_video_job(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    voice_id: str | None = Form(default=None),
    digital_human_id: str | None = Form(default=None),
    title: str | None = Form(default=None),
):
    try:
        return await digital_human_service.create_ppt_job(
            owner_id=current_user.id,
            file=file,
            voice_id=voice_id,
            digital_human_id=digital_human_id,
            title=title,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/jobs/{task_id}")
def get_digital_human_job_status(
    task_id: str,
    current_user: CurrentUser,
):
    owner_id = _require_job_access(task_id, current_user)
    _ensure_async_result()
    task = AsyncResult(task_id, app=celery)
    if task.state == "PENDING":
        return {"status": "pending", "progress": 0, "message": "排队中", "stage": "queued"}

    if task.state in {"STARTED", "PROGRESS"}:
        meta = task.info if isinstance(task.info, dict) else {}
        return {
            "status": "processing",
            "progress": _normalize_progress(meta.get("progress") or 5),
            "message": str(meta.get("message") or "渲染处理中"),
            "stage": str(meta.get("stage") or "processing"),
        }

    if task.state == "SUCCESS":
        result = task.result if isinstance(task.result, dict) else {}
        if result.get("status") == "error":
            return {
                "status": "failed",
                "progress": 100,
                "message": result.get("message") or "渲染失败",
                "stage": result.get("stage") or "failed",
            }
        video_name = f"{task_id}.mp4"
        script_name = f"{task_id}_script.json"
        video_url = (
            digital_human_service.signed_artifact_url(
                filename=video_name, owner_id=owner_id
            )
            if (Path(settings.DIGITAL_HUMAN_OUTPUT_DIR) / video_name).is_file()
            else None
        )
        script_url = (
            digital_human_service.signed_artifact_url(
                filename=script_name, owner_id=owner_id
            )
            if (Path(settings.DIGITAL_HUMAN_OUTPUT_DIR) / script_name).is_file()
            else None
        )
        return {
            "status": "success",
            "progress": _normalize_progress(result.get("progress") or 100, success=True),
            "message": result.get("message") or "渲染完成",
            "stage": result.get("stage") or "done",
            "video_url": video_url,
            "script_url": script_url,
            "render_engine": result.get("render_engine"),
            "gesture_timeline": result.get("gesture_timeline") or [],
        }

    failure = task.info
    return {
        "status": "failed",
        "progress": 100,
        "message": str(failure),
        "stage": "failed",
    }


@router.get("/media/{filename}")
def stream_digital_human_media(
    filename: str,
    ticket: str | None = Query(default=None),
    current_user: User | None = Depends(deps.get_optional_current_user),
):
    _require_artifact_access(
        filename=filename, current_user=current_user, ticket=ticket
    )
    file_path = Path(settings.DIGITAL_HUMAN_OUTPUT_DIR) / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="未找到数字人作品")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/scripts/{filename}")
def stream_digital_human_script(
    filename: str,
    ticket: str | None = Query(default=None),
    current_user: User | None = Depends(deps.get_optional_current_user),
):
    _require_artifact_access(
        filename=filename, current_user=current_user, ticket=ticket
    )
    file_path = Path(settings.DIGITAL_HUMAN_OUTPUT_DIR) / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="未找到数字人作品")
    return FileResponse(
        file_path,
        media_type="application/json",
        filename=filename,
    )


@router.get("/assets")
def list_digital_human_assets(current_user: CurrentUser):
    return {
        "assets": digital_human_asset_service.list_assets(),
        "gestures": digital_human_asset_service.gesture_manifest(),
    }


@router.get("/works")
def list_digital_human_works(current_user: CurrentUser):
    output_dir = Path(settings.DIGITAL_HUMAN_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    works = []
    for video_path in sorted(
        output_dir.glob("*.mp4"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    ):
        owner_id = digital_human_service.artifact_owner_id(video_path.name)
        if owner_id is None or (
            not current_user.is_superuser and owner_id != current_user.id
        ):
            continue
        script_path = output_dir / f"{video_path.stem}_script.json"
        title = video_path.stem
        job_type = "text"
        description = "数字人讲解视频"
        if script_path.exists():
            try:
                import json

                script = json.loads(script_path.read_text(encoding="utf-8"))
                title = str(script.get("title") or title)
                description = str(script.get("narration") or description)[:120]
                source_kind = str(script.get("source_kind") or "")
                job_type = "ppt" if source_kind in {"ppt", "pptx", "pdf"} else "text"
            except Exception:
                pass
        stat = video_path.stat()
        works.append(
            {
                "id": video_path.stem,
                "title": title,
                "description": description,
                "type": job_type,
                "duration": "",
                "file_size": stat.st_size,
                "created_at": datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).isoformat(),
                "video_url": digital_human_service.signed_artifact_url(
                    filename=video_path.name, owner_id=owner_id
                ),
                "script_url": (
                    digital_human_service.signed_artifact_url(
                        filename=script_path.name, owner_id=owner_id
                    )
                    if script_path.exists()
                    else None
                ),
                "digital_human_id": "teacher-default",
                "digital_human_name": "默认教师数字人",
            }
        )
    return {"works": works}


@router.get("/health")
def get_digital_human_health(current_user: CurrentUser):
    checks = {
        "celery_enabled": celery_enabled(),
        "ffmpeg": bool(
            settings.DIGITAL_HUMAN_FFMPEG_PATH.strip()
            or shutil.which("ffmpeg")
        ),
        "fallback_renderer": settings.DIGITAL_HUMAN_ALLOW_FALLBACK_RENDERER,
        "musetalk_dir": os.path.exists(settings.DIGITAL_HUMAN_MUSETALK_DIR),
        "musetalk_unet": os.path.exists(settings.DIGITAL_HUMAN_MUSETALK_UNET_MODEL_PATH),
        "musetalk_config": os.path.exists(settings.DIGITAL_HUMAN_MUSETALK_UNET_CONFIG_PATH),
        "wav2lip_dir": os.path.exists(settings.DIGITAL_HUMAN_WAV2LIP_DIR),
        "default_asset": os.path.exists(
            digital_human_asset_service.get_asset("teacher-default").source_image
        ),
    }
    return {
        "engine": settings.DIGITAL_HUMAN_ENGINE,
        "checks": checks,
        "ready": checks["celery_enabled"] and (
            checks["fallback_renderer"]
            or (checks["musetalk_dir"] and checks["musetalk_unet"] and checks["musetalk_config"])
        ),
    }
