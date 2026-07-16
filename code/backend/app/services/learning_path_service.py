from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.models.learning_path import LearningPath
from app.models.learning_evidence import LearningPathUpdateEvent
from app.schemas.learning_path import LearningPathNodePublic, LearningPathPublic
from app.schemas.learning_report import LearningReport


class LearningPathService:
    def update_from_resource_run(
        self,
        session: Session,
        *,
        user_id: UUID,
        course_id: UUID | None,
        run_id: str,
        subject: str,
        topic: str,
        package_id: str,
    ) -> LearningPathUpdateEvent:
        record = session.exec(
            select(LearningPath).where(LearningPath.user_id == user_id)
        ).first()
        before_nodes = list(record.nodes or []) if record else []
        nodes = [dict(node) for node in before_nodes if isinstance(node, dict)]
        normalized_topic = topic.strip()
        if not any(str(node.get("topic") or "").strip() == normalized_topic for node in nodes):
            nodes.append(
                {
                    "title": f"学习并核验 {normalized_topic}",
                    "status": "pending",
                    "order": len(nodes),
                    "topic": normalized_topic,
                    "action": f"使用资源包 {package_id} 完成学习、练习和证据核验",
                    "source_run_id": run_id,
                }
            )
        if record:
            record.subject = subject[:80]
            record.summary = f"已根据资源生成运行 {run_id} 更新学习路径"[:500]
            record.nodes = nodes
            record.updated_at = datetime.now(timezone.utc)
        else:
            record = LearningPath(
                user_id=user_id,
                subject=subject[:80],
                summary=f"已根据资源生成运行 {run_id} 创建学习路径"[:500],
                nodes=nodes,
            )
        session.add(record)
        session.flush([record])
        event = LearningPathUpdateEvent(
            run_id=run_id,
            user_id=user_id,
            course_id=course_id,
            learning_path_id=record.id,
            status="completed",
            before_state={"nodes": before_nodes},
            after_state={"nodes": nodes},
            summary=f"新增或保留知识点“{normalized_topic}”的资源学习节点",
        )
        session.add(event)
        session.flush([event])
        return event
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
