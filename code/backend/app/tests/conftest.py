from collections.abc import Generator
import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import Item, User
from app.tests.utils.user import authentication_token_from_email
from app.tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    if os.getenv("ZHIXI_SKIP_DB_TEST_FIXTURE") == "1":
        yield None  # type: ignore[misc]
        return
    with Session(engine) as session:
        init_db(session)
        baseline_item_ids = set(session.exec(select(Item.id)).all())
        baseline_user_ids = set(session.exec(select(User.id)).all())
        yield session
        session.rollback()
        item_cleanup = delete(Item)
        if baseline_item_ids:
            item_cleanup = item_cleanup.where(Item.id.not_in(baseline_item_ids))
        session.execute(item_cleanup)
        user_cleanup = delete(User)
        if baseline_user_ids:
            user_cleanup = user_cleanup.where(User.id.not_in(baseline_user_ids))
        session.execute(user_cleanup)
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def superuser_token_headers(client: TestClient) -> dict[str, str]:
    return get_superuser_token_headers(client)


@pytest.fixture(scope="module")
def normal_user_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client, email=settings.EMAIL_TEST_USER, db=db
    )
