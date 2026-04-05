from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base_class import Base

# 表名由 Base 生成：ChatThread -> chatthread；须与 ForeignKey 引用一致，供 relationship 推断 join
class Chat(Base):
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(
        String(50),
        ForeignKey("chatthread.thread_id", ondelete="CASCADE"),
        index=True,
    )
    user_input = Column(Text, nullable=False)
    system_prompt = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    thread = relationship("ChatThread", back_populates="chats")

    # 可选：如果需要关联到用户
    # user_id = Column(Integer, ForeignKey("user.id"))
    # user = relationship("User", back_populates="chats")