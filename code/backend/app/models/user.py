import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field, Relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.item import Item


class User(Base, table=True):
    """User model."""

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(index=True)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    items: List["Item"] = Relationship(back_populates="owner")
    # Video 定义在根目录 app/models.py，此处用前向引用参与 back_populates
    videos: List["Video"] = Relationship(back_populates="uploader")
    # Resource 定义在根目录 app/models.py，此处用前向引用参与 back_populates
    resources: List["Resource"] = Relationship(back_populates="uploader")
