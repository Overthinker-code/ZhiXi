from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class Token(BaseModel):
    """访问令牌模型"""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """令牌载荷模型"""
    sub: Optional[UUID] = None  # 用户ID
    exp: Optional[int] = None   # 过期时间 