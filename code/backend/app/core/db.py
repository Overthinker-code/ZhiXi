from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlmodel import SQLModel, Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    Assignment,
    Course,
    CoursePlan,
    TC,
    Teacher,
    UD,
    User,
    UserCreate,
)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

DEMO_UD_ID = UUID("b0000001-0000-4000-8000-000000000001")
DEMO_TEACHER_ID = UUID("b0000002-0000-4000-8000-000000000001")
DEMO_TC_ID = UUID("d0000001-0000-4000-8000-000000000001")
DEMO_STUDENT_EMAIL = "syudent@example.com"
DEMO_STUDENT_ALIASES = ("student@example.com",)
DEMO_STUDENT_PASSWORD = "student123456"
DEMO_COURSE_SPECS: list[tuple[UUID, str, str, str, str]] = [
    (
        UUID("c1111111-1111-4111-9111-111111111101"),
        "数据库系统",
        "CS-DB-001",
        "关系模型、SQL、事务与存储，配套实验与案例。",
        "专业核心",
    ),
    (
        UUID("c1111111-1111-4111-9111-111111111102"),
        "数据结构",
        "CS-DS-001",
        "线性表、树、图与常用算法，注重动手实现。",
        "专业核心",
    ),
    (
        UUID("c1111111-1111-4111-9111-111111111103"),
        "人工智能导论",
        "CS-AI-001",
        "搜索、机器学习与深度学习入门。",
        "专业选修",
    ),
    (
        UUID("c1111111-1111-4111-9111-111111111104"),
        "宏观经济学",
        "EC-MAC-001",
        "国民收入、货币与财政政策分析。",
        "专业核心",
    ),
    (
        UUID("c1111111-1111-4111-9111-111111111105"),
        "审计学",
        "AC-AUD-001",
        "审计准则、风险评估与内部控制。",
        "专业核心",
    ),
    (
        UUID("c1111111-1111-4111-9111-111111111106"),
        "金融学",
        "FI-FIN-001",
        "金融市场、资产定价与公司金融基础。",
        "专业核心",
    ),
]

DEMO_COURSE_OUTLINES: dict[UUID, list[tuple[str, list[str]]]] = {
    DEMO_COURSE_SPECS[0][0]: [
        ("关系数据模型", ["数据模型与关系模型", "关系代数", "SQL 基础"]),
        ("完整性与约束", ["实体完整性", "参照完整性", "用户定义完整性"]),
        ("事务与并发控制", ["事务与原子性", "可串行化", "死锁处理"]),
        ("规范化与恢复", ["函数依赖", "范式与 BCNF", "日志与检查点"]),
    ],
    DEMO_COURSE_SPECS[1][0]: [
        ("线性结构", ["顺序表", "链表", "栈与队列"]),
        ("树结构", ["二叉树遍历", "堆与优先队列", "平衡搜索树"]),
        ("图结构", ["图的存储", "深度与广度搜索", "最短路径"]),
        ("排序与查找", ["快速排序", "归并排序", "哈希查找"]),
    ],
    DEMO_COURSE_SPECS[2][0]: [
        ("智能与搜索", ["人工智能概览", "状态空间搜索", "启发式搜索"]),
        ("知识与推理", ["知识表示", "逻辑推理", "概率推理"]),
        ("机器学习", ["监督学习", "无监督学习", "模型评估"]),
        ("神经网络", ["感知机", "反向传播", "深度学习应用"]),
    ],
    DEMO_COURSE_SPECS[3][0]: [
        ("国民收入核算", ["GDP 核算", "价格指数", "收入与支出循环"]),
        ("短期经济波动", ["总需求", "总供给", "乘数效应"]),
        ("宏观政策", ["财政政策", "货币政策", "政策组合"]),
        ("长期增长", ["资本积累", "技术进步", "开放经济"]),
    ],
    DEMO_COURSE_SPECS[4][0]: [
        ("审计基础", ["审计目标", "职业道德", "审计准则"]),
        ("风险评估", ["重大错报风险", "了解被审计单位", "风险应对"]),
        ("内部控制", ["控制环境", "控制测试", "实质性程序"]),
        ("审计报告", ["审计证据", "审计意见", "关键审计事项"]),
    ],
    DEMO_COURSE_SPECS[5][0]: [
        ("金融体系", ["金融市场", "金融机构", "利率与货币"]),
        ("资产定价", ["风险与收益", "债券定价", "股票估值"]),
        ("公司金融", ["资本预算", "资本结构", "股利政策"]),
        ("风险管理", ["衍生工具", "投资组合", "金融监管"]),
    ],
}


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def seed_education_demo(session: Session) -> None:
    """幂等补齐六门演示课程、教学班、课程计划与作业。"""

    ud = session.get(UD, DEMO_UD_ID)
    if not ud:
        ud = UD(
            id=DEMO_UD_ID,
            university="演示大学",
            department="计算机学院",
        )
        session.add(ud)
        session.commit()
        session.refresh(ud)

    teacher = session.get(Teacher, DEMO_TEACHER_ID)
    if not teacher:
        teacher = Teacher(
            id=DEMO_TEACHER_ID,
            name="演示教师",
            identifier="DEMO-T001",
            ud_id=DEMO_UD_ID,
        )
        session.add(teacher)
        session.commit()
        session.refresh(teacher)

    for cid, name, identifier, description, course_type in DEMO_COURSE_SPECS:
        course = session.get(Course, cid)
        if not course:
            course = Course(
                id=cid,
                name=name,
                description=description,
                course_type=course_type,
                identifier=identifier,
                ud_id=DEMO_UD_ID,
            )
            session.add(course)
        else:
            course.name = name
            course.identifier = identifier
            course.description = description
            course.course_type = course_type
            session.add(course)
    session.commit()

    now = datetime(2026, 6, 15, 9, 0, 0)
    for course_index, (course_id, course_name, *_rest) in enumerate(
        DEMO_COURSE_SPECS
    ):
        tc_id = (
            DEMO_TC_ID
            if course_index == 0
            else uuid5(NAMESPACE_URL, f"zhixi:tc:{course_id}")
        )
        tc = session.get(TC, tc_id)
        if not tc:
            tc = session.exec(
                select(TC).where(TC.course_id == course_id).limit(1)
            ).first()
        if not tc:
            tc = TC(
                id=tc_id,
                name=f"{course_name}·2026春",
                course_id=course_id,
                lecturer_id=DEMO_TEACHER_ID,
            )
            session.add(tc)
            session.flush()
        elif not tc.name or tc.name == "春季教学班":
            tc.name = f"{course_name}·2026春"
            session.add(tc)

        outline = DEMO_COURSE_OUTLINES[course_id]
        lesson_rows = [
            (chapter_title, lesson_title)
            for chapter_title, lessons in outline
            for lesson_title in lessons
        ]
        for week, (chapter_title, lesson_title) in enumerate(lesson_rows, start=1):
            plan = session.exec(
                select(CoursePlan).where(
                    CoursePlan.tc_id == tc.id,
                    CoursePlan.week == week,
                )
            ).first()
            if plan:
                plan.goal = chapter_title
                plan.key_point = lesson_title
                session.add(plan)
                continue
            session.add(
                CoursePlan(
                    id=uuid5(NAMESPACE_URL, f"zhixi:plan:{course_id}:{week}"),
                    tc_id=tc.id,
                    week=week,
                    goal=chapter_title,
                    key_point=lesson_title,
                )
            )

        for assignment_index, (chapter_title, lessons) in enumerate(
            outline[:3], start=1
        ):
            assignment_id = uuid5(
                NAMESPACE_URL,
                f"zhixi:assignment:{course_id}:{assignment_index}",
            )
            assignment = session.get(Assignment, assignment_id)
            title = f"{chapter_title}综合任务"
            description = (
                f"完成{chapter_title}相关概念梳理，并围绕"
                f"{'、'.join(lessons[:2])}提交练习与反思。"
            )
            if assignment:
                assignment.title = title
                assignment.description = description
                assignment.due_date = now + timedelta(days=assignment_index * 7)
                session.add(assignment)
                continue
            session.add(
                Assignment(
                    id=assignment_id,
                    course_id=course_id,
                    title=title,
                    description=description,
                    due_date=now + timedelta(days=assignment_index * 7),
                )
            )
    session.commit()


def ensure_demo_student_links(session: Session) -> None:
    """Link demo login users to education Student rows when present."""
    from sqlalchemy import inspect

    from app.models import Student

    try:
        cols = {c["name"] for c in inspect(session.bind).get_columns("student")}
    except Exception:
        return
    if "user_id" not in cols:
        return

    for email in (DEMO_STUDENT_EMAIL, *DEMO_STUDENT_ALIASES):
        user = session.exec(select(User).where(User.email == email)).first()
        if not user:
            continue
        student = session.exec(select(Student).where(Student.user_id == user.id)).first()
        if student:
            continue
        student = session.exec(select(Student).limit(1)).first()
        if student and not student.user_id:
            student.user_id = user.id
            session.add(student)
    session.commit()


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # No Alembic revisions are present in this project, so create tables directly.
    SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            username=settings.FIRST_SUPERUSER.split("@")[0],
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)
    else:
        if not verify_password(settings.FIRST_SUPERUSER_PASSWORD, user.hashed_password):
            user.hashed_password = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
        user.username = user.username or settings.FIRST_SUPERUSER.split("@")[0]
        user.is_superuser = True
        session.add(user)
        session.commit()

    for student_email in (DEMO_STUDENT_EMAIL, *DEMO_STUDENT_ALIASES):
        student = session.exec(
            select(User).where(User.email == student_email)
        ).first()
        if not student:
            student_in = UserCreate(
                email=student_email,
                password=DEMO_STUDENT_PASSWORD,
                username="student",
                is_superuser=False,
            )
            crud.create_user(session=session, user_create=student_in)
        else:
            if not verify_password(DEMO_STUDENT_PASSWORD, student.hashed_password):
                student.hashed_password = get_password_hash(DEMO_STUDENT_PASSWORD)
            student.username = "student"
            student.is_superuser = False
            student.is_active = True
            session.add(student)
            session.commit()

    seed_education_demo(session)
    ensure_demo_student_links(session)
