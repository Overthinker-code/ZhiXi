from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api import deps
from app.api.deps import CurrentUser
from app.providers.chat_thread_provider import chat_thread_provider
from app.providers.chat_provider import chat_provider
from app.services.chat_artifact_service import hydrate_chat_artifacts
from app.schemas.agent_workspace import (
    ConversationMessagePublic,
    LearningContextPublic,
    LearningContextUpdate,
)
from app.services.conversation_context_service import conversation_context_service

router = APIRouter()


def _owned_session(db: Session, session_id: str, current_user: CurrentUser) -> str:
    user_id = str(current_user.id)
    thread = chat_thread_provider.get_by_thread_id_and_user(
        db, thread_id=session_id, user_id=user_id
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Learning session not found")
    return user_id


@router.get(
    "/session/{session_id}/messages",
    response_model=list[ConversationMessagePublic],
)
def read_session_messages(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
):
    user_id = _owned_session(db, session_id, current_user)
    rows = conversation_context_service.list_messages(
        db, session_id=session_id, user_id=user_id, skip=skip, limit=limit
    )
    normalized = [
        ConversationMessagePublic(
            id=row.id,
            session_id=row.session_id,
            role=row.role,
            content=row.content,
            status=row.status,
            metadata=row.message_metadata or {},
            timestamp=row.created_at,
        )
        for row in rows
    ]
    if normalized:
        return normalized

    # Compatibility path for sessions created before normalized messages existed.
    legacy_rows = list(
        reversed(
            chat_provider.get_chat_history(
                db, thread_id=session_id, skip=skip // 2, limit=max(1, limit // 2)
            )
        )
    )
    hydrate_chat_artifacts(db, legacy_rows)
    messages: list[ConversationMessagePublic] = []
    for row in legacy_rows:
        timestamp = row.created_at
        messages.append(
            ConversationMessagePublic(
                id=-(row.id * 2),
                session_id=session_id,
                role="user",
                content=row.user_input or "",
                timestamp=timestamp,
            )
        )
        messages.append(
            ConversationMessagePublic(
                id=-(row.id * 2 + 1),
                session_id=session_id,
                role="assistant",
                content=row.response or "",
                metadata={
                    "agent": getattr(row, "agent", None),
                    "intent": getattr(row, "intent", None),
                    "citations": getattr(row, "citations", []) or [],
                    "confidence": getattr(row, "confidence", None),
                    "grounding_mode": getattr(row, "grounding_mode", None),
                    "suggestions": getattr(row, "suggestions", []) or [],
                    "metrics": getattr(row, "metrics", {}) or {},
                },
                timestamp=timestamp,
            )
        )
    return messages[:limit]


@router.get(
    "/session/{session_id}/context",
    response_model=LearningContextPublic,
)
def read_learning_context(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
):
    user_id = _owned_session(db, session_id, current_user)
    return conversation_context_service.get_or_create_context(
        db, session_id=session_id, user_id=user_id
    )


@router.patch(
    "/session/{session_id}/context",
    response_model=LearningContextPublic,
)
def patch_learning_context(
    session_id: str,
    update: LearningContextUpdate,
    current_user: CurrentUser,
    db: Session = Depends(deps.get_db),
):
    user_id = _owned_session(db, session_id, current_user)
    context = conversation_context_service.get_or_create_context(
        db, session_id=session_id, user_id=user_id
    )
    return conversation_context_service.update_context(db, context=context, update=update)
