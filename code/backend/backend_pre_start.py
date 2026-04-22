import logging

from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.sql.expression import SelectOfScalar

from app.core.config import settings

# Fix forward references
SelectOfScalar.inherit_cache = True  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init() -> None:
    # 支持 SQLite 和 PostgreSQL
    connect_args = {}
    if settings.SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
        connect_args = {"check_same_thread": False}
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI, connect_args=connect_args)
    # Make sure all SQLModel models are imported before initializing the DB
    # otherwise, SQLModel might fail to initialize relationships properly
    from app.models import (
        User,
        Message,
        Log,
        HelpDocument,
        UD,
        Teacher,
        Course,
        TC,
        CoursePlan,
        Student,
        StudentTC,
        Video,
    )

    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created")

    # 检查是否需要创建初始超级用户
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        if not users:
            # Initialize database data will be created by initial_data.py
            logger.info("No users found, creating initial data")


def main() -> None:
    logger.info("Initializing service")
    init()
    logger.info("Service finished initializing")


if __name__ == "__main__":
    main()
