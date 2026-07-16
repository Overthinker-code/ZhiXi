from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.agent_task import AgentTask
from app.services.agent_task_service import agent_task_service


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    AgentTask.__table__.create(engine)
    return Session(engine)


def test_agent_tasks_are_incremental_and_latest_run_is_restored() -> None:
    db = _session()
    first = agent_task_service.start_run(
        db,
        session_id="session-1",
        user_id="user-1",
        run_id="run-1",
        use_knowledge=True,
        resource_mode=False,
    )
    assert [task.status for task in first] == [
        "completed",
        "running",
        "completed",
        "running",
        "waiting",
    ]

    updated = agent_task_service.update_task(
        db,
        run_id="run-1",
        task_key="knowledge",
        status="completed",
        progress=100,
        message="知识检索完成",
    )
    assert next(task for task in updated if task.task_key == "knowledge").status == "completed"

    agent_task_service.start_run(
        db,
        session_id="session-1",
        user_id="user-1",
        run_id="run-2",
        use_knowledge=False,
        resource_mode=True,
    )
    latest = agent_task_service.list_latest(db, session_id="session-1", user_id="user-1")
    assert {task.run_id for task in latest} == {"run-2"}
    assert next(task for task in latest if task.task_key == "executor").agent_name == "Resource Agent"


def test_fail_run_closes_running_and_waiting_tasks() -> None:
    db = _session()
    agent_task_service.start_run(
        db,
        session_id="session-1",
        user_id="user-1",
        run_id="run-1",
        use_knowledge=False,
        resource_mode=False,
    )
    tasks = agent_task_service.fail_run(db, run_id="run-1", message="执行失败")
    executor = next(task for task in tasks if task.task_key == "executor")
    evaluator = next(task for task in tasks if task.task_key == "evaluator")
    assert executor.status == "failed"
    assert evaluator.status == "failed"


def test_complete_run_closes_every_non_terminal_task() -> None:
    db = _session()
    agent_task_service.start_run(
        db,
        session_id="session-1",
        user_id="user-1",
        run_id="run-1",
        use_knowledge=True,
        resource_mode=True,
    )
    tasks = agent_task_service.complete_run(
        db,
        run_id="run-1",
        message="任务已完成",
    )

    assert all(task.status == "completed" for task in tasks)
    assert all(task.progress == 100 for task in tasks)
    assert all(
        task.message == "任务已完成"
        for task in tasks
        if task.task_key in {"knowledge", "executor", "evaluator"}
    )
