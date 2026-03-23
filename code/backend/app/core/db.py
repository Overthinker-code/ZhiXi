from sqlmodel import SQLModel, Session, create_engine, select

from app import crud
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import User, UserCreate

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


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
