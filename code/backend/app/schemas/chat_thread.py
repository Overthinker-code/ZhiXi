from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


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
    # 旧数据或未触发 onupdate 时可能为空，避免校验失败导致 500
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ChatThread(ChatThreadInDBBase):
    pass
