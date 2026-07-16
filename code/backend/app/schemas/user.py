from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    username: Optional[str] = None


class UserCreate(UserBase):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    username: str | None = None


class UserUpdate(UserBase):
    password: Optional[str] = Field(default=None, min_length=10, max_length=128)


class UserInDBBase(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class User(UserInDBBase):
    pass


class UserPublic(BaseModel):
    """用于公开展示的用户信息"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False


class NewPassword(BaseModel):
    """密码更新模型"""

    current_password: str = Field(..., min_length=1, max_length=128, description="当前密码")
    new_password: str = Field(..., min_length=10, max_length=128, description="新密码")


class UsersPublic(BaseModel):
    data: list[UserPublic]
    count: int


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    username: str


class UserUpdateMe(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None


UpdatePassword = NewPassword
