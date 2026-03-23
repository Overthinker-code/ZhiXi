from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.tc import TCPublic

class StudentBase(BaseModel):
    name: str
    identifier: str
    ud_id: UUID

class StudentCreate(StudentBase):
    tc_ids: Optional[List[UUID]] = []

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    identifier: Optional[str] = None
    ud_id: Optional[UUID] = None
    tc_ids: Optional[List[UUID]] = None

class StudentInDBBase(StudentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StudentPublic(StudentInDBBase):
    tcs: Optional[List[TCPublic]] = []

class StudentsPublic(BaseModel):
    data: List[StudentPublic]
    count: int
