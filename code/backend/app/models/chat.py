from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base_class import Base

class Chat(Base):
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(50), index=True)
    user_input = Column(Text, nullable=False)
    system_prompt = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 可选：如果需要关联到用户
    # user_id = Column(Integer, ForeignKey("user.id"))
    # user = relationship("User", back_populates="chats") 