#!/usr/bin/env python3
"""Seed an evidence-backed, presentation-ready learner profile.

The dataset is additive and idempotent. It does not remove real chat, quiz or
wrong-question history; stable source IDs make repeated runs safe.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlmodel import Session, select

from app.core.db import DEMO_TEACHER_ID, DEMO_UD_ID, engine
from app.models import Course, CoursePlan, Resource, Student, TC, User
from app.models.quiz import QuizAttempt
from app.models.resource_run import CourseKnowledgeNode
from app.models.user_memory_profile import UserMemoryProfile
from app.services.knowledge_graph_service import ensure_course_graph
from app.services.learning_report_service import learning_report_service
from app.services.student_profile_agent import student_profile_agent


DATASET = "rich_profile_demo_v1"
SOFTWARE_ENGINEERING_ID = UUID("c1111111-1111-4111-9111-111111111107")
COURSE_IDS = {
    "数据库系统": UUID("c1111111-1111-4111-9111-111111111101"),
    "数据结构": UUID("c1111111-1111-4111-9111-111111111102"),
    "人工智能导论": UUID("c1111111-1111-4111-9111-111111111103"),
    "软件工程导论": SOFTWARE_ENGINEERING_ID,
}

SOFTWARE_OUTLINE = [
    ("软件工程基础", "软件生命周期"),
    ("软件工程基础", "开发过程模型"),
    ("软件工程基础", "可行性分析"),
    ("需求分析与建模", "需求分析"),
    ("需求分析与建模", "数据流图 DFD"),
    ("需求分析与建模", "用例建模"),
    ("软件设计", "模块化设计"),
    ("软件设计", "内聚与耦合"),
    ("软件测试与维护", "黑盒与白盒测试"),
    ("软件测试与维护", "软件维护"),
    ("软件测试与维护", "配置管理"),
]

# Old and recent observations form a real longitudinal series. Recent scores
# improve without becoming unrealistically perfect.
ASSESSMENTS = {
    "数据库系统": [
        ("SQL 基础", 0.58, 0.84),
        ("事务与原子性", 0.52, 0.78),
        ("可串行化", 0.48, 0.70),
        ("函数依赖", 0.61, 0.82),
        ("范式与 BCNF", 0.55, 0.74),
    ],
    "数据结构": [
        ("链表", 0.62, 0.86),
        ("二叉树遍历", 0.57, 0.80),
        ("深度与广度搜索", 0.50, 0.72),
        ("最短路径", 0.46, 0.68),
        ("快速排序", 0.64, 0.83),
    ],
    "人工智能导论": [
        ("状态空间搜索", 0.53, 0.76),
        ("启发式搜索", 0.47, 0.69),
        ("知识表示", 0.59, 0.79),
        ("监督学习", 0.55, 0.73),
        ("模型评估", 0.49, 0.71),
    ],
    "软件工程导论": [
        ("软件生命周期", 0.60, 0.86),
        ("需求分析", 0.55, 0.80),
        ("数据流图 DFD", 0.43, 0.66),
        ("内聚与耦合", 0.51, 0.74),
        ("黑盒与白盒测试", 0.57, 0.79),
    ],
}

SOURCE_TYPES = ("quiz", "assignment", "exercise_grading", "exam", "teacher_assessment")
OLD_AGES = (82, 70, 58, 46, 35)
RECENT_AGES = (29, 24, 18, 11, 4)

PROFILE_MEMORY = {
    "current_goal": "系统掌握软件工程分析与设计，并提升计算机核心课程综合应用能力",
    "learning_goal": "完成软件工程导论知识闭环，能够独立完成需求分析、DFD、模块设计和测试方案",
    "learning_style": "图解、案例与分步练习结合",
    "cognitive_style": "视觉化理解与实践验证并重",
    "weak_points": ["数据流图分层与平衡", "最短路径算法迁移", "启发式搜索策略选择"],
    "strengths": ["持续主动提问", "案例分析", "练习后反思", "跨课程知识关联"],
    "knowledge_state": {
        "软件工程.软件生命周期": 0.86,
        "软件工程.需求分析": 0.80,
        "软件工程.数据流图 DFD": 0.66,
        "软件工程.内聚与耦合": 0.74,
        "软件工程.软件测试": 0.79,
        "数据库.SQL 基础": 0.84,
        "数据库.事务与并发": 0.76,
        "数据结构.树与图": 0.78,
        "数据结构.算法设计": 0.72,
        "人工智能.搜索与推理": 0.70,
        "人工智能.机器学习基础": 0.74,
    },
    "mastery_map": {
        "软件工程.软件生命周期": 0.86,
        "软件工程.需求分析": 0.80,
        "软件工程.数据流图 DFD": 0.66,
        "软件工程.内聚与耦合": 0.74,
        "软件工程.软件测试": 0.79,
        "数据库.SQL 基础": 0.84,
        "数据库.事务与并发": 0.76,
        "数据结构.树与图": 0.78,
        "数据结构.算法设计": 0.72,
        "人工智能.搜索与推理": 0.70,
        "人工智能.机器学习基础": 0.74,
    },
    "learning_preference": {
        "visual_preference": 0.88,
        "step_by_step_preference": 0.90,
        "example_preference": 0.84,
        "practice_preference": 0.80,
        "document_preference": 0.72,
        "video_preference": 0.65,
    },
    "resource_preference": {
        "图解与思维导图": 0.88,
        "案例讲解": 0.84,
        "专项练习": 0.80,
        "课程文档": 0.72,
        "教学视频": 0.65,
    },
    "learning_rhythm": "工作日下午与晚间保持稳定学习，周末适合完成综合实践",
    "self_regulation": {
        "planning": 0.82,
        "completion": 0.86,
        "reflection": 0.78,
        "persistence": 0.88,
    },
    "interest_topics": ["软件工程", "系统建模", "人工智能", "计算机网络", "数据结构"],
    "profile_demo_dataset": DATASET,
}


def ensure_software_course(session: Session) -> Course:
    course = session.get(Course, SOFTWARE_ENGINEERING_ID)
    if not course:
        course = Course(
            id=SOFTWARE_ENGINEERING_ID,
            name="软件工程导论",
            identifier="CS-SE-001",
            description="软件生命周期、需求分析、系统建模、设计、测试与维护。",
            course_type="专业核心",
            ud_id=DEMO_UD_ID,
        )
        session.add(course)
        session.flush()
    tc_id = uuid5(NAMESPACE_URL, f"zhixi:tc:{SOFTWARE_ENGINEERING_ID}")
    tc = session.get(TC, tc_id)
    if not tc:
        tc = TC(
            id=tc_id,
            name="软件工程导论·2026春",
            course_id=course.id,
            lecturer_id=DEMO_TEACHER_ID,
        )
        session.add(tc)
        session.flush()
    for week, (chapter, point) in enumerate(SOFTWARE_OUTLINE, start=1):
        plan_id = uuid5(NAMESPACE_URL, f"zhixi:plan:{SOFTWARE_ENGINEERING_ID}:{week}")
        plan = session.get(CoursePlan, plan_id)
        if not plan:
            session.add(CoursePlan(id=plan_id, tc_id=tc.id, week=week, goal=chapter, key_point=point))
    session.commit()
    return course


def curriculum_nodes(session: Session, course_id: UUID) -> dict[str, CourseKnowledgeNode]:
    ensure_course_graph(session, course_id=course_id)
    rows = session.exec(
        select(CourseKnowledgeNode).where(
            CourseKnowledgeNode.course_id == course_id,
            CourseKnowledgeNode.map_type == "knowledge",
            CourseKnowledgeNode.node_type == "concept",
        )
    ).all()
    return {row.label: row for row in rows}


def seed_assessment_evidence(session: Session, user: User) -> int:
    now = datetime.now(timezone.utc)
    added = 0
    for course_name, entries in ASSESSMENTS.items():
        course_id = COURSE_IDS[course_name]
        nodes = curriculum_nodes(session, course_id)
        for index, (label, old_score, recent_score) in enumerate(entries):
            node = nodes.get(label)
            if not node:
                raise SystemExit(f"Missing curriculum node: {course_name} / {label}")
            source_type = SOURCE_TYPES[index % len(SOURCE_TYPES)]
            for period, age, score in (
                ("baseline", OLD_AGES[index], old_score),
                ("recent", RECENT_AGES[index], recent_score),
            ):
                source_id = f"{DATASET}:{course_id}:{index}:{period}"
                before = session.exec(
                    select(CourseKnowledgeNode).where(CourseKnowledgeNode.id == node.id)
                ).first()
                evidence = learning_report_service.record_evidence(
                    session,
                    user_id=user.id,
                    course_id=course_id,
                    knowledge_point=label,
                    knowledge_point_id=str((before or node).id),
                    source_type=source_type,
                    source_id=source_id,
                    event_type="assessment_completed",
                    observed_at=now - timedelta(days=age, hours=(index * 3) % 12),
                    score=score,
                    weight=2.8 if period == "recent" else 0.8,
                    payload={
                        "dataset": DATASET,
                        "scored": True,
                        "task_type": "project" if source_type in {"assignment", "teacher_assessment"} else "application",
                        "task_execution": {
                            "planned": True,
                            "completion_rate": min(1.0, score + 0.10),
                            "reflection_submitted": period == "recent",
                        },
                    },
                )
                # record_evidence is intentionally idempotent and returns an
                # existing row on repeat runs. Refresh the pedagogical weight
                # as well so dataset revisions remain reproducible.
                evidence.weight = 2.8 if period == "recent" else 0.8
                session.add(evidence)
                added += 1
    session.commit()
    return added


def seed_improvement_attempts(session: Session, user: User) -> int:
    resource = session.exec(
        select(Resource).where(
            Resource.uploader_id == user.id,
            Resource.title.contains("软件工程导论"),
        )
    ).first()
    if not resource:
        raise SystemExit("Software engineering quiz resource not found for target user")
    resource.course_id = SOFTWARE_ENGINEERING_ID
    resource.subject = "软件工程导论"
    resource.knowledge_point = "软件工程导论"
    session.add(resource)
    existing = session.exec(
        select(QuizAttempt).where(QuizAttempt.user_id == user.id)
    ).all()
    seeded = {
        str((item.answers or {}).get("demo_attempt"))
        for item in existing
        if (item.answers or {}).get("dataset") == DATASET
    }
    scores = (7, 8, 8, 9, 8, 9, 9, 9)
    now = datetime.now(timezone.utc)
    for index, correct in enumerate(scores, start=1):
        marker = str(index)
        if marker in seeded:
            continue
        wrong = (
            ["数据流图分层与平衡", "模块耦合判定"]
            if correct <= 7
            else ["数据流图分层与平衡"]
            if correct == 8
            else []
        )
        session.add(
            QuizAttempt(
                user_id=user.id,
                resource_id=resource.id,
                answers={"dataset": DATASET, "demo_attempt": marker},
                total_questions=10,
                correct_count=correct,
                score=correct / 10,
                wrong_knowledge_points=wrong,
                created_time=now - timedelta(days=max(1, 25 - index * 3)),
            )
        )
    session.commit()
    return len(scores) - len(seeded.intersection({str(i) for i in range(1, 9)}))


def enrich_memory_profile(session: Session, user: User) -> None:
    row = session.exec(select(UserMemoryProfile).where(UserMemoryProfile.user_id == user.id)).first()
    if row:
        row.memory_profile = {**(row.memory_profile or {}), **PROFILE_MEMORY}
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = UserMemoryProfile(user_id=user.id, memory_profile=dict(PROFILE_MEMORY))
    session.add(row)
    session.commit()


def seed(email: str) -> None:
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            raise SystemExit(f"User not found: {email}")
        student = session.exec(select(Student).where(Student.user_id == user.id)).first()
        if not student:
            raise SystemExit(f"Student linkage not found: {email}")
        ensure_software_course(session)
        evidence_count = seed_assessment_evidence(session, user)
        attempt_count = seed_improvement_attempts(session, user)
        enrich_memory_profile(session, user)
        profile = student_profile_agent.synchronize(session, user.id)
        analytics = learning_report_service.build_portrait_analytics(session, user.id)
        print({
            "email": email,
            "dataset": DATASET,
            "evidence_processed": evidence_count,
            "new_quiz_attempts": attempt_count,
            "digital_twin_score": (profile.learning_behavior or {}).get("overall_score"),
            "profile_version": profile.profile_version,
            "analytics_overall": analytics.overall_score,
            "growth_30d": analytics.growth_30d,
            "engagement": analytics.engagement,
            "courses": [item.name for item in analytics.courses],
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a rich learner profile")
    parser.add_argument("--email", default="student@example.com")
    args = parser.parse_args()
    seed(args.email)


if __name__ == "__main__":
    main()
