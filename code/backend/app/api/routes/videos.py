from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlmodel import select, and_, or_
import os
import shutil
from datetime import datetime

from app import models
from app.api import deps
from app.core.config import settings
from uuid import UUID

router = APIRouter()

# 创建存储视频的目录
UPLOAD_DIR = os.path.join(settings.BASE_PATH, "files", "videos")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

    return models.VideosPublic(data=videos, count=total)


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

    # 生成唯一的文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join("videos", unique_filename)
    abs_file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 保存文件
    with open(abs_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 获取文件大小
    file_size = os.path.getsize(abs_file_path)

    # 创建视频记录
    video = models.Video(
        title=title,
        file_path=file_path,
        file_name=file.filename,
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
    video = db.get(models.Video, video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的视频",
        )

    return video


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
    video = db.get(models.Video, video_id)
    if not video:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的视频",
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
