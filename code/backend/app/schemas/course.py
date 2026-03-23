from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    course_type: Optional[str] = None
    identifier: str


class CourseCreate(CourseBase):
    ud_id: UUID


class CourseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    course_type: Optional[str] = None
    identifier: Optional[str] = None
    ud_id: Optional[UUID] = None


class CoursePublic(CourseBase):
    id: UUID
    ud_id: UUID
    created_at: datetime
    updated_at: datetime


class CoursesPublic(BaseModel):
    data: List[CoursePublic]
    count: int
