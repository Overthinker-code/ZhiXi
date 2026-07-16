from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base_class import Base


class ChatFeedback(Base):
    __tablename__ = "chat_feedback"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("chat.id"), nullable=False, index=True)
    user_id = Column(String(50), nullable=True, index=True)
    rating = Column(String(10), nullable=False)
    prompt_key = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", backref="feedbacks")
