from __future__ import annotations

import mimetypes
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, SessionDep
from app.schemas.resource_generation import (
    ResourceGenerationRequest,
    ResourceGenerationResponse,
    ResourceRunPublic,
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
        status_code = {
            "COURSE_NOT_FOUND": 404,
            "COURSE_ACCESS_DENIED": 403,
            "RUN_CANCELLED": 409,
            "RESOURCE_RUN_ALREADY_ACTIVE": 409,
            "RESOURCE_RUN_QUEUE_FULL": 429,
            "CONTENT_SAFETY_BLOCKED": 422,
        }.get(exc.code, 500)
        detail = {"code": exc.code, "message": str(exc), "run_id": exc.run_id}
        if exc.safety_review:
            detail["safety"] = exc.safety_review
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc


@router.post("/runs", response_model=ResourceRunPublic, status_code=202)
def create_resource_run(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: ResourceGenerationRequest,
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key"),
    ] = None,
) -> Any:
    try:
        run = resource_package_service.create_requested_run(
            session,
            request=request,
            owner_id=current_user.id,
            idempotency_key=idempotency_key,
        )
        resource_package_service.enqueue_requested_run(run.id)
        return resource_package_service.get_run(
            session,
            run_id=run.id,
            user_id=current_user.id,
        )
    except ResourcePackagePersistenceError as exc:
        status_code = {
            "COURSE_NOT_FOUND": 404,
            "COURSE_ACCESS_DENIED": 403,
            "RESOURCE_RUN_ALREADY_ACTIVE": 409,
            "RESOURCE_RUN_QUEUE_FULL": 429,
            "CONTENT_SAFETY_BLOCKED": 422,
            "INVALID_IDEMPOTENCY_KEY": 422,
            "IDEMPOTENCY_CONFLICT": 409,
        }.get(exc.code, 500)
        detail = {"code": exc.code, "message": str(exc), "run_id": exc.run_id}
        if exc.safety_review:
            detail["safety"] = exc.safety_review
        raise HTTPException(
            status_code=status_code,
            detail=detail,
        ) from exc


@router.get("/runs/{run_id}", response_model=ResourceRunPublic)
def get_resource_run(*, session: SessionDep, current_user: CurrentUser, run_id: str) -> Any:
    run = resource_package_service.get_run(
        session, run_id=run_id, user_id=current_user.id, is_superuser=current_user.is_superuser
    )
    if not run:
        raise HTTPException(status_code=404, detail="Resource run not found")
    return run


@router.post("/runs/{run_id}/cancel", response_model=ResourceRunPublic)
def cancel_resource_run(*, session: SessionDep, current_user: CurrentUser, run_id: str) -> Any:
    run = resource_package_service.request_cancel(session, run_id=run_id, user_id=current_user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Resource run not found")
    return run


@router.post("/runs/{run_id}/resume", response_model=ResourceRunPublic)
def resume_resource_run(*, session: SessionDep, current_user: CurrentUser, run_id: str) -> Any:
    try:
        run = resource_package_service.resume(session, run_id=run_id, user_id=current_user.id)
    except ResourcePackagePersistenceError as exc:
        status_code = 429 if exc.code == "RESOURCE_RUN_QUEUE_FULL" else 409
        raise HTTPException(
            status_code=status_code,
            detail={"code": exc.code, "message": str(exc), "run_id": exc.run_id},
        ) from exc
    if not run:
        raise HTTPException(status_code=404, detail="Resource run not found")
    return run


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


@router.get("/packages/{package_id}")
def get_generated_package(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    package_id: str,
) -> Any:
    try:
        payload = resource_package_service.get_package(
            session,
            package_id=package_id,
            user_id=current_user.id,
            is_superuser=current_user.is_superuser,
        )
    except ResourcePackagePersistenceError as exc:
        if exc.code != "ARTIFACT_INTEGRITY_FAILED":
            raise
        raise HTTPException(
            status_code=409,
            detail={"code": exc.code, "message": str(exc), "run_id": exc.run_id},
        ) from exc
    if not payload:
        raise HTTPException(status_code=404, detail="Generated package not found")
    return payload


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
        target = resource_generation_service.resolve_verified_artifact_path(
            package_id,
            file_name,
        )
    except (FileNotFoundError, ValueError):
        raise HTTPException(status_code=404, detail="Generated artifact not found")
    media_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
    return FileResponse(path=str(target), filename=file_name, media_type=media_type)
