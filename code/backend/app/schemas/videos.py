from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class VideoBase(BaseModel):
    title: str = Field(max_length=255)
    file_path: str = Field(max_length=255)
    file_name: str = Field(max_length=255)
    file_size: int
    content_type: str = Field(max_length=100)
    week: Optional[int] = Field(default=None, ge=1, le=20)


class VideoCreate(VideoBase):
    tc_id: UUID
    uploader_id: UUID


class VideoUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    week: Optional[int] = Field(default=None, ge=1, le=20)
    tc_id: Optional[UUID] = None


class VideoPublic(VideoBase):
    id: UUID
    tc_id: UUID
    uploader_id: UUID
    created_at: datetime
    updated_at: datetime


class VideosPublic(BaseModel):
    data: List[VideoPublic]
    count: int
