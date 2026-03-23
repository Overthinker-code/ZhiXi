from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    username: Optional[str] = None


class UserCreate(UserBase):
    email: EmailStr
    password: str
    username: str



class UserUpdate(UserBase):
    password: Optional[str] = None



class UserInDBBase(UserBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True

class User(UserInDBBase):
    pass

class UserPublic(BaseModel):
    """用于公开展示的用户信息"""
    id: UUID
    username: str
    email: EmailStr


class NewPassword(BaseModel):
    """密码更新模型"""
    current_password: str = Field(..., min_length=6, description="当前密码")
    new_password: str = Field(..., min_length=6, description="新密码") 
    
class UsersPublic(BaseModel):
    data: list[UserPublic]
    count: int
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: str
class UserUpdateMe(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    
    
    
UpdatePassword = NewPassword