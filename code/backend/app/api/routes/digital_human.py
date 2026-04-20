from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.config import settings
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


def _ensure_async_result():
    if AsyncResult is None or celery is None or not celery_enabled():
        raise HTTPException(
            status_code=503,
            detail="Celery/Redis 未就绪，请先启动数字人队列服务。",
        )


@router.post("/jobs/text-to-video")
def create_text_to_video_job(
    request: TextToVideoRequest,
    current_user: CurrentUser,
):
    try:
        return digital_human_service.create_text_job(
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
    _ensure_async_result()
    task = AsyncResult(task_id, app=celery)
    if task.state == "PENDING":
        return {"status": "pending", "progress": 0, "message": "排队中", "stage": "queued"}

    if task.state in {"STARTED", "PROGRESS"}:
        meta = task.info if isinstance(task.info, dict) else {}
        return {
            "status": "processing",
            "progress": int(meta.get("progress") or 5),
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
        return {
            "status": "success",
            "progress": int(result.get("progress") or 100),
            "message": result.get("message") or "渲染完成",
            "stage": result.get("stage") or "done",
            "video_url": result.get("video_url"),
        }

    failure = task.info
    return {
        "status": "failed",
        "progress": 100,
        "message": str(failure),
        "stage": "failed",
    }


@router.get("/media/{filename}")
def stream_digital_human_media(filename: str):
    safe_name = os.path.basename(filename)
    file_path = Path(settings.DIGITAL_HUMAN_OUTPUT_DIR) / safe_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="生成视频不存在")
    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=safe_name,
    )
