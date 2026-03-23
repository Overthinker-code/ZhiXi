from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.core.enums import MessageStatus, MessageType

class Message(SQLModel, table=True):
    """消息模型"""
    id: Optional[UUID] = Field(default=None, primary_key=True)
    sender_id: Optional[UUID] = Field(default=None, foreign_key="user.id", index=True)
    receiver_id: UUID = Field(foreign_key="user.id", index=True)
    content: str = Field(max_length=1000)
    type: MessageType = Field(default=MessageType.personal)
    status: MessageStatus = Field(default=MessageStatus.unread)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 可选的关联字段，用于API返回
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True 