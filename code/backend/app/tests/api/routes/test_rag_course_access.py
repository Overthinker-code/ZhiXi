from fastapi.testclient import TestClient
from types import SimpleNamespace
from uuid import uuid4

from app.core.config import settings
from app.api.v1.endpoints import rag


COURSE_ID = "c1111111-1111-4111-9111-111111111101"


def test_course_rag_query_requires_real_course_access(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
):
    response = client.post(
        f"{settings.API_V1_STR}/rag/query",
        headers=normal_user_token_headers,
        json={"query": "ACID", "course_id": COURSE_ID},
    )

    assert response.status_code == 404


def test_course_rag_query_requires_explicit_course_boundary(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
):
    response = client.post(
        f"{settings.API_V1_STR}/rag/query",
        headers=normal_user_token_headers,
        json={"query": "ACID"},
    )

    assert response.status_code == 422


def test_superuser_can_query_course_rag(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    monkeypatch,
):
    from app.api.v1.endpoints import rag

    monkeypatch.setattr(rag.rag_service, "query_knowledge_base", lambda **_: [])
    response = client.post(
        f"{settings.API_V1_STR}/rag/query",
        headers=superuser_token_headers,
        json={"query": "ACID", "course_id": COURSE_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_rag_admin_role_never_uses_email_allowlist():
    email_only = SimpleNamespace(
        email="admin@example.com", is_superuser=False
    )
    real_admin = SimpleNamespace(
        email="someone@example.com", is_superuser=True
    )

    assert rag._rag_role(email_only) == "user"
    assert rag._rag_role(real_admin) == "admin"


def test_upload_course_binding_rejects_unverified_course(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
):
    response = client.post(
        f"{settings.API_V1_STR}/rag/upload",
        headers=normal_user_token_headers,
        data={"course_id": str(uuid4())},
        files={"file": ("notes.txt", b"ACID transaction notes", "text/plain")},
    )

    assert response.status_code == 404


def test_upload_rejects_orphan_chapter_metadata(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
):
    response = client.post(
        f"{settings.API_V1_STR}/rag/upload",
        headers=normal_user_token_headers,
        data={"chapter_id": "chapter-3"},
        files={"file": ("notes.txt", b"ACID transaction notes", "text/plain")},
    )

    assert response.status_code == 422


def test_preview_commit_rejects_non_uuid_file_id(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
):
    response = client.post(
        f"{settings.API_V1_STR}/rag/upload/commit",
        headers=normal_user_token_headers,
        json={"file_id": "../../outside"},
    )

    assert response.status_code == 422
