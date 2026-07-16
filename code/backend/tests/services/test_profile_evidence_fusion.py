from __future__ import annotations

from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.db.base_class import Base
from app.models import LearningEvidence
from app.models.chat_thread import ChatThread
from app.models.conversation_message import ConversationMessage
from app.models.learning_task import LearningTask
from app.models.user import User  # noqa: F401
from app.models.user_memory_profile import UserMemoryProfile
from app.providers.chat_provider import chat_provider
from app.services.learning_task_service import learning_task_service


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    return Session(engine)


def test_grounded_chat_and_task_update_profile_without_inventing_mastery(
    monkeypatch,
) -> None:
    db = _session()
    user_id = uuid4()
    thread = ChatThread(
        thread_id=uuid4().hex,
        title="事务学习",
        user_id=str(user_id),
        knowledge_point="事务隔离级别",
    )
    db.add(thread)
    db.add(
        UserMemoryProfile(
            user_id=user_id,
            memory_profile={"mastery_map": {"既有可信知识点": 0.64}},
        )
    )
    db.commit()
    monkeypatch.setattr(
        "app.providers.chat_provider.schedule_memory_profile_refresh",
        lambda _user_id: None,
    )

    chat_provider.save_stream_turn(
        db,
        thread_id=thread.thread_id,
        user_input="课程资料如何解释可重复读？",
        response="可重复读保证同一事务内重复读取一致。",
        agent="course_rag_agent",
        intent="course_question",
        grounding_mode="course_rag",
        citations=[
            {
                "title": "数据库系统课程讲义：事务隔离",
                "source_type": "course_document",
                "chunk_id": "tx-iso-3",
                "private_prompt": "must not persist",
            }
        ],
    )

    evidence = db.exec(select(LearningEvidence)).one()
    assert evidence.source_type == "knowledge_base"
    assert evidence.event_type == "grounded_response"
    assert evidence.score is None
    assert evidence.payload["citations"] == [
        {
            "title": "数据库系统课程讲义：事务隔离",
            "source_type": "course_document",
            "chunk_id": "tx-iso-3",
        }
    ]
    assert len(db.exec(select(ConversationMessage)).all()) == 2
    profile = db.exec(select(UserMemoryProfile)).one().memory_profile
    assert profile["mastery_map"] == {"既有可信知识点": 0.64}
    assert profile["knowledge_base_context"]["recent_documents"] == [
        {
            "title": "数据库系统课程讲义：事务隔离",
            "source": "course_document",
        }
    ]

    task = learning_task_service.upsert_from_message(
        db,
        user_id=str(user_id),
        session_id=thread.thread_id,
        message="创建学习任务：明天前完成数据库事务学习",
    )
    assert task is not None
    assert db.exec(select(LearningTask)).one().id == task.id
    updated = db.exec(select(UserMemoryProfile)).one().memory_profile
    assert updated["mastery_map"] == {"既有可信知识点": 0.64}
    assert updated["current_goal"] == task.goal
    assert updated["profile_dimensions"]["current_goal"]["source_type"] == "explicit_task"
    assert updated["profile_dimensions"]["self_regulation"]["source_type"] == "behavioral_evidence"
    assert updated["knowledge_base_context"]["recent_documents"][0]["title"].startswith(
        "数据库系统课程讲义"
    )
