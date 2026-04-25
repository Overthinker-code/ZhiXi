from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base_class import Base


class AIUsageLog(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True, nullable=True)
    thread_id = Column(String(50), index=True, nullable=False)
    prompt_key = Column(String(50), nullable=True)
    provider = Column(String(50), nullable=True)
    model = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="success")
    cache_hit = Column(Boolean, nullable=False, default=False)
    grounding_mode = Column(String(30), nullable=True)
    confidence = Column(String(20), nullable=True)

    ttft_ms = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    agent_hops = Column(Integer, nullable=True)
    tool_calls_count = Column(Integer, nullable=True)
    rag_hit_count = Column(Integer, nullable=True)

    route_trace = Column(Text, nullable=True)
    extra_json = Column(Text, nullable=True)
    estimated = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
