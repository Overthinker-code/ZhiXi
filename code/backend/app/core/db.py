from uuid import UUID

from sqlmodel import SQLModel, Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import Course, TC, Teacher, UD, User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

DEMO_UD_ID = UUID("b0000001-0000-4000-8000-000000000001")
DEMO_TEACHER_ID = UUID("b0000002-0000-4000-8000-000000000001")
DEMO_TC_ID = UUID("d0000001-0000-4000-8000-000000000001")
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


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def seed_education_demo(session: Session) -> None:
    """空库时写入演示院系/教师/课程/教学班，与前端 demo 兜底 id 一致。"""
    if session.exec(select(Course)).first() is not None:
        return

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

    first_course_id = DEMO_COURSE_SPECS[0][0]
    for cid, name, identifier, description, course_type in DEMO_COURSE_SPECS:
        if session.get(Course, cid):
            continue
        session.add(
            Course(
                id=cid,
                name=name,
                description=description,
                course_type=course_type,
                identifier=identifier,
                ud_id=DEMO_UD_ID,
            )
        )
    session.commit()

    if session.get(TC, DEMO_TC_ID) is None:
        session.add(
            TC(
                id=DEMO_TC_ID,
                name="春季教学班",
                course_id=first_course_id,
                lecturer_id=DEMO_TEACHER_ID,
            )
        )
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

    seed_education_demo(session)
