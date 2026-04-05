from typing import List, Optional
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.chat_thread import ChatThread
from app.models.chat import Chat
from app.schemas.chat_thread import ChatThreadCreate, ChatThreadUpdate
from app.providers.base_provider import BaseProvider, _pydantic_to_dict


class ChatThreadProvider(BaseProvider[ChatThread, ChatThreadCreate, ChatThreadUpdate]):
    def get_by_thread_id(self, db: Session, *, thread_id: str) -> Optional[ChatThread]:
        stmt = select(ChatThread).where(ChatThread.thread_id == thread_id)
        return db.scalars(stmt).first()

    def get_by_thread_id_and_user(
        self, db: Session, *, thread_id: str, user_id: str
    ) -> Optional[ChatThread]:
        stmt = select(ChatThread).where(
            ChatThread.thread_id == thread_id,
            ChatThread.user_id == user_id,
        )
        return db.scalars(stmt).first()

    def get_multi_by_user(
        self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[ChatThread]:
        stmt = (
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(ChatThread.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    def get_multi_by_created_at(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ChatThread]:
        stmt = (
            select(ChatThread)
            .order_by(ChatThread.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    def create_with_defaults(
        self, db: Session, *, obj_in: ChatThreadCreate, user_id: Optional[str] = None
    ) -> ChatThread:
        data = dict(_pydantic_to_dict(obj_in, exclude_unset=True))
        if not data.get("thread_id"):
            data["thread_id"] = uuid4().hex
        if not data.get("title"):
            data["title"] = "新对话"
        if user_id:
            data["user_id"] = user_id
        db_obj = ChatThread(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove_by_thread_id(self, db: Session, *, thread_id: str) -> Optional[ChatThread]:
        thread = self.get_by_thread_id(db, thread_id=thread_id)
        if not thread:
            return None
        db.execute(delete(Chat).where(Chat.thread_id == thread_id))
        db.delete(thread)
        db.commit()
        return thread

    def remove_by_thread_id_and_user(
        self, db: Session, *, thread_id: str, user_id: str
    ) -> Optional[ChatThread]:
        thread = self.get_by_thread_id_and_user(db, thread_id=thread_id, user_id=user_id)
        if not thread:
            return None
        db.execute(delete(Chat).where(Chat.thread_id == thread_id))
        db.delete(thread)
        db.commit()
        return thread


chat_thread_provider = ChatThreadProvider(ChatThread)
