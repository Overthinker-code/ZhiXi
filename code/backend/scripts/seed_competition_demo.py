#!/usr/bin/env python3
"""Competition-scale demo seed: courses, students, behavior, chats, profiles."""

from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app import crud
from app.core.db import (
    DEMO_COURSE_SPECS,
    DEMO_STUDENT_ALIASES,
    DEMO_STUDENT_EMAIL,
    DEMO_STUDENT_PASSWORD,
    DEMO_TC_ID,
    DEMO_TEACHER_ID,
    DEMO_UD_ID,
    engine,
)
from app.models import (
    Assignment,
    BehaviorSummaryRecord,
    Course,
    CoursePlan,
    Resource,
    Student,
    StudentTC,
    Submission,
    TC,
    Teacher,
    UD,
    User,
    Video,
)
from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.models.learning_path import LearningPath
from app.schemas.user import UserCreate
from app.models.user_memory_profile import UserMemoryProfile

EXTRA_COURSES: list[tuple[str, str, str, str]] = [
    ("操作系统", "CS-OS-001", "进程、内存、文件系统与并发控制。", "专业核心"),
    ("计算机网络", "CS-NET-001", "TCP/IP、路由与网络安全基础。", "专业核心"),
    ("软件工程", "CS-SE-001", "需求、设计模式与敏捷开发。", "专业核心"),
    ("编译原理", "CS-CP-001", "词法、语法分析与代码生成。", "专业选修"),
    ("机器学习", "CS-ML-001", "监督学习、集成方法与模型评估。", "专业选修"),
    ("深度学习", "CS-DL-001", "CNN、RNN、Transformer 与应用。", "专业选修"),
    ("计算机组成原理", "CS-CO-001", "指令集、流水线与存储层次。", "专业核心"),
    ("Web 全栈开发", "CS-WEB-001", "前后端分离、REST 与部署。", "专业选修"),
    ("云计算基础", "CS-CLOUD-001", "虚拟化、容器与微服务入门。", "专业选修"),
    ("自然语言处理", "CS-NLP-001", "分词、序列标注与大模型应用。", "专业选修"),
]

CHAT_TOPICS = [
    ("B+树分裂条件是什么？", "节点满时分裂并上推中间键；删除导致低于最小填充因子时合并。"),
    ("事务隔离级别有哪些？", "读未提交、读已提交、可重复读、串行化。"),
    ("索引失效的常见场景？", "函数包裹列、隐式转换、前导模糊、OR 非索引列等。"),
    ("CNN 与 RNN 的区别？", "CNN 擅空间特征，RNN 擅序列依赖；Transformer 用自注意力。"),
    ("TCP 三次握手过程？", "SYN → SYN-ACK → ACK，建立可靠连接。"),
]

PROFILE_TEMPLATE = {
    "current_goal": "掌握数据库与 AI 核心课程",
    "learning_style": "分步讲解 + 例题练习",
    "weak_points": ["索引优化", "B+树", "事务隔离", "梯度消失"],
    "mastery_map": {
        "索引基础": 0.72,
        "B+树结构": 0.58,
        "事务与并发": 0.65,
        "SQL 优化": 0.48,
        "机器学习基础": 0.55,
    },
    "strengths": ["主动提问", "完成练习意愿强"],
}


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def ensure_ud_teacher(session: Session) -> tuple[UD, Teacher]:
    ud = session.get(UD, DEMO_UD_ID)
    if not ud:
        ud = UD(id=DEMO_UD_ID, university="演示大学", department="计算机学院")
        session.add(ud)
        session.flush()
    teacher = session.get(Teacher, DEMO_TEACHER_ID)
    if not teacher:
        teacher = Teacher(
            id=DEMO_TEACHER_ID,
            name="演示教师",
            identifier="DEMO-T001",
            ud_id=DEMO_UD_ID,
        )
        session.add(teacher)
        session.flush()
    return ud, teacher


def seed_courses(session: Session) -> list[Course]:
    ensure_ud_teacher(session)
    courses: list[Course] = []
    for cid, name, identifier, description, course_type in DEMO_COURSE_SPECS:
        row = session.get(Course, cid)
        if not row:
            row = Course(
                id=cid,
                name=name,
                description=description,
                course_type=course_type,
                identifier=identifier,
                ud_id=DEMO_UD_ID,
            )
            session.add(row)
        courses.append(row)
    for name, identifier, description, course_type in EXTRA_COURSES:
        existing = session.exec(
            select(Course).where(Course.identifier == identifier)
        ).first()
        if existing:
            courses.append(existing)
            continue
        row = Course(
            id=uuid.uuid4(),
            name=name,
            description=description,
            course_type=course_type,
            identifier=identifier,
            ud_id=DEMO_UD_ID,
        )
        session.add(row)
        courses.append(row)
    session.commit()
    return list(session.exec(select(Course)).all())


def seed_teaching_classes(session: Session, courses: list[Course]) -> list[TC]:
    tcs: list[TC] = []
    for i, course in enumerate(courses[:10]):
        tc = session.exec(
            select(TC).where(TC.course_id == course.id).limit(1)
        ).first()
        if not tc:
            tc_id = DEMO_TC_ID if i == 0 else uuid.uuid4()
            tc = TC(
                id=tc_id,
                name=f"{course.name}·2026春",
                course_id=course.id,
                lecturer_id=DEMO_TEACHER_ID,
            )
            session.add(tc)
        tcs.append(tc)
    session.commit()
    return tcs


def ensure_demo_user(session: Session, email: str, username: str) -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user:
        return user
    user = crud.create_user(
        session=session,
        user_create=UserCreate(
            email=email,
            password=DEMO_STUDENT_PASSWORD,
            username=username,
            is_superuser=False,
        ),
    )
    return user


def seed_students(session: Session, count: int = 120) -> list[Student]:
    ensure_ud_teacher(session)
    students: list[Student] = []
    demo_emails = [DEMO_STUDENT_EMAIL, *DEMO_STUDENT_ALIASES]
    for idx, email in enumerate(demo_emails):
        user = ensure_demo_user(session, email, "student" if idx == 0 else f"student{idx}")
        st = session.exec(select(Student).where(Student.user_id == user.id)).first()
        if not st:
            st = session.exec(
                select(Student).where(Student.identifier == f"DEMO-S{idx+1:03d}")
            ).first()
        if not st:
            st = Student(
                id=uuid.uuid4(),
                name=f"演示学生{idx+1}",
                identifier=f"DEMO-S{idx+1:03d}",
                ud_id=DEMO_UD_ID,
                user_id=user.id,
            )
            session.add(st)
        else:
            st.user_id = user.id
            session.add(st)
        students.append(st)

    existing = session.exec(select(Student)).all()
    start = len(students)
    for i in range(start, count):
        ident = f"STU-{i+1:04d}"
        if session.exec(select(Student).where(Student.identifier == ident)).first():
            continue
        students.append(
            Student(
                id=uuid.uuid4(),
                name=f"学生{i+1}",
                identifier=ident,
                ud_id=DEMO_UD_ID,
            )
        )
        session.add(students[-1])
    session.commit()
    return list(session.exec(select(Student)).all())


def seed_enrollments(session: Session, students: list[Student], tcs: list[TC]) -> None:
    rng = _rng(42)
    for student in students:
        picks = rng.sample(tcs, k=min(rng.randint(2, 4), len(tcs)))
        for tc in picks:
            exists = session.exec(
                select(StudentTC).where(
                    StudentTC.student_id == student.id,
                    StudentTC.tc_id == tc.id,
                )
            ).first()
            if exists:
                continue
            session.add(StudentTC(student_id=student.id, tc_id=tc.id))
    session.commit()


def seed_course_content(session: Session, tcs: list[TC], admin_id: uuid.UUID) -> None:
    rng = _rng(7)
    for tc in tcs:
        for week in range(1, 9):
            title = f"第{week}周 · {tc.name}"
            if not session.exec(
                select(Video).where(Video.tc_id == tc.id, Video.title == title).limit(1)
            ).first():
                session.add(
                    Video(
                        id=uuid.uuid4(),
                        title=title,
                        file_path=f"/media/videos/{tc.id}/week{week}.mp4",
                        file_name=f"week{week}.mp4",
                        file_size=rng.randint(8_000_000, 40_000_000),
                        content_type="video/mp4",
                        week=week,
                        tc_id=tc.id,
                        uploader_id=admin_id,
                    )
                )
            res_title = f"讲义 · 第{week}周"
            if not session.exec(
                select(Resource).where(
                    Resource.course_id == tc.course_id,
                    Resource.title == res_title,
                ).limit(1)
            ).first():
                session.add(
                    Resource(
                        id=uuid.uuid4(),
                        title=res_title,
                        type="pdf",
                        file_path=f"/media/docs/{tc.id}/week{week}.pdf",
                        file_name=f"week{week}.pdf",
                        file_size=rng.randint(200_000, 2_000_000),
                        content_type="application/pdf",
                        course_id=tc.course_id,
                        uploader_id=admin_id,
                    )
                )
        for w in range(1, 17):
            if session.exec(
                select(CoursePlan).where(CoursePlan.tc_id == tc.id, CoursePlan.week == w).limit(1)
            ).first():
                continue
            session.add(
                CoursePlan(
                    id=uuid.uuid4(),
                    tc_id=tc.id,
                    week=w,
                    goal=f"第{w}周学习目标",
                    key_point=f"第{w}周重点与实验",
                )
            )
    session.commit()


def seed_assignments(session: Session, tcs: list[TC], students: list[Student]) -> None:
    rng = _rng(11)
    for tc in tcs[:6]:
        for n in range(1, 4):
            title = f"{tc.name} · 作业{n}"
            assignment = session.exec(
                select(Assignment).where(
                    Assignment.course_id == tc.course_id,
                    Assignment.title == title,
                )
            ).first()
            if not assignment:
                assignment = Assignment(
                    id=uuid.uuid4(),
                    title=title,
                    description="完成本章练习题并提交代码/报告",
                    course_id=tc.course_id,
                    due_date=datetime.now(timezone.utc) + timedelta(days=7 * n),
                )
                session.add(assignment)
                session.flush()
            enrolled = session.exec(
                select(StudentTC.student_id).where(StudentTC.tc_id == tc.id)
            ).all()
            for sid in enrolled[:40]:
                if session.exec(
                    select(Submission).where(
                        Submission.assignment_id == assignment.id,
                        Submission.student_id == sid,
                    )
                ).first():
                    continue
                if rng.random() < 0.75:
                    session.add(
                        Submission(
                            id=uuid.uuid4(),
                            assignment_id=assignment.id,
                            student_id=sid,
                            file_path=f"/submissions/{assignment.id}/{sid}.pdf",
                            score=float(rng.randint(60, 98)),
                            submit_time=datetime.now(timezone.utc)
                            - timedelta(days=rng.randint(0, 5)),
                        )
                    )
    session.commit()


def seed_behavior(session: Session, students: list[Student], tcs: list[TC], days: int = 30) -> None:
    rng = _rng(19)
    now = datetime.now(timezone.utc)
    for day_offset in range(days):
        day = now - timedelta(days=day_offset)
        for tc in tcs[:8]:
            for student in rng.sample(students, k=min(15, len(students))):
                if session.exec(
                    select(BehaviorSummaryRecord).where(
                        BehaviorSummaryRecord.student_id == student.id,
                        BehaviorSummaryRecord.tc_id == tc.id,
                        BehaviorSummaryRecord.session_date >= day.replace(hour=0, minute=0),
                        BehaviorSummaryRecord.session_date < day.replace(hour=23, minute=59),
                    )
                ).first():
                    continue
                lei = round(rng.uniform(0.45, 0.92), 3)
                session.add(
                    BehaviorSummaryRecord(
                        id=uuid.uuid4(),
                        student_id=student.id,
                        tc_id=tc.id,
                        course_id=tc.course_id,
                        session_date=day,
                        avg_lei=lei,
                        avg_cognitive_depth=round(rng.uniform(0.3, 0.85), 3),
                        mind_wandering_rate=round(max(0.05, 1 - lei + rng.uniform(-0.1, 0.1)), 3),
                        on_task_rate=round(rng.uniform(0.5, 0.95), 3),
                        contagion_index=round(rng.uniform(0.1, 0.6), 3),
                        bloom_distribution=json.dumps(
                            {
                                "remembering": 0.2,
                                "understanding": 0.3,
                                "applying": 0.25,
                                "analyzing": 0.15,
                                "evaluating": 0.07,
                                "creating": 0.03,
                            }
                        ),
                    )
                )
    session.commit()


def seed_learning_for_user(session: Session, user: User) -> None:
    thread = session.exec(
        select(ChatThread).where(ChatThread.user_id == str(user.id)).limit(1)
    ).first()
    if not thread:
        thread = ChatThread(
            thread_id=f"seed_{uuid.uuid4().hex[:12]}",
            user_id=str(user.id),
            title="AI 与数据库学习",
            created_at=datetime.utcnow(),
        )
        session.add(thread)
        session.flush()

    chat_count = session.query(Chat).filter(Chat.thread_id == thread.thread_id).count()
    if chat_count < len(CHAT_TOPICS):
        base = datetime.utcnow() - timedelta(hours=3)
        for i, (q, a) in enumerate(CHAT_TOPICS):
            session.add(
                Chat(
                    thread_id=thread.thread_id,
                    user_input=q,
                    response=a,
                    created_at=base + timedelta(minutes=i * 8),
                )
            )

    profile = session.exec(
        select(UserMemoryProfile).where(UserMemoryProfile.user_id == user.id)
    ).first()
    if not profile:
        session.add(
            UserMemoryProfile(
                user_id=user.id,
                memory_profile=PROFILE_TEMPLATE,
            )
        )

    path = session.exec(
        select(LearningPath).where(LearningPath.user_id == user.id)
    ).first()
    if not path:
        nodes = [
            {"id": "n1", "title": "巩固索引优化", "status": "active", "order": 1},
            {"id": "n2", "title": "完成 B+树练习", "status": "pending", "order": 2},
            {"id": "n3", "title": "复习事务隔离", "status": "pending", "order": 3},
        ]
        session.add(
            LearningPath(
                user_id=user.id,
                subject="数据库系统",
                summary="基于画像生成的个性化学习路径",
                nodes=nodes,
            )
        )
    session.commit()


def run_seed(*, student_count: int = 120, behavior_days: int = 30) -> dict:
    with Session(engine) as session:
        admin = session.exec(
            select(User).where(User.is_superuser == True)  # noqa: E712
        ).first()
        admin_id = admin.id if admin else uuid.uuid4()
        courses = seed_courses(session)
        tcs = seed_teaching_classes(session, courses)
        students = seed_students(session, count=student_count)
        seed_enrollments(session, students, tcs)
        seed_course_content(session, tcs, admin_id)
        seed_assignments(session, tcs, students)
        seed_behavior(session, students, tcs, days=behavior_days)
        for email in (DEMO_STUDENT_EMAIL, *DEMO_STUDENT_ALIASES):
            user = session.exec(select(User).where(User.email == email)).first()
            if user:
                seed_learning_for_user(session, user)
        return {
            "courses": len(courses),
            "teaching_classes": len(tcs),
            "students": len(students),
            "behavior_days": behavior_days,
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed competition demo data")
    parser.add_argument("--students", type=int, default=120)
    parser.add_argument("--behavior-days", type=int, default=30)
    args = parser.parse_args()
    stats = run_seed(student_count=args.students, behavior_days=args.behavior_days)
    print("Seed complete:", stats)


if __name__ == "__main__":
    main()
