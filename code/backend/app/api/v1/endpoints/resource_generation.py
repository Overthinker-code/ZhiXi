from __future__ import annotations

import mimetypes
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, SessionDep
from app.schemas.resource_generation import (
    ResourceGenerationRequest,
    ResourceGenerationResponse,
)
from app.services.resource_generation_service import resource_generation_service
from app.services.resource_package_service import (
    ResourcePackagePersistenceError,
    resource_package_service,
)

router = APIRouter()


@router.post("/packages", response_model=ResourceGenerationResponse)
def generate_resource_package(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: ResourceGenerationRequest,
) -> Any:
    try:
        return resource_package_service.generate(
            session,
            request,
            owner_id=current_user.id,
        )
    except ResourcePackagePersistenceError as exc:
        status_code = 404 if exc.code == "COURSE_NOT_FOUND" else 500
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@router.get("/packages/recent")
def list_recent_generated_packages(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    course_id: UUID | None = Query(default=None),
    limit: int = Query(default=12, ge=1, le=50),
) -> Any:
    return {
        "packages": resource_package_service.list_recent(
            session,
            owner_id=current_user.id,
            course_id=course_id,
            limit=limit,
        )
    }


@router.get("/artifacts/{package_id}/{file_name}")
def download_generated_artifact(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    package_id: str,
    file_name: str,
) -> FileResponse:
    if not resource_package_service.can_access(
        session,
        package_id=package_id,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    ):
        raise HTTPException(status_code=404, detail="Generated artifact not found")
    try:
        target = resource_generation_service.resolve_artifact_path(
            package_id,
            file_name,
        )
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Generated artifact not found")
    media_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    return FileResponse(path=str(target), filename=file_name, media_type=media_type)
