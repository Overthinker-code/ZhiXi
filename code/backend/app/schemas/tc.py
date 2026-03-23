from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class TCBase(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)


class TCCreate(TCBase):
    course_id: UUID
    lecturer_id: UUID


class TCUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    course_id: Optional[UUID] = None
    lecturer_id: Optional[UUID] = None


class TCPublic(TCBase):
    id: UUID
    course_id: UUID
    lecturer_id: UUID
    created_at: datetime
    updated_at: datetime
    course_name: Optional[str] = None
    lecturer_name: Optional[str] = None


class TCsPublic(BaseModel):
    data: List[TCPublic]
    count: int
