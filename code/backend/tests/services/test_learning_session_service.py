from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.chat_thread import ChatThread
from app.services.learning_session_service import (
    analyze_learning_session,
    learning_session_service,
)


def test_first_message_analysis_extracts_learning_topic() -> None:
    result = analyze_learning_session("为什么数据库事务需要隔离级别？")

    assert result.course == "数据库"
    assert result.knowledge_point == "隔离级别"
    assert result.intent == "concept_understanding"
    assert result.title == "数据库-隔离级别理解学习"


def test_learning_plan_analysis_uses_plan_intent() -> None:
    result = analyze_learning_session("帮我制定数据库期末复习计划")

    assert result.course == "数据库"
    assert result.intent == "learning_plan"
    assert result.title.endswith("学习计划")


def test_record_turn_only_classifies_the_first_message() -> None:
    engine = create_engine("sqlite:///:memory:")
    ChatThread.__table__.create(engine)
    db = sessionmaker(bind=engine)()
    thread = ChatThread(thread_id="session-1", title="新对话", user_id="user-1")
    db.add(thread)
    db.commit()
    db.refresh(thread)

    learning_session_service.record_turn(
        db, thread=thread, first_query="为什么数据库事务需要隔离级别？"
    )
    first_title = thread.title
    first_topic = thread.knowledge_point
    first_time = thread.last_message_at

    learning_session_service.record_turn(
        db, thread=thread, first_query="接着给我讲一下索引"
    )

    assert thread.title == first_title
    assert thread.knowledge_point == first_topic
    assert thread.last_message_at >= first_time
