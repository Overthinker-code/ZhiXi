from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.learning_task import LearningTask
from app.models.chat import Chat
from app.models.chat_thread import ChatThread


class LearningTaskService:
    _TASK_HINTS = ("学习任务", "学习计划", "设置任务", "创建任务", "制定任务")

    @staticmethod
    def _record_task_signal(
        db: Session,
        *,
        user_id: str,
        task: LearningTask,
        event_type: str,
    ) -> None:
        try:
            uid = UUID(user_id)
        except (TypeError, ValueError):
            return
        from app.services.learning_report_service import learning_report_service

        learning_report_service.record_evidence(
            db,
            user_id=uid,
            knowledge_point=task.title,
            source_type="learning_task",
            source_id=f"{task.id}:{task.updated_at.isoformat() if task.updated_at else event_type}",
            event_type=event_type,
            weight=0.3,
            score=None,
            payload={
                "task_execution": {
                    "task_id": task.id,
                    "goal": task.goal,
                    "progress": task.progress,
                    "status": task.status,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                }
            },
        )

    def extract_task(self, message: str, *, now: datetime | None = None) -> dict | None:
        text = re.sub(r"\s+", "", message or "").strip("，。！？ ")
        if not text:
            return None
        has_deadline_goal = bool(re.search(r"(?:前|之前|截止).{0,8}完成|完成.{0,30}学习", text))
        if not any(hint in text for hint in self._TASK_HINTS) and not has_deadline_goal:
            return None

        current = now or datetime.now().astimezone()
        deadline = self._extract_deadline(text, current)
        topic = self._extract_topic(text)
        if not topic:
            return None

        title = topic if topic.endswith(("学习", "复习", "练习")) else f"{topic}学习"
        deadline_label = deadline.strftime("%Y年%m月%d日") if deadline else "未设置截止日期"
        return {
            "title": title[:200],
            "goal": f"在{deadline_label}前完成{topic}的学习" if deadline else text[:500],
            "deadline": deadline,
            "current_stage": "任务已创建",
            "progress": 0,
        }

    def _extract_deadline(self, text: str, now: datetime) -> datetime | None:
        if "明天" in text:
            target = now + timedelta(days=1)
            return target.replace(hour=23, minute=59, second=59, microsecond=0)
        if "今天" in text:
            return now.replace(hour=23, minute=59, second=59, microsecond=0)
        match = re.search(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日?", text)
        if not match:
            match = re.search(r"(?:(\d{4})[./-])?(\d{1,2})[./-](\d{1,2})", text)
        if not match:
            return None
        year = int(match.group(1)) if match.group(1) else now.year
        month = int(match.group(2))
        day = int(match.group(3))
        try:
            candidate = datetime(year, month, day, 23, 59, 59, tzinfo=now.tzinfo or timezone.utc)
        except ValueError:
            return None
        if not match.group(1) and candidate.date() < now.date():
            candidate = candidate.replace(year=year + 1)
        return candidate

    @staticmethod
    def _extract_topic(text: str) -> str:
        # Prefer explicit replacement/edit expressions before the generic
        # patterns below. This avoids titles such as "换成学习黑盒白盒学习".
        direct = re.search(
            r"(?:学习任务|学习计划|当前任务|任务)"
            r"(?:换成|改成|改为|修改为|调整为|变更为|设置为|设为|是|为|：|:)"
            r"(.+?)(?:[，。！？]|$)",
            text,
        )
        if direct:
            topic = direct.group(1)
            topic = re.sub(r"^(?:换成|改成|改为|修改为|设置为|设为)", "", topic)
            topic = re.sub(r"^(?:学习|复习|掌握)", "", topic)
            topic = re.sub(r"(?:的)?学习$", "", topic)
            topic = topic.strip("，。：:的 ")
            if topic and len(topic) <= 100:
                return topic
        patterns = (
            r"完成(.+?)(?:的学习|学习)(?:任务|计划)?(?:[，。！？]|$)",
            r"(?:学习任务|学习计划)(?:是|为|：|:)?(.+?)(?:[，。！？]|$)",
            r"(?:学习|掌握)(.+?)(?:，|。|！|？|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            topic = match.group(1)
            topic = re.sub(r"^(?:在|到|截止).*?(?:前|之前)", "", topic)
            topic = re.sub(r"(?:的)?学习$", "", topic)
            topic = topic.strip("，。：:的 ")
            if topic and len(topic) <= 100:
                return topic
        return ""

    def update_current(
        self,
        db: Session,
        *,
        user_id: str,
        changes: dict,
    ) -> LearningTask | None:
        task = self.get_current(db, user_id=user_id)
        if not task:
            return None
        if "title" in changes and changes["title"] is not None:
            title = str(changes["title"]).strip()
            if title:
                task.title = title[:200]
        if "goal" in changes and changes["goal"] is not None:
            task.goal = str(changes["goal"]).strip()[:500]
        if "deadline" in changes:
            task.deadline = changes["deadline"]
        db.add(task)
        db.flush([task])
        self._record_task_signal(
            db, user_id=user_id, task=task, event_type="task_updated"
        )
        db.commit()
        db.refresh(task)
        return task

    def upsert_from_message(
        self,
        db: Session,
        *,
        user_id: str,
        session_id: str,
        message: str,
    ) -> LearningTask | None:
        parsed = self.extract_task(message)
        if not parsed:
            return None
        db.execute(
            update(LearningTask)
            .where(LearningTask.user_id == user_id, LearningTask.status == "active")
            .values(status="replaced")
        )
        task = LearningTask(
            user_id=user_id,
            session_id=session_id,
            status="active",
            **parsed,
        )
        db.add(task)
        db.flush([task])
        self._record_task_signal(
            db, user_id=user_id, task=task, event_type="task_created"
        )
        db.commit()
        db.refresh(task)
        return task

    def get_current(self, db: Session, *, user_id: str) -> LearningTask | None:
        statement = (
            select(LearningTask)
            .where(LearningTask.user_id == user_id, LearningTask.status == "active")
            .order_by(LearningTask.id.desc())
            .limit(1)
        )
        task = db.scalars(statement).first()
        if task:
            parsed = self.extract_task(task.goal)
            expected = parsed.get("deadline") if parsed else None
            changed = False
            malformed_title = any(
                marker in task.title
                for marker in ("换成", "改成", "改为", "修改为", "设置为", "设为")
            )
            if parsed and parsed.get("title") and malformed_title:
                task.title = parsed["title"]
                changed = True
            if (
                task.deadline
                and expected
                and task.deadline.astimezone(expected.tzinfo).date() != expected.date()
            ):
                task.deadline = expected
                changed = True
            if changed:
                db.add(task)
                db.commit()
                db.refresh(task)
        return task

    def recover_from_recent_history(
        self, db: Session, *, user_id: str, limit: int = 20
    ) -> LearningTask | None:
        """Backfill a task instruction sent before task persistence was available."""
        statement = (
            select(Chat, ChatThread.thread_id)
            .join(ChatThread, ChatThread.thread_id == Chat.thread_id)
            .where(ChatThread.user_id == user_id)
            .order_by(Chat.id.desc())
            .limit(limit)
        )
        for chat, session_id in db.execute(statement).all():
            if self.extract_task(chat.user_input or ""):
                return self.upsert_from_message(
                    db,
                    user_id=user_id,
                    session_id=session_id,
                    message=chat.user_input or "",
                )
        return None

    @staticmethod
    def public_payload(task: LearningTask) -> dict:
        return {
            "id": task.id,
            "title": task.title,
            "goal": task.goal,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "current_stage": task.current_stage,
            "progress": task.progress,
            "status": task.status,
            "session_id": task.session_id,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


learning_task_service = LearningTaskService()
