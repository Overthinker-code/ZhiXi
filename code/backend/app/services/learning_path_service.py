from __future__ import annotations

from datetime import datetime

from sqlmodel import Session, select

from app.models.learning_path import LearningPath
from app.schemas.learning_path import LearningPathNodePublic, LearningPathPublic
from app.schemas.learning_report import LearningReport


class LearningPathService:
    def upsert_from_report(
        self,
        session: Session,
        user_id: str,
        report: LearningReport,
        *,
        subject: str = "数据库系统",
    ) -> LearningPathPublic:
        from uuid import UUID

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        nodes: list[dict] = []
        order = 0
        for topic in (report.weak_points or [])[:4]:
            nodes.append(
                {
                    "title": f"巩固 {topic}",
                    "status": "in_progress" if order == 0 else "pending",
                    "order": order,
                    "topic": topic,
                    "action": "伴学追问 + 针对性练习",
                }
            )
            order += 1
        for action in (report.recommended_actions or [])[:3]:
            nodes.append(
                {
                    "title": action[:40],
                    "status": "pending",
                    "order": order,
                    "topic": "",
                    "action": action,
                }
            )
            order += 1
        if not nodes:
            nodes = [
                {
                    "title": "完成学情诊断",
                    "status": "in_progress",
                    "order": 0,
                    "topic": "",
                    "action": "建立学习基线",
                },
                {
                    "title": "伴学中心对话",
                    "status": "pending",
                    "order": 1,
                    "topic": "",
                    "action": "积累学习画像",
                },
            ]

        summary = report.summary or "个性化学习路径"
        existing = session.exec(
            select(LearningPath).where(LearningPath.user_id == uid)
        ).first()
        if existing:
            existing.subject = subject
            existing.summary = summary[:500]
            existing.nodes = nodes
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            record = existing
        else:
            record = LearningPath(
                user_id=uid,
                subject=subject,
                summary=summary[:500],
                nodes=nodes,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
        return self.to_public(record, user_id)

    def get_for_user(self, session: Session, user_id: str) -> LearningPathPublic | None:
        from uuid import UUID

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        record = session.exec(
            select(LearningPath).where(LearningPath.user_id == uid)
        ).first()
        if not record:
            return None
        return self.to_public(record, user_id)

    def to_public(self, record: LearningPath, user_id: str) -> LearningPathPublic:
        return LearningPathPublic(
            user_id=user_id,
            subject=record.subject or "",
            summary=record.summary or "",
            nodes=[
                LearningPathNodePublic(**node)
                for node in (record.nodes or [])
                if isinstance(node, dict)
            ],
            updated_at=record.updated_at.isoformat() if record.updated_at else "",
        )


learning_path_service = LearningPathService()
