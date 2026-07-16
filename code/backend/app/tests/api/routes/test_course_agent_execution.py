from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.v1.endpoints import ai_chat
from app.core.config import settings
from app.models import Course, Student, StudentTC, TC, User


COURSE_ID = "c1111111-1111-4111-9111-111111111101"


@pytest.fixture(scope="module", autouse=True)
def enroll_test_student(db: Session):
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).first()
    course_id = UUID(COURSE_ID)
    course = db.get(Course, course_id)
    tc = db.exec(select(TC).where(TC.course_id == course_id)).first()
    assert user is not None and course is not None and tc is not None
    student = db.exec(select(Student).where(Student.user_id == user.id)).first()
    created_student = student is None
    if student is None:
        student = Student(
            name="课程Agent接口测试学生",
            identifier=f"AGENT-{str(user.id)[:8]}",
            ud_id=course.ud_id,
            user_id=user.id,
        )
        db.add(student)
        db.flush([student])
    relation = db.exec(
        select(StudentTC).where(
            StudentTC.student_id == student.id,
            StudentTC.tc_id == tc.id,
        )
    ).first()
    created_relation = relation is None
    if relation is None:
        relation = StudentTC(student_id=student.id, tc_id=tc.id)
        db.add(relation)
    db.commit()
    try:
        yield
    finally:
        if created_relation:
            db.delete(relation)
        if created_student:
            db.delete(student)
        db.commit()


def _payload(agent_key: str, mode: str) -> dict[str, Any]:
    return {
        "message": "请完成一次课程智能体契约验证",
        "mode": mode,
        "agentKey": agent_key,
        "courseContext": {
            "courseId": COURSE_ID,
            "knowledgePointIds": [],
            "useCourseRag": True,
        },
        "tools": {
            "webSearch": True,
            "courseRag": True,
            "deepResearch": True,
            "homeworkReview": True,
            "resourceGeneration": True,
            "citationRequired": True,
        },
        "reasoning": {"level": "balanced", "showSummary": True, "showProcess": True},
        "attachments": [],
        "resourceRequest": {"types": [], "difficulty": "normal", "target": ""},
    }


@pytest.mark.parametrize(
    ("agent_key", "client_mode", "expected_mode", "expected_worker", "expected_tools"),
    [
        (
            "research",
            "tutor",
            "deep_research",
            "web_research_agent",
            {"knowledge_base", "web_search"},
        ),
        ("practice", "deep_research", "tutor", "quiz_master", {"knowledge_base"}),
        ("reader", "homework_review", "tutor", "doc_researcher", {"knowledge_base"}),
    ],
)
def test_three_specialized_agents_execute_with_server_owned_contracts(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    agent_key: str,
    client_mode: str,
    expected_mode: str,
    expected_worker: str,
    expected_tools: set[str],
) -> None:
    captured = []

    def fake_stream(request):
        captured.append(request)
        yield {"type": "token", "content": f"{agent_key} 已执行"}
        yield {
            "type": "final",
            "content": f"{agent_key} 已执行",
            "agent": expected_worker,
            "citations": [],
            "suggestions": [],
            "metrics": {},
        }

    monkeypatch.setattr(ai_chat, "stream_chat_events", fake_stream)
    response = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=normal_user_token_headers,
        json=_payload(agent_key, client_mode),
    )

    assert response.status_code == 200
    assert 'event: agent_contract' in response.text
    assert f'"agentKey": "{agent_key}"' in response.text
    assert response.text.count(f'{agent_key} 已执行') == 1
    assert captured
    request = captured[0]
    assert request.force_agent == expected_worker
    assert set(request.active_tools or []) == expected_tools
    assert request.route_context["mode"] == expected_mode
    assert request.route_context["tools"]["resourceGeneration"] is False
    if agent_key == "practice":
        assert request.route_context["tools"]["webSearch"] is False
        assert request.tool_mode == "chat"


def test_course_agent_catalog_is_course_scoped_and_hides_internal_routing(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    db: Session,
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/ai/course-agents",
        headers=normal_user_token_headers,
        params={"course_id": COURSE_ID},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contextBound"] is True
    course = db.get(Course, UUID(COURSE_ID))
    assert course is not None
    assert payload["courseTitle"] == course.name
    assert {"research", "practice", "reader"}.issubset(
        {item["key"] for item in payload["agents"]}
    )
    assert all("workerAgent" not in item and "instruction" not in item for item in payload["agents"])
    assert all("usage" not in item and "accuracy" not in item for item in payload["agents"])


@pytest.mark.parametrize("agent_key", ["resource", "graph", "arbitrary_frontend_agent"])
def test_chat_stream_rejects_non_chat_or_unknown_agent_keys(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    agent_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This test isolates the endpoint's server-owned Agent contract. Rate-limit
    # behavior is covered independently in tests/security/test_security_controls.py.
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_REQUESTS", 100)
    response = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=normal_user_token_headers,
        json=_payload(agent_key, "tutor"),
    )
    assert response.status_code == 422
