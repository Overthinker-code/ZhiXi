from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class ChatFeedbackBase(BaseModel):
    record_id: int
    rating: str
    prompt_key: Optional[str] = None


class ChatFeedbackCreate(ChatFeedbackBase):
    pass


class ChatFeedbackInDBBase(ChatFeedbackBase):
    id: int
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatFeedback(ChatFeedbackInDBBase):
    pass


class ChatFeedbackInDB(ChatFeedbackInDBBase):
    pass
