from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


TEACHER_DASHBOARD_PATHS = [
    "/dashboard/teacher/stats",
    "/dashboard/teacher/alerts-trend",
    "/dashboard/teacher/popular",
    "/dashboard/teacher/content-distribution",
    "/dashboard/teacher/course-engagement/c1111111-1111-4111-9111-111111111101",
    "/dashboard/teacher/student-engagement/c1111111-1111-4111-9111-111111111101",
]


@pytest.mark.parametrize("path", TEACHER_DASHBOARD_PATHS)
def test_student_cannot_read_teacher_dashboard(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    path: str,
) -> None:
    response = client.get(f"{settings.API_V1_STR}{path}", headers=normal_user_token_headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Teacher dashboard access required"


@pytest.mark.parametrize("path", TEACHER_DASHBOARD_PATHS)
def test_superuser_can_read_teacher_dashboard(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    path: str,
) -> None:
    response = client.get(f"{settings.API_V1_STR}{path}", headers=superuser_token_headers)

    assert response.status_code == 200, response.text
