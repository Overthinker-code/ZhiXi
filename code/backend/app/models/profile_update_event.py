from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from app.db.base_class import Base


class ProfileUpdateEvent(Base):
    # Dialogue-derived profile patches are intentionally isolated from the
    # assessment-backed profile_update_event ledger used by resource runs.
    __tablename__ = "agent_profile_update_event"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), nullable=False, index=True)
    session_id = Column(String(50), nullable=True, index=True)
    message_id = Column(Integer, nullable=True, index=True)
    source_type = Column(String(40), nullable=False, default="chat")
    alpha = Column(Float, nullable=False, default=0.1)
    evidence = Column(JSON, nullable=False, default=dict)
    profile_patch = Column(JSON, nullable=False, default=dict)
    before_snapshot = Column(JSON, nullable=False, default=dict)
    after_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
