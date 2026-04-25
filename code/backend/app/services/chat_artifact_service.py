from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.chat import Chat
from app.models.chat_artifact import ChatArtifact


def _json_dump(value: Any) -> str:
    return json.dumps(value or [], ensure_ascii=False)


def _json_load(value: str | None, *, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        parsed = json.loads(value)
        return parsed if parsed is not None else fallback
    except Exception:
        return fallback


def upsert_chat_artifact(
    db: Session,
    *,
    chat_id: int,
    agent: str | None = None,
    intent: str | None = None,
    routing_reason: str | None = None,
    confidence: str | None = None,
    grounding_mode: str | None = None,
    citations: list[dict[str, Any]] | None = None,
    suggestions: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
) -> ChatArtifact:
    artifact = db.query(ChatArtifact).filter(ChatArtifact.chat_id == chat_id).first()
    if artifact is None:
        artifact = ChatArtifact(chat_id=chat_id)
        db.add(artifact)

    artifact.agent = agent
    artifact.intent = intent
    artifact.routing_reason = routing_reason
    artifact.confidence = confidence
    artifact.grounding_mode = grounding_mode
    artifact.citations_json = _json_dump(citations or [])
    artifact.suggestions_json = _json_dump(suggestions or [])
    artifact.metrics_json = json.dumps(metrics or {}, ensure_ascii=False)
    db.commit()
    db.refresh(artifact)
    return artifact


def attach_chat_artifact(chat: Chat, artifact: ChatArtifact | None) -> Chat:
    if artifact is None:
        return chat
    setattr(chat, "agent", artifact.agent)
    setattr(chat, "intent", artifact.intent)
    setattr(chat, "routing_reason", artifact.routing_reason)
    setattr(chat, "confidence", artifact.confidence)
    setattr(chat, "grounding_mode", artifact.grounding_mode)
    setattr(chat, "citations", _json_load(artifact.citations_json, fallback=[]))
    setattr(chat, "suggestions", _json_load(artifact.suggestions_json, fallback=[]))
    setattr(chat, "metrics", _json_load(artifact.metrics_json, fallback={}))
    return chat


def hydrate_chat_artifacts(db: Session, chats: list[Chat]) -> list[Chat]:
    if not chats:
        return chats
    chat_ids = [chat.id for chat in chats if getattr(chat, "id", None) is not None]
    if not chat_ids:
        return chats
    artifact_rows = (
        db.query(ChatArtifact).filter(ChatArtifact.chat_id.in_(chat_ids)).all()
    )
    artifact_map = {row.chat_id: row for row in artifact_rows}
    return [attach_chat_artifact(chat, artifact_map.get(chat.id)) for chat in chats]
