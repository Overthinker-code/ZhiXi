from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import select, and_, or_
import os
import aiofiles

from app import models
from app.api import deps
from app.core.config import settings
from app.core.upload_security import random_storage_name, validate_upload
from uuid import UUID

router = APIRouter()

# 创建存储视频的目录
UPLOAD_DIR = os.path.join(settings.BASE_PATH, "files", "videos")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _authorized_tc_ids(db: Any, current_user: models.User) -> list[UUID]:
    """Return only teaching classes the current student is actually enrolled in."""
    return list(
        db.exec(
            select(models.StudentTC.tc_id)
            .join(models.Student, models.Student.id == models.StudentTC.student_id)
            .where(models.Student.user_id == current_user.id)
        ).all()
    )


def _can_access_video(
    db: Any, *, current_user: models.User, video: models.Video
) -> bool:
    if current_user.is_superuser or video.uploader_id == current_user.id:
        return True
    return video.tc_id in set(_authorized_tc_ids(db, current_user))


def _get_accessible_video(
    db: Any, *, current_user: models.User, video_id: UUID
) -> models.Video:
    video = db.get(models.Video, video_id)
    if not video or not _can_access_video(
        db, current_user=current_user, video=video
    ):
        # An inaccessible object is indistinguishable from a missing object.
        raise HTTPException(status_code=404, detail="未找到指定的视频")
    return video


@router.get("/", response_model=models.VideosPublic)
def read_videos(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    title: str = None,
    tc_id: UUID = None,
    week: int = None,
    uploader_id: UUID = None,
) -> Any:
    """
    获取视频列表。
    """
    query = select(models.Video)
    conditions = []

    if not current_user.is_superuser:
        conditions.append(
            or_(
                models.Video.uploader_id == current_user.id,
                models.Video.tc_id.in_(_authorized_tc_ids(db, current_user)),
            )
        )

    if title:
        conditions.append(models.Video.title.contains(title))
    if tc_id:
        conditions.append(models.Video.tc_id == tc_id)
    if week:
        conditions.append(models.Video.week == week)
    if uploader_id:
        conditions.append(models.Video.uploader_id == uploader_id)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)
    videos = db.exec(query).all()

    count_query = select(models.Video)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total = len(db.exec(count_query).all())

    return models.VideosPublic(
        data=[
            models.VideoPublic.model_validate(video, from_attributes=True)
            for video in videos
        ],
        count=total,
    )


@router.post("/", response_model=models.VideoPublic)
async def create_video(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    title: str = Form(...),
    tc_id: UUID = Form(...),
    week: int = Form(None),
    file: UploadFile = File(...),
) -> Any:
    """
    上传新视频。
    """
    # 检查教学班是否存在
    tc = db.get(models.TC, tc_id)
    if not tc:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教学班",
        )

    # 检查周次是否在有效范围内
    if week and (week < 1 or week > 20):
        raise HTTPException(
            status_code=400,
            detail="周次必须在1到20之间",
        )

    safe_name, file_extension = await validate_upload(
        file, allowed_extensions={".mp4", ".webm"}
    )
    unique_filename = random_storage_name(file_extension)
    file_path = os.path.join("videos", unique_filename)
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

    # 创建视频记录
    video = models.Video(
        title=title,
        file_path=file_path,
        file_name=safe_name,
        file_size=file_size,
        content_type=file.content_type,
        tc_id=tc_id,
        uploader_id=current_user.id,
        week=week,
    )

    db.add(video)
    db.commit()
    db.refresh(video)

    return video


@router.get("/{video_id}", response_model=models.VideoPublic)
def read_video(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    video_id: UUID,
) -> Any:
    """
    通过ID获取视频信息。
    """
    return _get_accessible_video(
        db, current_user=current_user, video_id=video_id
    )


@router.get("/{video_id}/download")
def download_video(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    video_id: UUID,
) -> Any:
    """
    下载视频文件。
    """
    video = _get_accessible_video(
        db, current_user=current_user, video_id=video_id
    )

    file_path = os.path.join(UPLOAD_DIR, os.path.basename(video.file_path))
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="视频文件不存在或已被删除",
        )

    return FileResponse(
        file_path, media_type=video.content_type, filename=video.file_name
    )


@router.put("/{video_id}", response_model=models.VideoPublic)
def update_video(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    video_id: UUID,
    video_in: models.VideoUpdate,
) -> Any:
    """
    更新视频信息（不包括文件本身）。
    """
    video = db.get(models.Video, video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的视频",
        )

    # 检查当前用户是否是上传者或管理员
    if video.uploader_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="您没有权限修改此视频",
        )

    # 如果要更新tc_id，检查教学班是否存在
    if video_in.tc_id and video_in.tc_id != video.tc_id:
        tc = db.get(models.TC, video_in.tc_id)
        if not tc:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的教学班",
            )

    # 如果要更新week，检查是否在有效范围内
    if video_in.week and (video_in.week < 1 or video_in.week > 20):
        raise HTTPException(
            status_code=400,
            detail="周次必须在1到20之间",
        )

    video_data = video_in.dict(exclude_unset=True)
    for key, value in video_data.items():
        setattr(video, key, value)

    db.add(video)
    db.commit()
    db.refresh(video)

    return video


@router.delete("/{video_id}")
def delete_video(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    video_id: UUID,
) -> Any:
    """
    删除视频。
    """
    video = db.get(models.Video, video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的视频",
        )

    # 检查当前用户是否是上传者或管理员
    if video.uploader_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="您没有权限删除此视频",
        )

    # 删除物理文件
    file_path = os.path.join(UPLOAD_DIR, os.path.basename(video.file_path))
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(video)
    db.commit()

    return {"detail": "视频已成功删除"}
