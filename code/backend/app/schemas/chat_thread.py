from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ChatThreadBase(BaseModel):
    thread_id: Optional[str] = None
    title: Optional[str] = None


class ChatThreadCreate(ChatThreadBase):
    pass


class ChatThreadUpdate(BaseModel):
    title: Optional[str] = None


class ChatThreadInDBBase(ChatThreadBase):
    id: int
    thread_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatThread(ChatThreadInDBBase):
    pass
