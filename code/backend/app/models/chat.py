from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base_class import Base

# 不显式建 DB 外键（避免旧库未迁移时阻塞启动）；用 primaryjoin 满足 SQLAlchemy 2 映射
class Chat(Base):
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), index=True)
    user_input = Column(Text, nullable=False)
    system_prompt = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship(
        "ChatThread",
        back_populates="chats",
        primaryjoin="foreign(Chat.thread_id) == ChatThread.thread_id",
    )

    # 可选：如果需要关联到用户
    # user_id = Column(Integer, ForeignKey("user.id"))
    # user = relationship("User", back_populates="chats")