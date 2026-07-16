from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import ai_chat
from app.core.config import settings


def test_upload_binds_document_to_owner_session_and_course(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_response = client.post(
        f"{settings.API_V1_STR}/ai/sessions",
        headers=normal_user_token_headers,
    )
    session_id = session_response.json()["sessionId"]
    current_user = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    ).json()
    written_index: dict[str, object] = {}

    async def fake_process_uploaded_file(*args, **kwargs):
        assert kwargs["owner_id"] == str(current_user["id"])
        assert kwargs["thread_id"] == session_id
        assert kwargs["course_id"] == "c1111111-1111-4111-9111-111111111101"
        return {"file_id": "owned-course-document", "chunks": 1, "preview_snippet": "ACID"}

    monkeypatch.setattr(ai_chat.rag_service, "process_uploaded_file", fake_process_uploaded_file)
    monkeypatch.setattr(
        ai_chat.knowledge_graph_service,
        "can_access_course",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(ai_chat, "_read_attachment_index", lambda: {})
    monkeypatch.setattr(ai_chat, "_write_attachment_index", lambda value: written_index.update(value))

    response = client.post(
        f"{settings.API_V1_STR}/ai/attachments",
        headers=normal_user_token_headers,
        data={
            "session_id": session_id,
            "course_id": "c1111111-1111-4111-9111-111111111101",
            "chapter_id": "ch3",
            "knowledge_point_ids": '["acid"]',
        },
        files={"file": ("notes.txt", b"ACID notes", "text/plain")},
    )

    assert response.status_code == 200
    attachment = response.json()
    assert attachment["ownerId"] == str(current_user["id"])
    assert attachment["sessionId"] == session_id
    assert attachment["courseId"] == "c1111111-1111-4111-9111-111111111101"
    assert attachment["chapterId"] == "ch3"
    assert attachment["knowledgePointIds"] == ["acid"]
    assert written_index["owned-course-document"] == attachment


def test_attachment_metadata_rejects_foreign_owner(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = f"foreign-{uuid4().hex}"
    monkeypatch.setattr(
        ai_chat,
        "_read_attachment_index",
        lambda: {
            file_id: {
                "fileId": file_id,
                "name": "foreign.png",
                "type": "image",
                "ownerId": str(uuid4()),
                "path": "/tmp/foreign.png",
            }
        },
    )

    response = client.get(
        f"{settings.API_V1_STR}/ai/attachments/{file_id}",
        headers=normal_user_token_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment not found"


def test_chat_stream_rejects_foreign_attachment_before_streaming(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_id = f"foreign-stream-{uuid4().hex}"
    session_response = client.post(
        f"{settings.API_V1_STR}/ai/sessions",
        headers=normal_user_token_headers,
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["sessionId"]
    monkeypatch.setattr(
        ai_chat,
        "_read_attachment_index",
        lambda: {
            file_id: {
                "fileId": file_id,
                "name": "foreign.png",
                "type": "image",
                "ownerId": str(uuid4()),
                "path": "/tmp/foreign.png",
                "sessionId": session_id,
                "courseId": "",
            }
        },
    )

    response = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=normal_user_token_headers,
        json={
            "sessionId": session_id,
            "message": "请分析这张图片",
            "attachments": [
                {"fileId": file_id, "type": "image", "name": "foreign.png"}
            ],
        },
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"] == "Attachment not found"


@pytest.mark.parametrize(
    ("metadata_session", "metadata_course", "request_course"),
    [
        ("another-session", "", ""),
        ("owned-session", "c1111111-1111-4111-9111-111111111102", "c1111111-1111-4111-9111-111111111101"),
    ],
)
def test_chat_stream_rejects_attachment_from_another_session_or_course(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    metadata_session: str,
    metadata_course: str,
    request_course: str,
) -> None:
    session_response = client.post(
        f"{settings.API_V1_STR}/ai/sessions",
        headers=normal_user_token_headers,
    )
    session_id = session_response.json()["sessionId"]
    current_user = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    ).json()
    file_id = f"scoped-{uuid4().hex}"
    bound_session = session_id if metadata_session == "owned-session" else metadata_session
    monkeypatch.setattr(
        ai_chat,
        "_read_attachment_index",
        lambda: {
            file_id: {
                "fileId": file_id,
                "name": "notes.pdf",
                "type": "pdf",
                "ownerId": str(current_user["id"]),
                "sessionId": bound_session,
                "courseId": metadata_course,
            }
        },
    )

    course_context = {
        "knowledgePointIds": [],
        "useCourseRag": bool(request_course),
    }
    if request_course:
        course_context["courseId"] = request_course
        monkeypatch.setattr(
            ai_chat.knowledge_graph_service,
            "can_access_course",
            lambda *args, **kwargs: True,
        )
    response = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=normal_user_token_headers,
        json={
            "sessionId": session_id,
            "message": "请阅读附件",
            "courseContext": course_context,
            "attachments": [{"fileId": file_id, "type": "pdf", "name": "notes.pdf"}],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment not found"


def test_chat_stream_does_not_fallback_for_unindexed_document_attachment(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_response = client.post(
        f"{settings.API_V1_STR}/ai/sessions",
        headers=normal_user_token_headers,
    )
    session_id = session_response.json()["sessionId"]
    monkeypatch.setattr(ai_chat, "_read_attachment_index", lambda: {})

    response = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=normal_user_token_headers,
        json={
            "sessionId": session_id,
            "message": "请阅读附件",
            "attachments": [{"fileId": "legacy-unscoped-file", "type": "pdf"}],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment not found"


def test_chat_stream_does_not_replace_an_unknown_client_session(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/ai/chat/stream",
        headers=normal_user_token_headers,
        json={
            "sessionId": f"unknown-{uuid4().hex}",
            "message": "请解释事务原子性",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Chat session not found"
