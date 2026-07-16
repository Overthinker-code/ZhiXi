from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base_class import Base


class LearningContext(Base):
    """Long-lived structured context attached to one learning session."""

    __tablename__ = "learning_context"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), nullable=False, unique=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    current_course = Column(String(200), nullable=True)
    current_knowledge_point = Column(String(200), nullable=True)
    user_goal = Column(String(500), nullable=True)
    weak_points = Column(JSON, nullable=False, default=list)
    generated_resources = Column(JSON, nullable=False, default=list)
    historical_tasks = Column(JSON, nullable=False, default=list)
    context_data = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
