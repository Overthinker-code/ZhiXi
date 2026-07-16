from __future__ import annotations

from collections.abc import Generator
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.v1.endpoints import alerts
from app.core.config import settings
from app.models import Student, StudentTC, TC, User


@pytest.fixture
def alert_class_scope(db: Session) -> Generator[tuple[User, TC, TC], None, None]:
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    own_class = db.exec(select(TC).order_by(TC.created_at)).first()
    assert own_class is not None
    student = db.exec(select(Student).where(Student.user_id == user.id)).first()
    created_student = student is None
    if student is None:
        student = Student(
            name="告警授权测试学生",
            identifier=f"ALERT-{str(user.id)[:8]}",
            ud_id=own_class.course.ud_id,
            user_id=user.id,
        )
        db.add(student)
        db.flush([student])
    own_relation = db.exec(
        select(StudentTC).where(
            StudentTC.student_id == student.id,
            StudentTC.tc_id == own_class.id,
        )
    ).first()
    created_relation = own_relation is None
    if own_relation is None:
        own_relation = StudentTC(student_id=student.id, tc_id=own_class.id)
        db.add(own_relation)
    other_class = TC(
        id=uuid4(),
        name="未授权平行教学班",
        course_id=own_class.course_id,
        lecturer_id=own_class.lecturer_id,
    )
    db.add(other_class)
    db.commit()
    try:
        yield user, own_class, other_class
    finally:
        db.delete(other_class)
        if created_relation:
            db.delete(own_relation)
        if created_student:
            db.delete(student)
        db.commit()


def test_alert_history_requires_exact_teaching_class_membership(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    alert_class_scope: tuple[User, TC, TC],
) -> None:
    _user, own_class, other_class = alert_class_scope

    own = client.get(
        f"{settings.API_V1_STR}/alerts/history",
        headers=normal_user_token_headers,
        params={"tc_id": str(own_class.id), "limit": 1},
    )
    cross_class = client.get(
        f"{settings.API_V1_STR}/alerts/history",
        headers=normal_user_token_headers,
        params={"tc_id": str(other_class.id), "limit": 1},
    )
    missing = client.get(
        f"{settings.API_V1_STR}/alerts/history",
        headers=normal_user_token_headers,
        params={"tc_id": str(uuid4()), "limit": 1},
    )

    assert own.status_code == 200
    assert cross_class.status_code == 403
    assert cross_class.json()["detail"] == "Teaching class access denied"
    assert missing.status_code == 404


def test_alert_stream_prefers_authorization_header_over_query_token(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
    alert_class_scope: tuple[User, TC, TC],
) -> None:
    _user, _own_class, other_class = alert_class_scope
    superuser_query_token = superuser_token_headers["Authorization"].removeprefix(
        "Bearer "
    )

    response = client.get(
        f"{settings.API_V1_STR}/alerts/stream",
        headers=normal_user_token_headers,
        params={"tc_id": str(other_class.id), "token": superuser_query_token},
    )

    # The lower-privilege header identity wins; a query token cannot override
    # it to cross a teaching-class boundary.
    assert response.status_code == 403


def test_alert_stream_query_token_is_deprecated_but_still_authorized(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    alert_class_scope: tuple[User, TC, TC],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, own_class, _other_class = alert_class_scope
    query_token = normal_user_token_headers["Authorization"].removeprefix("Bearer ")

    async def one_event(tc_id: UUID, current_user: User):
        assert tc_id == own_class.id
        assert current_user.id == user.id
        yield 'data: {"status":"ok"}\n\n'

    monkeypatch.setattr(alerts, "event_generator", one_event)
    response = client.get(
        f"{settings.API_V1_STR}/alerts/stream",
        params={"tc_id": str(own_class.id), "token": query_token},
    )

    assert response.status_code == 200
    assert response.headers["deprecation"] == "true"
    assert "Query token authentication is deprecated" in response.headers["warning"]
    assert 'data: {"status":"ok"}' in response.text
