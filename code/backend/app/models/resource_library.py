from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel


class ResourceFavorite(SQLModel, table=True):
    __tablename__ = "resource_favorite"
    __table_args__ = (
        UniqueConstraint("user_id", "resource_id", name="uq_resource_favorite_user_resource"),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    resource_id: UUID = Field(foreign_key="resource.id", index=True)
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )


class UserResourceConfig(SQLModel, table=True):
    __tablename__ = "user_resource_config"
    __table_args__ = (
        UniqueConstraint("user_id", "resource_id", name="uq_user_resource_config_user_resource"),
    )

    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    resource_id: UUID = Field(foreign_key="resource.id", index=True)
    is_top: bool = Field(default=False)
    is_hidden: bool = Field(default=False)
    created_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    updated_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
