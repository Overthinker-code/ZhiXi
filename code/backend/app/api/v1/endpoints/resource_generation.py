from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from jwt.exceptions import InvalidTokenError
import jwt

from app.api import deps
from app.api.deps import CurrentUser
from app.core import security
from app.core.config import settings
from app.core.db import engine
from sqlmodel import Session
from app.models import TokenPayload, User
from app.schemas.resource_generation import (
    ResourceGenerationRequest,
    ResourceGenerationResponse,
)
from app.services.resource_generation_service import resource_generation_service

router = APIRouter()


def _resolve_download_user(token: str | None) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except InvalidTokenError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    with Session(engine) as session:
        user = session.get(User, token_data.sub)
        if not user or not user.is_active:
            raise HTTPException(status_code=403, detail="Could not validate credentials")
        return user


@router.post("/packages", response_model=ResourceGenerationResponse)
def generate_resource_package(
    *,
    current_user: CurrentUser,
    request: ResourceGenerationRequest,
) -> Any:
    _ = current_user
    return resource_generation_service.generate(request)


@router.get("/packages/recent")
def list_recent_generated_packages(
    *,
    current_user: CurrentUser,
) -> Any:
    _ = current_user
    return {"packages": resource_generation_service.list_recent_packages()}


@router.get("/artifacts/{package_id}/{file_name}")
def download_generated_artifact(
    *,
    current_user: CurrentUser | None = Depends(deps.get_optional_current_user),
    package_id: str,
    file_name: str,
    token: str | None = Query(default=None),
) -> FileResponse:
    _ = current_user or _resolve_download_user(token)
    root = (Path(settings.BASE_PATH) / "generated_resources").resolve()
    target = (root / package_id / file_name).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Generated artifact not found")
    media_type = "application/pdf" if file_name.endswith(".pdf") else "text/plain"
    return FileResponse(path=str(target), filename=file_name, media_type=media_type)
