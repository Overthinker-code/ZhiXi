from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.agent_task import AgentTask


class AgentTaskService:
    def start_run(
        self,
        db: Session,
        *,
        session_id: str,
        user_id: str,
        run_id: str,
        use_knowledge: bool,
        resource_mode: bool,
        executor_name: str | None = None,
    ) -> list[AgentTask]:
        executor_name = executor_name or ("Resource Agent" if resource_mode else "Tutor Agent")
        definitions = [
            ("profile", "Profile Agent", "completed", 100, "已确认当前用户身份与会话上下文"),
            (
                "knowledge",
                "Knowledge Agent",
                "running" if use_knowledge else "completed",
                20 if use_knowledge else 100,
                "正在检索课程与知识证据" if use_knowledge else "本轮无需额外知识检索",
            ),
            ("planner", "Planner Agent", "completed", 100, f"已路由到 {executor_name}"),
            ("executor", executor_name, "running", 15, "正在生成学习内容"),
            ("evaluator", "Evaluator Agent", "waiting", 0, "等待输出校验"),
        ]
        rows = [
            AgentTask(
                session_id=session_id,
                user_id=user_id,
                run_id=run_id,
                task_key=key,
                agent_name=name,
                status=status,
                progress=progress,
                message=message,
            )
            for key, name, status, progress, message in definitions
        ]
        db.add_all(rows)
        db.commit()
        for row in rows:
            db.refresh(row)
        return rows

    def update_task(
        self,
        db: Session,
        *,
        run_id: str,
        task_key: str,
        status: str,
        progress: int,
        message: str,
    ) -> list[AgentTask]:
        db.execute(
            update(AgentTask)
            .where(AgentTask.run_id == run_id, AgentTask.task_key == task_key)
            .values(
                status=status,
                progress=max(0, min(100, int(progress))),
                message=message[:500],
            )
        )
        db.commit()
        return self.list_run(db, run_id=run_id)

    def fail_run(self, db: Session, *, run_id: str, message: str) -> list[AgentTask]:
        db.execute(
            update(AgentTask)
            .where(
                AgentTask.run_id == run_id,
                AgentTask.status.in_(("running", "waiting")),
            )
            .values(status="failed", message=message[:500])
        )
        db.commit()
        return self.list_run(db, run_id=run_id)

    def list_run(self, db: Session, *, run_id: str) -> list[AgentTask]:
        statement = select(AgentTask).where(AgentTask.run_id == run_id).order_by(AgentTask.id)
        return list(db.scalars(statement).all())

    def list_latest(
        self, db: Session, *, session_id: str, user_id: str
    ) -> list[AgentTask]:
        latest = db.scalars(
            select(AgentTask)
            .where(AgentTask.session_id == session_id, AgentTask.user_id == user_id)
            .order_by(AgentTask.id.desc())
            .limit(1)
        ).first()
        return self.list_run(db, run_id=latest.run_id) if latest else []

    @staticmethod
    def public_payload(rows: list[AgentTask]) -> list[dict[str, Any]]:
        return [
            {
                "id": row.id,
                "session_id": row.session_id,
                "run_id": row.run_id,
                "task_key": row.task_key,
                "agent_name": row.agent_name,
                "status": row.status,
                "progress": row.progress,
                "message": row.message,
                "created_time": row.created_time.isoformat() if row.created_time else None,
                "updated_time": row.updated_time.isoformat() if row.updated_time else None,
            }
            for row in rows
        ]


agent_task_service = AgentTaskService()
