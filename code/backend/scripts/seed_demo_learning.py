#!/usr/bin/env python3
"""Seed demo learning data for答辩/Golden Path 演示."""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlmodel import Session, select

from app.core.db import engine
from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.models.user import User
from app.models.user_memory_profile import UserMemoryProfile
from app.services.knowledge_graph_service import ensure_course_graph
from app.services.learning_report_service import learning_report_service


DEMO_COURSE_ID = UUID("c1111111-1111-4111-9111-111111111101")

# A compact, repeatable assessment ledger for the competition demo.  These are
# scored assessment events, not chat/exposure events, so they are eligible for
# mastery inference. Stable source ids make the seed idempotent.
DEMO_ASSESSMENTS = [
    ("SQL 基础", "quiz", "demo-db-quiz-01", 0.72, 1.0, 18),
    ("SQL 基础", "assignment", "demo-db-lab-01", 0.82, 1.2, 12),
    ("事务与原子性", "quiz", "demo-db-quiz-02", 0.48, 1.0, 15),
    ("事务与原子性", "exercise_grading", "demo-db-practice-02", 0.63, 0.9, 8),
    ("可串行化", "quiz", "demo-db-quiz-03", 0.42, 1.0, 14),
    ("可串行化", "teacher_assessment", "demo-db-oral-03", 0.58, 0.8, 6),
    ("死锁处理", "assignment", "demo-db-lab-03", 0.76, 1.2, 10),
    ("函数依赖", "quiz", "demo-db-quiz-04", 0.67, 1.0, 9),
    ("范式与 BCNF", "exam", "demo-db-unit-test-04", 0.54, 1.4, 5),
    ("日志与检查点", "exercise_grading", "demo-db-practice-04", 0.79, 0.9, 4),
]

# Twelve-week history gives the demo account a genuine longitudinal series.
# Scores increase gradually but remain imperfect, so the chart demonstrates
# change without hard-coding presentation values in the frontend.
DEMO_HISTORY_ASSESSMENTS = [
    ("SQL 基础", "quiz", "demo-db-history-01", 0.42, 0.8, 82),
    ("事务与原子性", "quiz", "demo-db-history-02", 0.45, 0.8, 75),
    ("可串行化", "assignment", "demo-db-history-03", 0.47, 1.0, 68),
    ("函数依赖", "exercise_grading", "demo-db-history-04", 0.51, 0.8, 61),
    ("范式与 BCNF", "exam", "demo-db-history-05", 0.54, 1.1, 54),
    ("死锁处理", "assignment", "demo-db-history-06", 0.58, 1.0, 47),
    ("日志与检查点", "teacher_assessment", "demo-db-history-07", 0.61, 0.9, 40),
    ("SQL 基础", "quiz", "demo-db-history-08", 0.66, 0.9, 33),
    ("事务与原子性", "exercise_grading", "demo-db-history-09", 0.68, 0.9, 27),
]

ALL_DEMO_ASSESSMENTS = DEMO_HISTORY_ASSESSMENTS + DEMO_ASSESSMENTS

DEMO_CHATS = [
    (
        "B+树的分裂和合并条件是什么？",
        "B+树分裂发生在节点满时，通常将中间键上推；合并发生在删除后节点元素低于最小填充因子时。",
    ),
    (
        "事务的 ACID 特性中，隔离级别有哪些？",
        "标准隔离级别包括：读未提交、读已提交、可重复读、串行化。InnoDB 默认可重复读。",
    ),
    (
        "索引失效的常见场景有哪些？",
        "常见场景：对索引列使用函数、隐式类型转换、前导模糊查询、OR 连接非索引列、不符合最左前缀等。",
    ),
    (
        "请给我两道关于索引优化的练习题。",
        "好的。第一题：分析 WHERE YEAR(create_time)=2024 为何可能不走索引。第二题：设计覆盖索引优化分页查询。",
    ),
]

DEMO_PROFILE = {
    "current_goal": "掌握数据库索引优化与 B+ 树原理",
    "learning_style": "偏好分步讲解 + 例题练习",
    "weak_points": ["索引优化", "B+树分裂", "事务隔离级别"],
    "mastery_map": {
        "索引基础": 0.72,
        "B+树结构": 0.58,
        "事务与并发": 0.65,
        "SQL 优化": 0.48,
    },
    "strengths": ["主动提问", "愿意完成练习题"],
}


def seed_for_user(session: Session, email: str) -> None:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise SystemExit(f"User not found: {email}")

    thread_id = f"seed_{uuid.uuid4().hex[:12]}"
    existing_thread = session.exec(
        select(ChatThread).where(ChatThread.user_id == str(user.id)).limit(1)
    ).first()
    if existing_thread:
        thread_id = existing_thread.thread_id
    else:
        session.add(
            ChatThread(
                thread_id=thread_id,
                user_id=str(user.id),
                title="数据库学习对话",
                created_at=datetime.now(timezone.utc),
            )
        )
        session.flush()

    existing_count = len(
        session.exec(select(Chat.id).where(Chat.thread_id == thread_id)).all()
    )
    if existing_count >= len(DEMO_CHATS):
        print(f"Chat history already seeded for {email}")
    else:
        base_time = datetime.now(timezone.utc) - timedelta(hours=2)
        for i, (question, answer) in enumerate(DEMO_CHATS):
            session.add(
                Chat(
                    thread_id=thread_id,
                    user_input=question,
                    response=answer,
                    created_at=base_time + timedelta(minutes=i * 15),
                )
            )
        print(f"Seeded {len(DEMO_CHATS)} chat messages for {email}")

    # Materialize stable graph nodes before binding assessment evidence.  The
    # graph service remains the single source of node identifiers.
    ensure_course_graph(session, course_id=DEMO_COURSE_ID)
    from app.models import CourseKnowledgeNode

    graph_nodes = session.exec(
        select(CourseKnowledgeNode).where(
            CourseKnowledgeNode.course_id == DEMO_COURSE_ID,
            CourseKnowledgeNode.map_type == "knowledge",
        )
    ).all()
    node_by_label = {node.label: node for node in graph_nodes}
    now = datetime.now(timezone.utc)
    evidence_added = 0
    for label, source_type, source_id, score, weight, age_days in ALL_DEMO_ASSESSMENTS:
        node = node_by_label.get(label)
        if node is None:
            raise SystemExit(f"Knowledge node not found for demo assessment: {label}")
        learning_report_service.record_evidence(
            session,
            user_id=user.id,
            course_id=DEMO_COURSE_ID,
            knowledge_point=label,
            knowledge_point_id=str(node.id),
            source_type=source_type,
            source_id=source_id,
            event_type="assessment_completed",
            observed_at=now - timedelta(days=age_days),
            score=score,
            weight=weight,
            payload={
                "dataset": "competition_demo_v1",
                "scored": True,
                "rubric": "0-1 normalized score",
                "task_type": (
                    "project"
                    if source_type in {"assignment", "teacher_assessment"}
                    else "quiz"
                ),
                "task_execution": {
                    "completion_rate": min(1.0, score + 0.12),
                },
            },
        )
        evidence_added += 1
    session.flush()
    evidence_summary = learning_report_service.evidence_confidence(
        session,
        user.id,
        course_id=DEMO_COURSE_ID,
    )

    profile = session.exec(
        select(UserMemoryProfile).where(UserMemoryProfile.user_id == user.id)
    ).first()
    mastery_from_evidence: dict[str, float] = {}
    for label, *_ in ALL_DEMO_ASSESSMENTS:
        node = node_by_label[label]
        canonical = learning_report_service.normalize_knowledge_point(str(node.id))
        estimate = evidence_summary.get(canonical, {}).get("mastery_estimate")
        if estimate is not None:
            mastery_from_evidence[label] = round(float(estimate), 2)
    evidence_backed_profile = {
        **DEMO_PROFILE,
        "mastery_map": mastery_from_evidence,
        "evidence_model": {
            "version": "weighted_beta_v1",
            "course_id": str(DEMO_COURSE_ID),
            "updated_at": now.isoformat(),
            "eligible_assessments": len(ALL_DEMO_ASSESSMENTS),
        },
    }
    if profile:
        profile.memory_profile = {**(profile.memory_profile or {}), **evidence_backed_profile}
        profile.updated_at = datetime.now(timezone.utc)
        session.add(profile)
    else:
        session.add(
            UserMemoryProfile(
                user_id=user.id,
                memory_profile=evidence_backed_profile,
            )
        )
    print(
        f"Seeded evidence-backed memory profile for {email}: "
        f"{evidence_added} idempotent evidence events across {len(mastery_from_evidence)} knowledge points"
    )
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo learning data")
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Target user email (default: admin@example.com)",
    )
    args = parser.parse_args()
    with Session(engine) as session:
        seed_for_user(session, args.email)


if __name__ == "__main__":
    main()
