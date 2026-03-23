from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class TeacherBase(BaseModel):
    name: str = Field(..., max_length=255)
    identifier: str = Field(..., max_length=255)


class TeacherCreate(TeacherBase):
    ud_id: UUID


class TeacherUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    identifier: Optional[str] = Field(default=None, max_length=255)
    ud_id: Optional[UUID] = None


class TeacherPublic(TeacherBase):
    id: UUID
    ud_id: UUID
    created_at: datetime
    updated_at: datetime


class TeachersPublic(BaseModel):
    data: List[TeacherPublic]
    count: int
