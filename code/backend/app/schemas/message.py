from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field
from sqlmodel import SQLModel

from app.core.enums import MessageStatus, MessageType


class MessageCreate(SQLModel):
    """创建消息请求模型"""

    receiver_id: UUID
    content: str = Field(min_length=1, max_length=1000)
    type: MessageType = MessageType.feedback


class Message(SQLModel):
    """返回消息信息模型"""

    id: UUID
    sender_id: Optional[UUID] = None
    sender_name: Optional[str] = None
    receiver_id: Optional[UUID] = None
    receiver_name: Optional[str] = None
    content: str
    type: MessageType
    status: MessageStatus
    created_at: datetime


class MessageUpdate(SQLModel):
    """更新消息状态模型"""

    status: MessageStatus


class UnreadCount(SQLModel):
    """未读消息数量模型"""

    count: int
