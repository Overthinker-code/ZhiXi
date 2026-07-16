from typing import Any

from sqlalchemy.orm import Session

from app.models.conversation_message import ConversationMessage
from app.models.learning_context import LearningContext
from app.schemas.agent_workspace import LearningContextUpdate


class ConversationContextService:
    def append_turn(
        self,
        db: Session,
        *,
        session_id: str,
        user_id: str,
        user_content: str,
        assistant_content: str,
        legacy_chat_id: int | None = None,
        assistant_metadata: dict[str, Any] | None = None,
    ) -> list[ConversationMessage]:
        messages = [
            ConversationMessage(
                session_id=session_id,
                user_id=user_id,
                role="user",
                content=user_content,
                legacy_chat_id=legacy_chat_id,
                message_metadata={},
            ),
            ConversationMessage(
                session_id=session_id,
                user_id=user_id,
                role="assistant",
                content=assistant_content,
                legacy_chat_id=legacy_chat_id,
                message_metadata=assistant_metadata or {},
            ),
        ]
        db.add_all(messages)
        existing_context = (
            db.query(LearningContext)
            .filter(
                LearningContext.session_id == session_id,
                LearningContext.user_id == user_id,
            )
            .first()
        )
        if not existing_context:
            db.add(LearningContext(session_id=session_id, user_id=user_id))
        db.commit()
        for message in messages:
            db.refresh(message)
        return messages

    def list_messages(
        self,
        db: Session,
        *,
        session_id: str,
        user_id: str,
        skip: int = 0,
        limit: int = 200,
    ) -> list[ConversationMessage]:
        return (
            db.query(ConversationMessage)
            .filter(
                ConversationMessage.session_id == session_id,
                ConversationMessage.user_id == user_id,
            )
            .order_by(ConversationMessage.created_at.asc(), ConversationMessage.id.asc())
            .offset(skip)
            .limit(min(max(limit, 1), 500))
            .all()
        )

    def get_or_create_context(
        self, db: Session, *, session_id: str, user_id: str
    ) -> LearningContext:
        context = (
            db.query(LearningContext)
            .filter(
                LearningContext.session_id == session_id,
                LearningContext.user_id == user_id,
            )
            .first()
        )
        if context:
            return context
        context = LearningContext(session_id=session_id, user_id=user_id)
        db.add(context)
        db.commit()
        db.refresh(context)
        return context

    def update_context(
        self,
        db: Session,
        *,
        context: LearningContext,
        update: LearningContextUpdate,
    ) -> LearningContext:
        values = update.model_dump(exclude_unset=True)
        for field, value in values.items():
            if value is not None:
                setattr(context, field, value)
        db.add(context)
        db.commit()
        db.refresh(context)
        return context


conversation_context_service = ConversationContextService()
