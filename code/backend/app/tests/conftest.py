from collections.abc import Generator
import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine, init_db
from app.main import app
from app.models import (
    CourseKnowledgeEdge,
    CourseKnowledgeNodeAction,
    LearningEvidence,
    LearningPathUpdateEvent,
    ProfileUpdateEvent,
    ResourceGenerationRun,
    ResourceGenerationStep,
    ResourceKnowledgeLink,
)
from app.tests.utils.user import authentication_token_from_email
from app.tests.utils.utils import get_superuser_token_headers


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    if os.getenv("ZHIXI_SKIP_DB_TEST_FIXTURE") == "1":
        yield None  # type: ignore[misc]
        return
    with Session(engine) as session:
        init_db(session)
        yield session
        session.rollback()


def _clear_resource_run_state(session: Session) -> None:
    """Remove run-scoped rows so a failed test cannot block the next test."""
    session.rollback()
    session.exec(delete(ResourceKnowledgeLink))
    session.exec(delete(CourseKnowledgeNodeAction))
    session.exec(delete(CourseKnowledgeEdge).where(CourseKnowledgeEdge.run_id.is_not(None)))
    session.exec(delete(ProfileUpdateEvent))
    session.exec(delete(LearningPathUpdateEvent))
    session.exec(delete(LearningEvidence).where(LearningEvidence.run_id.is_not(None)))
    session.exec(delete(ResourceGenerationStep))
    session.exec(delete(ResourceGenerationRun))
    session.commit()


@pytest.fixture(autouse=True)
def isolate_resource_runs(db: Session | None) -> Generator[None, None, None]:
    """Guarantee that active ResourceRun records never cross test boundaries."""
    if db is None:
        yield
        return
    _clear_resource_run_state(db)
    try:
        yield
    finally:
        _clear_resource_run_state(db)


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
