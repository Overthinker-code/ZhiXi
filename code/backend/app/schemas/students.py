from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.tc import TCPublic

class StudentBase(BaseModel):
    name: str
    identifier: str
    ud_id: UUID

class StudentCreate(StudentBase):
    tc_ids: Optional[List[UUID]] = Field(default_factory=list)

class StudentUpdate(BaseModel):
    name: Optional[str] = None
    identifier: Optional[str] = None
    ud_id: Optional[UUID] = None
    tc_ids: Optional[List[UUID]] = None

class StudentInDBBase(StudentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

class StudentPublic(StudentInDBBase):
    tcs: Optional[List[TCPublic]] = Field(default_factory=list)

class StudentsPublic(BaseModel):
    data: List[StudentPublic]
    count: int
