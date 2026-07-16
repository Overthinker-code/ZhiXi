from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.models.conversation_message import ConversationMessage  # noqa: F401
from app.models.learning_context import LearningContext  # noqa: F401
from app.schemas.agent_workspace import LearningContextUpdate
from app.services.conversation_context_service import conversation_context_service


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_append_turn_persists_ordered_messages_and_creates_context() -> None:
    db = _session()
    conversation_context_service.append_turn(
        db,
        session_id="session-1",
        user_id="user-1",
        user_content="为什么需要事务隔离？",
        assistant_content="事务隔离用于控制并发事务之间的可见性。",
        legacy_chat_id=7,
        assistant_metadata={"agent": "tutor"},
    )

    rows = conversation_context_service.list_messages(
        db, session_id="session-1", user_id="user-1"
    )
    assert [row.role for row in rows] == ["user", "assistant"]
    assert rows[1].message_metadata == {"agent": "tutor"}
    assert rows[0].legacy_chat_id == 7

    context = conversation_context_service.get_or_create_context(
        db, session_id="session-1", user_id="user-1"
    )
    assert context.session_id == "session-1"
    assert context.weak_points == []


def test_context_patch_preserves_fields_that_are_not_in_update() -> None:
    db = _session()
    context = conversation_context_service.get_or_create_context(
        db, session_id="session-2", user_id="user-1"
    )
    context = conversation_context_service.update_context(
        db,
        context=context,
        update=LearningContextUpdate(
            current_course="数据库系统",
            weak_points=["事务", "锁机制"],
        ),
    )
    context = conversation_context_service.update_context(
        db,
        context=context,
        update=LearningContextUpdate(user_goal="期末复习"),
    )

    assert context.current_course == "数据库系统"
    assert context.user_goal == "期末复习"
    assert context.weak_points == ["事务", "锁机制"]


def test_messages_are_isolated_by_user_and_session() -> None:
    db = _session()
    for session_id, user_id in (("session-a", "user-1"), ("session-b", "user-1"), ("session-c", "user-2")):
        conversation_context_service.append_turn(
            db,
            session_id=session_id,
            user_id=user_id,
            user_content=f"{session_id}-{user_id}",
            assistant_content="answer",
        )

    rows = conversation_context_service.list_messages(
        db, session_id="session-a", user_id="user-1"
    )
    assert len(rows) == 2
    assert rows[0].content == "session-a-user-1"
    assert conversation_context_service.list_messages(
        db, session_id="session-a", user_id="user-2"
    ) == []
