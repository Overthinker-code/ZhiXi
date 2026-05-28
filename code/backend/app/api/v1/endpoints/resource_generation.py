from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser
from app.core.config import settings
from app.schemas.resource_generation import (
    ResourceGenerationRequest,
    ResourceGenerationResponse,
)
from app.services.resource_generation_service import resource_generation_service

router = APIRouter()


@router.post("/packages", response_model=ResourceGenerationResponse)
def generate_resource_package(
    *,
    current_user: CurrentUser,
    request: ResourceGenerationRequest,
) -> Any:
    _ = current_user
    return resource_generation_service.generate(request)


@router.get("/artifacts/{package_id}/{file_name}")
def download_generated_artifact(
    *,
    current_user: CurrentUser,
    package_id: str,
    file_name: str,
) -> FileResponse:
    _ = current_user
    root = (Path(settings.BASE_PATH) / "generated_resources").resolve()
    target = (root / package_id / file_name).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Generated artifact not found")
    media_type = "application/pdf" if file_name.endswith(".pdf") else "text/plain"
    return FileResponse(path=str(target), filename=file_name, media_type=media_type)
