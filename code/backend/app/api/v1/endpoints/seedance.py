from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.seedance_video_service import (
    SeedanceVideoRequest,
    seedance_video_service,
)

router = APIRouter()


class SeedanceConfigResponse(BaseModel):
    configured: bool
    api_base: str
    model: str


@router.get("/config", response_model=SeedanceConfigResponse)
async def get_seedance_config(current_user: CurrentUser):
    return SeedanceConfigResponse(
        configured=seedance_video_service.configured(),
        api_base=seedance_video_service.api_base,
        model=seedance_video_service.build_generation_payload(
            SeedanceVideoRequest(prompt="probe")
        )["model"],
    )


@router.post("/videos/generations")
async def create_seedance_video(
    request: SeedanceVideoRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    if not seedance_video_service.configured():
        raise HTTPException(status_code=503, detail="SEEDANCE_API_KEY is not configured")
    try:
        return await seedance_video_service.create_video_task(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/tasks/{task_id}")
async def get_seedance_task(
    task_id: str,
    current_user: CurrentUser,
) -> dict[str, Any]:
    if not seedance_video_service.configured():
        raise HTTPException(status_code=503, detail="SEEDANCE_API_KEY is not configured")
    try:
        return await seedance_video_service.get_task(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
