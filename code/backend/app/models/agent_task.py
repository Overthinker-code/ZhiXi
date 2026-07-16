from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base_class import Base


class AgentTask(Base):
    """A user-visible execution status for one Agent workflow run."""

    __tablename__ = "agent_task"
    __table_args__ = (
        UniqueConstraint("run_id", "task_key", name="uq_agent_task_run_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), nullable=False, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    run_id = Column(String(64), nullable=False, index=True)
    task_key = Column(String(50), nullable=False)
    agent_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default="waiting", index=True)
    progress = Column(Integer, nullable=False, default=0)
    message = Column(String(500), nullable=False, default="")
    created_time = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_time = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
