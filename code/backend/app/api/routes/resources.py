from typing import Any
import os
import shutil
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import select, and_, func, or_

from app import models
from app.api import deps
from app.core.config import settings

router = APIRouter()

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
    "lecture_pdf",
    "practice_markdown",
    "practice_pdf",
    "mind_map",
    "reading_list",
    "case_project",
    "video_script",
    "quality_checklist",
}


def _ensure_generated_resource_access(
    resource: models.Resource,
    current_user: models.User,
) -> None:
    if (
        resource.package_id
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
) -> Any:
    """
    获取资源列表
    """
    query = select(models.Resource)
    conditions = []

    if not current_user.is_superuser:
        conditions.append(
            or_(
                models.Resource.package_id.is_(None),
                models.Resource.uploader_id == current_user.id,
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

    query = query.offset(skip).limit(limit)
    resources = db.exec(query).all()

    total_query = select(func.count(models.Resource.id))
    if conditions:
        total_query = total_query.where(and_(*conditions))

    total = db.exec(total_query).one() or 0

    return models.ResourcesPublic(data=resources, count=total)


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

    # 生成唯一的文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join("resources", unique_filename)
    abs_file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 保存文件
    with open(abs_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 获取文件大小
    file_size = os.path.getsize(abs_file_path)

    # 创建资源记录
    resource = models.Resource(
        title=title,
        type=type,
        file_name=file.filename,
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
    resource = db.get(models.Resource, resource_id)
    if not resource:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的资源"
        )

    _ensure_generated_resource_access(resource, current_user)

    return resource


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

    return FileResponse(
        str(abs_file_path),
        media_type=resource.content_type,
        filename=resource.file_name
    )
