from typing import Any
import os
import aiofiles
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import unicodedata
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlmodel import select, and_, func, or_

from app import models
from app.api import deps
from app.core.config import settings
from app.core.upload_security import random_storage_name, validate_upload
from app.services.resource_subject_service import resolve_resource_subject
from app.services.resource_preview_service import ResourcePreviewError, resource_preview_service
from app.services.knowledge_graph_service import can_access_course
from app.services.software_engineering_course_service import (
    is_shared_course_resource,
    resolve_course_source,
)

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
    "video",
    "audio",
    "quality_checklist",
    "knowledge_graph",
    "question",
}
ALLOWED_RESOURCE_EXTENSIONS = {
    ".doc", ".docx", ".gif", ".jpeg", ".jpg", ".md", ".mmd", ".mp3", ".mp4",
    ".pdf", ".png", ".ppt", ".pptx", ".txt", ".wav", ".webm", ".webp"
}


def _ensure_resource_access(
    db: Any,
    resource: models.Resource,
    current_user: models.User,
) -> None:
    """Resources without an explicit visibility policy are private by default."""
    shared_course_access = bool(
        is_shared_course_resource(resource)
        and resource.course_id
        and can_access_course(db, user=current_user, course_id=resource.course_id)
    )
    if (
        resource.uploader_id != current_user.id
        and not current_user.is_superuser
        and not shared_course_access
    ):
        raise HTTPException(status_code=404, detail="未找到指定的资源")


def _resolve_resource_file(resource: models.Resource) -> Path:
    if is_shared_course_resource(resource):
        try:
            return resolve_course_source(resource.file_path)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail="资源文件路径无效") from exc
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
    _ensure_resource_access(db, resource, current_user)
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


def _preview_headers(filename: str) -> dict[str, str]:
    # The converted HTML is deliberately inert. Keep these headers on binary
    # previews too, so browser MIME sniffing/caching cannot widen exposure.
    # Do not set frame-ancestors here: converted HTML is fetched into an
    # authenticated blob URL and rendered in a sandboxed iframe.  A
    # `frame-ancestors 'none'` policy follows that document and makes the
    # otherwise safe preview unrenderable.  The remaining policy keeps the
    # document inert (no scripts, network, navigation, or forms).
    original_name = Path(filename).name.replace("\\", "_").replace('"', "").replace("\r", "").replace("\n", "") or "resource"
    suffix = Path(original_name).suffix.lower()
    ascii_name = unicodedata.normalize("NFKD", original_name).encode("ascii", "ignore").decode("ascii")
    ascii_name = "".join(char if char.isalnum() or char in {".", "_", "-"} else "_" for char in ascii_name).strip("._")
    if not ascii_name or ascii_name == suffix.removeprefix("."):
        ascii_name = f"resource{suffix}" if suffix else "resource"
    encoded_name = quote(original_name.encode("utf-8"), safe="!#$&+-.^_`|~")
    return {
        "Cache-Control": "private, no-store",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src data: blob:; base-uri 'none'; form-action 'none'",
        "Content-Disposition": f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{encoded_name}",
    }


def _record_resource_event(
    db: Any,
    *,
    current_user: models.User,
    resource: models.Resource,
    event_type: str,
) -> None:
    from app.services.learning_report_service import learning_report_service
    from app.services.recommendation_feedback_service import (
        feedback_idempotency_key,
        signed_weight,
    )

    observed_at = datetime.now(timezone.utc)

    learning_report_service.record_evidence(
        db,
        user_id=current_user.id,
        course_id=resource.course_id,
        knowledge_point=resource.knowledge_point or resource.title,
        source_type="resource_interaction",
        source_id=f"{resource.id}:{event_type}",
        event_type=event_type,
        weight=0.2,
        score=None,
        observed_at=observed_at,
        idempotency_key=feedback_idempotency_key(str(resource.id), event_type, observed_at),
        payload={
            "resource_id": str(resource.id),
            "resource_type": resource.type,
            "subject": resource.subject,
            "origin": "external" if resource.type == "external" else "generated",
            "topic": resource.knowledge_point,
            "signed_preference_weight": signed_weight(event_type),
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

    if not current_user.is_superuser:
        # Resource currently has no visibility column.  Do not infer
        # publication from source/package metadata: that leaked ordinary
        # uploads from other accounts.  A future explicit visibility policy
        # must opt in to broader access deliberately.
        enrolled_course_ids = list(
            db.exec(
                select(models.TC.course_id)
                .join(models.StudentTC, models.StudentTC.tc_id == models.TC.id)
                .join(models.Student, models.Student.id == models.StudentTC.student_id)
                .where(models.Student.user_id == current_user.id)
            ).all()
        )
        shared_condition = and_(
            models.Resource.course_id.in_(enrolled_course_ids),
            models.Resource.source == "课程内置资料",
            models.Resource.file_path.startswith("course_sources/"),
        ) if enrolled_course_ids else False
        conditions.append(
            or_(models.Resource.uploader_id == current_user.id, shared_condition)
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
    resource = _resource_or_404(db, resource_id, current_user)
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


@router.get("/{resource_id}/preview")
def preview_resource(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    resource_id: UUID,
) -> Response:
    """Prepare an authenticated, non-download resource preview."""
    resource = _resource_or_404(db, resource_id, current_user)
    abs_file_path = _resolve_resource_file(resource)
    try:
        # This check and prepare are intentionally both inside the boundary:
        # an uploader can delete/replace the file between them.
        if not abs_file_path.is_file():
            raise FileNotFoundError(abs_file_path)
        preview = resource_preview_service.prepare(abs_file_path)
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(status_code=404, detail="资源文件不存在或已被删除") from exc
    except ResourcePreviewError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    # Evidence is written only after both authorization and parsing/preparation
    # succeed; failed previews never become learning activity.
    _record_resource_event(
        db,
        current_user=current_user,
        resource=resource,
        event_type="resource_previewed",
    )
    db.commit()
    if preview.stream_file:
        return FileResponse(
            str(abs_file_path),
            media_type=preview.media_type,
            headers=_preview_headers(resource.file_name),
        )
    return Response(
        content=preview.content or "",
        media_type=preview.media_type,
        headers=_preview_headers(resource.file_name),
    )
