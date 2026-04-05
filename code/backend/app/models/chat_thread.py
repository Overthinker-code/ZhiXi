from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ChatThread(Base):
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    user_id = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chats = relationship(
        "Chat",
        back_populates="thread",
        lazy="dynamic",
        primaryjoin="ChatThread.thread_id == foreign(Chat.thread_id)",
    )
