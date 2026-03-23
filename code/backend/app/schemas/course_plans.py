from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field


class CoursePlanBase(BaseModel):
    week: int = Field(..., ge=1, le=20)
    goal: str = Field(..., max_length=1000)
    key_point: str = Field(..., max_length=1000)


class CoursePlanCreate(CoursePlanBase):
    tc_id: UUID


class CoursePlanUpdate(BaseModel):
    week: Optional[int] = Field(default=None, ge=1, le=20)
    goal: Optional[str] = Field(default=None, max_length=1000)
    key_point: Optional[str] = Field(default=None, max_length=1000)
    tc_id: Optional[UUID] = None


class CoursePlanPublic(CoursePlanBase):
    id: UUID
    tc_id: UUID
    created_at: datetime
    updated_at: datetime


class CoursePlansPublic(BaseModel):
    data: List[CoursePlanPublic]
    count: int

