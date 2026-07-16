from typing import Any
import os
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import select, and_, func, or_

from app import models
from app.api import deps
from app.core.config import settings
from app.core.upload_security import random_storage_name, validate_upload
from app.services.resource_subject_service import resolve_resource_subject

router = APIRouter()


class FavoriteUpdate(BaseModel):
    favorite: bool


class ResourceConfigUpdate(BaseModel):
    is_top: bool

# 创建存储资源的目录
UPLOAD_DIR = os.path.join(settings.BASE_PATH, "files", "resources")
os.makedirs(UPLOAD_DIR, exist_ok=True)

VALID_RESOURCE_TYPES = {
    "pdf",
    "ppt",
    "pptx",
    "doc",
    "docx",
    "image",
    "lecture_markdown",
    "lecture_docx",
    "lecture_pdf",
    "practice_markdown",
    "practice_docx",
    "practice_pdf",
    "mind_map",
    "reading_list",
    "case_project",
    "video_script",
    "quality_checklist",
    "knowledge_graph",
    "question",
}
ALLOWED_RESOURCE_EXTENSIONS = {
    ".doc", ".docx", ".jpeg", ".jpg", ".md", ".pdf", ".png", ".ppt", ".pptx", ".txt"
}


def _ensure_generated_resource_access(
    resource: models.Resource,
    current_user: models.User,
) -> None:
    if (
        (resource.package_id or resource.source == "agent")
        and resource.uploader_id != current_user.id
        and not current_user.is_superuser
    ):
        raise HTTPException(status_code=404, detail="未找到指定的资源")


def _resolve_resource_file(resource: models.Resource) -> Path:
    if resource.package_id:
        root = (Path(settings.BASE_PATH) / "generated_resources").resolve()
        target = (Path(settings.BASE_PATH) / resource.file_path).resolve()
        package_root = (root / resource.package_id).resolve()
        if target.parent != package_root or package_root.parent != root:
            raise HTTPException(status_code=404, detail="资源文件路径无效")
        return target
    return Path(UPLOAD_DIR) / os.path.basename(resource.file_path)


def _resource_or_404(
    db: Any,
    resource_id: UUID,
    current_user: models.User,
) -> models.Resource:
    resource = db.get(models.Resource, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail="未找到指定的资源")
    _ensure_generated_resource_access(resource, current_user)
    return resource


def _resource_payload(
    resource: models.Resource,
    *,
    favorite: bool = False,
    top: bool = False,
) -> dict[str, Any]:
    payload = models.ResourcePublic.model_validate(resource).model_dump()
    payload.update({"favorite": favorite, "top": top})
    return payload


def _record_resource_event(
    db: Any,
    *,
    current_user: models.User,
    resource: models.Resource,
    event_type: str,
) -> None:
    from app.services.learning_report_service import learning_report_service

    learning_report_service.record_evidence(
        db,
        user_id=current_user.id,
        course_id=resource.course_id,
        knowledge_point=resource.knowledge_point or resource.title,
        source_type="resource_interaction",
        source_id=f"{resource.id}:{event_type}:{datetime.now(timezone.utc).isoformat()}",
        event_type=event_type,
        weight=0.2,
        score=None,
        payload={
            "resource_id": str(resource.id),
            "resource_type": resource.type,
            "subject": resource.subject,
        },
    )


@router.get("/", response_model=models.ResourcesPublic)
def read_resources(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    course_id: UUID = None,
    title: str = None,
    type: str = None,
    owned_only: bool = False,
) -> Any:
    """
    获取资源列表
    """
    query = select(models.Resource)
    conditions = []

    configs = db.exec(
        select(models.UserResourceConfig).where(
            models.UserResourceConfig.user_id == current_user.id
        )
    ).all()
    hidden_ids = {item.resource_id for item in configs if item.is_hidden}
    if hidden_ids:
        conditions.append(models.Resource.id.not_in(hidden_ids))

    if owned_only:
        conditions.append(models.Resource.uploader_id == current_user.id)

    if not current_user.is_superuser and not owned_only:
        conditions.append(
            or_(
                models.Resource.uploader_id == current_user.id,
                and_(
                    models.Resource.package_id.is_(None),
                    or_(
                        models.Resource.source.is_(None),
                        models.Resource.source != "agent",
                    ),
                ),
            )
        )

    if course_id:
        conditions.append(models.Resource.course_id == course_id)
    if title:
        conditions.append(models.Resource.title.contains(title))
    if type:
        conditions.append(models.Resource.type == type)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(models.Resource.upload_time.desc()).offset(skip).limit(limit)
    resources = db.exec(query).all()

    favorites = db.exec(
        select(models.ResourceFavorite).where(
            models.ResourceFavorite.user_id == current_user.id
        )
    ).all()
    favorite_ids = {item.resource_id for item in favorites}
    top_ids = {item.resource_id for item in configs if item.is_top and not item.is_hidden}
    resources = sorted(
        resources,
        key=lambda item: (item.id in top_ids, item.upload_time),
        reverse=True,
    )

    total_query = select(func.count(models.Resource.id))
    if conditions:
        total_query = total_query.where(and_(*conditions))

    total = db.exec(total_query).one() or 0

    return models.ResourcesPublic(
        data=[
            _resource_payload(
                resource,
                favorite=resource.id in favorite_ids,
                top=resource.id in top_ids,
            )
            for resource in resources
        ],
        count=total,
    )


@router.post("/", response_model=models.ResourcePublic)
async def create_resource(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    title: str = Form(...),
    type: str = Form(...),
    course_id: str = Form(...),
    file: UploadFile = File(...),
) -> Any:
    """
    上传新资源
    """
    # 将 course_id 转换为 UUID
    try:
        course_uuid = UUID(course_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid course_id format"
        )
    
    # 检查课程是否存在
    course = db.get(models.Course, course_uuid)
    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程"
        )

    # 验证资源类型
    if type not in VALID_RESOURCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type. Must be one of: {', '.join(sorted(VALID_RESOURCE_TYPES))}"
        )

    safe_name, extension = await validate_upload(
        file, allowed_extensions=ALLOWED_RESOURCE_EXTENSIONS
    )
    unique_filename = random_storage_name(extension)
    file_path = os.path.join("resources", unique_filename)
    abs_file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 保存文件
    file_size = 0
    async with aiofiles.open(abs_file_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.MAX_UPLOAD_SIZE:
                await buffer.close()
                os.remove(abs_file_path)
                raise HTTPException(status_code=413, detail="Uploaded file is too large")
            await buffer.write(chunk)

    # 创建资源记录
    resource = models.Resource(
        title=title,
        type=type,
        subject=resolve_resource_subject(course.name, title),
        file_name=safe_name,
        file_path=file_path,
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        course_id=course_uuid,
        uploader_id=current_user.id,
    )

    db.add(resource)
    db.commit()
    db.refresh(resource)

    return resource


@router.get("/{resource_id}", response_model=models.ResourcePublic)
def read_resource(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
) -> Any:
    """
    通过ID获取资源信息
    """
    resource = _resource_or_404(db, resource_id, current_user)
    favorite = db.exec(
        select(models.ResourceFavorite).where(
            models.ResourceFavorite.user_id == current_user.id,
            models.ResourceFavorite.resource_id == resource.id,
        )
    ).first()
    config = db.exec(
        select(models.UserResourceConfig).where(
            models.UserResourceConfig.user_id == current_user.id,
            models.UserResourceConfig.resource_id == resource.id,
        )
    ).first()
    return _resource_payload(
        resource,
        favorite=bool(favorite),
        top=bool(config and config.is_top),
    )


@router.put("/{resource_id}/favorite")
def set_resource_favorite(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
    update: FavoriteUpdate,
) -> Any:
    resource = _resource_or_404(db, resource_id, current_user)
    favorite = db.exec(
        select(models.ResourceFavorite).where(
            models.ResourceFavorite.user_id == current_user.id,
            models.ResourceFavorite.resource_id == resource_id,
        )
    ).first()
    if update.favorite and not favorite:
        db.add(models.ResourceFavorite(user_id=current_user.id, resource_id=resource_id))
    elif not update.favorite and favorite:
        db.delete(favorite)
    _record_resource_event(
        db,
        current_user=current_user,
        resource=resource,
        event_type="resource_favorited" if update.favorite else "resource_unfavorited",
    )
    db.commit()
    return {"resource_id": str(resource_id), "favorite": update.favorite}


@router.put("/{resource_id}/config")
def set_resource_config(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
    update: ResourceConfigUpdate,
) -> Any:
    resource = _resource_or_404(db, resource_id, current_user)
    config = db.exec(
        select(models.UserResourceConfig).where(
            models.UserResourceConfig.user_id == current_user.id,
            models.UserResourceConfig.resource_id == resource_id,
        )
    ).first()
    if not config:
        config = models.UserResourceConfig(user_id=current_user.id, resource_id=resource_id)
    config.is_top = update.is_top
    config.is_hidden = False
    config.updated_time = datetime.now(timezone.utc)
    db.add(config)
    _record_resource_event(
        db,
        current_user=current_user,
        resource=resource,
        event_type="resource_pinned" if update.is_top else "resource_unpinned",
    )
    db.commit()
    return {"resource_id": str(resource_id), "top": config.is_top}


@router.delete("/{resource_id}/library")
def remove_resource_from_library(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
) -> Any:
    resource = _resource_or_404(db, resource_id, current_user)
    config = db.exec(
        select(models.UserResourceConfig).where(
            models.UserResourceConfig.user_id == current_user.id,
            models.UserResourceConfig.resource_id == resource_id,
        )
    ).first()
    if not config:
        config = models.UserResourceConfig(user_id=current_user.id, resource_id=resource_id)
    config.is_hidden = True
    config.is_top = False
    config.updated_time = datetime.now(timezone.utc)
    db.add(config)
    favorite = db.exec(
        select(models.ResourceFavorite).where(
            models.ResourceFavorite.user_id == current_user.id,
            models.ResourceFavorite.resource_id == resource_id,
        )
    ).first()
    if favorite:
        db.delete(favorite)
    _record_resource_event(
        db,
        current_user=current_user,
        resource=resource,
        event_type="resource_removed_from_library",
    )
    db.commit()
    return {"resource_id": str(resource_id), "removed": True, "physical_deleted": False}


@router.put("/{resource_id}", response_model=models.ResourcePublic)
def update_resource(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
    resource_in: models.ResourceUpdate,
) -> Any:
    """
    更新资源信息（仅标题和类型）
    """
    resource = db.get(models.Resource, resource_id)
    if not resource:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的资源"
        )

    # 检查权限：只有上传者和管理员可以编辑
    if resource.uploader_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="您没有权限修改此资源"
        )

    # 更新字段
    if resource_in.title:
        resource.title = resource_in.title
    if resource_in.type:
        # 验证资源类型
        if resource_in.type not in VALID_RESOURCE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid type. Must be one of: {', '.join(sorted(VALID_RESOURCE_TYPES))}"
            )
        resource.type = resource_in.type

    db.add(resource)
    db.commit()
    db.refresh(resource)

    return resource


@router.delete("/{resource_id}")
def delete_resource(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
) -> Any:
    """
    删除资源及其对应的文件
    """
    resource = db.get(models.Resource, resource_id)
    if not resource:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的资源"
        )

    # 检查权限：只有上传者和管理员可以删除
    if resource.uploader_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="您没有权限删除此资源"
        )

    # 删除物理文件
    abs_file_path = _resolve_resource_file(resource)
    if abs_file_path.exists():
        try:
            abs_file_path.unlink()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete file: {str(e)}"
            )

    # 删除数据库记录
    db.delete(resource)
    db.commit()

    return {"message": "Resource deleted successfully"}


@router.get("/{resource_id}/download")
def download_resource(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
) -> Any:
    """
    下载资源文件
    """
    resource = db.get(models.Resource, resource_id)
    if not resource:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的资源"
        )

    _ensure_generated_resource_access(resource, current_user)
    abs_file_path = _resolve_resource_file(resource)
    if not abs_file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="资源文件不存在或已被删除"
        )

    _record_resource_event(
        db,
        current_user=current_user,
        resource=resource,
        event_type="resource_downloaded",
    )
    db.commit()

    return FileResponse(
        str(abs_file_path),
        media_type=resource.content_type,
        filename=resource.file_name
    )
