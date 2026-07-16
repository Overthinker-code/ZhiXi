from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.db.base_class import Base


class LearningTask(Base):
    """The user's current goal-oriented learning task."""

    __tablename__ = "learning_task"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(50), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    goal = Column(String(500), nullable=False, default="")
    deadline = Column(DateTime(timezone=True), nullable=True)
    current_stage = Column(String(100), nullable=False, default="任务已创建")
    progress = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="active", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
