from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_class import Base


class ChatArtifact(Base):
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, index=True, unique=True, nullable=False)
    agent = Column(String(50), nullable=True)
    intent = Column(String(80), nullable=True)
    routing_reason = Column(Text, nullable=True)
    confidence = Column(String(20), nullable=True)
    grounding_mode = Column(String(30), nullable=True)
    citations_json = Column(Text, nullable=True)
    suggestions_json = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
