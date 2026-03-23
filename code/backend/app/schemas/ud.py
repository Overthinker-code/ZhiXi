from typing import Optional, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class UDBase(BaseModel):
    university: str
    department: str


class UDCreate(UDBase):
    pass


class UDUpdate(BaseModel):
    university: Optional[str] = None
    department: Optional[str] = None


class UDPublicSingle(UDBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UDPublic(BaseModel):
    data: List[UDPublicSingle]
    count: int
