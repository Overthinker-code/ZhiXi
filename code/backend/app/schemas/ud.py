from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UDBase(BaseModel):
    university: str
    department: str


class UDCreate(UDBase):
    pass


class UDUpdate(BaseModel):
    university: Optional[str] = None
    department: Optional[str] = None


class UDPublicSingle(UDBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class UDPublic(BaseModel):
    data: List[UDPublicSingle]
    count: int
