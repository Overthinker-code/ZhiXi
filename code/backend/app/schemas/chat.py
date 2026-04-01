from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class ChatBase(BaseModel):
    thread_id: str = "default"
    user_input: str
    system_prompt: Optional[str] = None
    prompt_key: Optional[str] = "tutor"
    rag_k: Optional[int] = 4
    strict_mode: Optional[bool] = False
    active_tools: Optional[List[str]] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None

class ChatCreate(ChatBase):
    pass

class ChatUpdate(ChatBase):
    thread_id: Optional[str] = None
    user_input: Optional[str] = None
    system_prompt: Optional[str] = None
    prompt_key: Optional[str] = None
    rag_k: Optional[int] = None
    strict_mode: Optional[bool] = None
    response: Optional[str] = None

class ChatInDBBase(ChatBase):
    id: int
    response: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class Chat(ChatInDBBase):
    tool_calls: List[Dict[str, Any]] = []
    agent: Optional[str] = None
    intent: Optional[str] = None
    routing_reason: Optional[str] = None

class ChatInDB(ChatInDBBase):
    pass

class ChatResponse(BaseModel):
    """Response model for chat completion."""
    response: str
    thread_id: str
    created_at: datetime 
