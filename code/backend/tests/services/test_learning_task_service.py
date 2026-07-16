from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.learning_task import LearningTask
from app.services.learning_task_service import learning_task_service


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    LearningTask.__table__.create(engine)
    return Session(engine)


def test_extracts_topic_and_chinese_deadline() -> None:
    parsed = learning_task_service.extract_task(
        "我要设置一个学习任务，到7月14日前完成甘特图的学习。",
        now=datetime(2026, 7, 13, 10, 0, tzinfo=timezone.utc),
    )

    assert parsed is not None
    assert parsed["title"] == "甘特图学习"
    assert parsed["deadline"].isoformat().startswith("2026-07-14")
    assert parsed["progress"] == 0


def test_new_task_replaces_previous_active_task() -> None:
    db = _session()
    first = learning_task_service.upsert_from_message(
        db,
        user_id="user-1",
        session_id="session-1",
        message="设置学习任务：明天完成数据库学习",
    )
    second = learning_task_service.upsert_from_message(
        db,
        user_id="user-1",
        session_id="session-2",
        message="创建学习任务：7月20日前完成甘特图学习",
    )

    assert first is not None and second is not None
    db.refresh(first)
    assert first.status == "replaced"
    assert learning_task_service.get_current(db, user_id="user-1").id == second.id


def test_regular_learning_question_does_not_create_task() -> None:
    parsed = learning_task_service.extract_task("请解释一下甘特图是什么")
    assert parsed is None


def test_replacement_expression_does_not_leak_into_title() -> None:
    parsed = learning_task_service.extract_task(
        "我现在要把我的学习任务换成学习黑盒白盒"
    )

    assert parsed is not None
    assert parsed["title"] == "黑盒白盒学习"


def test_manual_update_changes_definition_without_replacing_task() -> None:
    db = _session()
    task = learning_task_service.upsert_from_message(
        db,
        user_id="user-1",
        session_id="session-1",
        message="创建学习任务：7月20日前完成甘特图学习",
    )
    assert task is not None

    updated = learning_task_service.update_current(
        db,
        user_id="user-1",
        changes={"title": "项目管理基础", "goal": "能够独立绘制甘特图"},
    )

    assert updated is not None
    assert updated.id == task.id
    assert updated.title == "项目管理基础"
    assert updated.goal == "能够独立绘制甘特图"
