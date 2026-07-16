from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes import digital_human as digital_human_routes
from app.api.routes import videos as video_routes
from app.core.config import settings
from app.models import Course, Student, StudentTC, TC, User, Video
from app.services.digital_human_service import digital_human_service


@pytest.fixture
def video_access_scope(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Generator[tuple[User, Video, Video], None, None]:
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    superuser = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    own_class = db.exec(select(TC).order_by(TC.created_at)).first()
    assert superuser is not None and own_class is not None
    course = db.get(Course, own_class.course_id)
    assert course is not None

    student = db.exec(select(Student).where(Student.user_id == user.id)).first()
    created_student = student is None
    if student is None:
        student = Student(
            name="视频授权测试学生",
            identifier=f"VIDEO-{str(user.id)[:8]}",
            ud_id=course.ud_id,
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
        name="视频授权测试未加入班级",
        course_id=own_class.course_id,
        lecturer_id=own_class.lecturer_id,
    )
    db.add(other_class)
    db.flush([other_class])

    own_video = Video(
        title="已授权课程视频",
        file_path="videos/own.mp4",
        file_name="own.mp4",
        file_size=9,
        content_type="video/mp4",
        tc_id=own_class.id,
        uploader_id=superuser.id,
        week=1,
    )
    other_video = Video(
        title="未授权课程视频",
        file_path="videos/other.mp4",
        file_name="other.mp4",
        file_size=10,
        content_type="video/mp4",
        tc_id=other_class.id,
        uploader_id=superuser.id,
        week=1,
    )
    db.add(own_video)
    db.add(other_video)
    db.commit()
    db.refresh(own_video)
    db.refresh(other_video)

    upload_dir = tmp_path / "videos"
    upload_dir.mkdir()
    (upload_dir / "own.mp4").write_bytes(b"own-video")
    (upload_dir / "other.mp4").write_bytes(b"other-video")
    monkeypatch.setattr(video_routes, "UPLOAD_DIR", str(upload_dir))

    try:
        yield user, own_video, other_video
    finally:
        db.delete(own_video)
        db.delete(other_video)
        db.delete(other_class)
        if created_relation:
            db.delete(own_relation)
        if created_student:
            db.delete(student)
        db.commit()


def test_video_list_detail_and_download_are_teaching_class_scoped(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    video_access_scope: tuple[User, Video, Video],
) -> None:
    _user, own_video, other_video = video_access_scope
    base = f"{settings.API_V1_STR}/education/videos"

    listing = client.get(f"{base}/", headers=normal_user_token_headers)
    own = client.get(f"{base}/{own_video.id}", headers=normal_user_token_headers)
    own_download = client.get(
        f"{base}/{own_video.id}/download", headers=normal_user_token_headers
    )
    cross_class = client.get(
        f"{base}/{other_video.id}", headers=normal_user_token_headers
    )
    cross_download = client.get(
        f"{base}/{other_video.id}/download", headers=normal_user_token_headers
    )
    missing = client.get(f"{base}/{uuid4()}", headers=normal_user_token_headers)

    assert listing.status_code == 200
    listed_ids = {item["id"] for item in listing.json()["data"]}
    assert str(own_video.id) in listed_ids
    assert str(other_video.id) not in listed_ids
    assert own.status_code == 200
    assert own_download.status_code == 200
    assert own_download.content == b"own-video"
    assert cross_class.status_code == cross_download.status_code == 404
    assert cross_class.json() == missing.json() == {"detail": "未找到指定的视频"}


@pytest.fixture
def digital_human_access_scope(
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[User, UUID, UUID]:
    user = db.exec(select(User).where(User.email == settings.EMAIL_TEST_USER)).one()
    superuser = db.exec(select(User).where(User.is_superuser.is_(True))).first()
    assert superuser is not None
    input_dir = tmp_path / "digital-input"
    output_dir = tmp_path / "digital-output"
    input_dir.mkdir()
    output_dir.mkdir()
    monkeypatch.setattr(settings, "DIGITAL_HUMAN_INPUT_DIR", str(input_dir))
    monkeypatch.setattr(settings, "DIGITAL_HUMAN_OUTPUT_DIR", str(output_dir))

    own_task_id = uuid4()
    other_task_id = uuid4()
    digital_human_service._register_job_owner(
        task_id=str(own_task_id), owner_id=user.id
    )
    digital_human_service._register_job_owner(
        task_id=str(other_task_id), owner_id=superuser.id
    )
    for task_id, title in (
        (own_task_id, "我的数字人作品"),
        (other_task_id, "他人的数字人作品"),
    ):
        (output_dir / f"{task_id}.mp4").write_bytes(f"video-{task_id}".encode())
        (output_dir / f"{task_id}_script.json").write_text(
            json.dumps(
                {
                    "title": title,
                    "narration": f"{title}的讲解内容",
                    "source_kind": "text",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return user, own_task_id, other_task_id


def test_digital_human_works_and_media_are_owner_scoped_with_signed_playback(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    digital_human_access_scope: tuple[User, UUID, UUID],
) -> None:
    _user, own_task_id, other_task_id = digital_human_access_scope
    base = f"{settings.API_V1_STR}/digital-human"

    works_response = client.get(f"{base}/works", headers=normal_user_token_headers)
    assert works_response.status_code == 200
    works = works_response.json()["works"]
    assert [work["id"] for work in works] == [str(own_task_id)]

    own_auth = client.get(
        f"{base}/media/{own_task_id}.mp4", headers=normal_user_token_headers
    )
    cross_owner = client.get(
        f"{base}/media/{other_task_id}.mp4", headers=normal_user_token_headers
    )
    missing = client.get(
        f"{base}/media/{uuid4()}.mp4", headers=normal_user_token_headers
    )
    raw_unauthenticated = client.get(f"{base}/media/{own_task_id}.mp4")
    signed_playback = client.get(works[0]["video_url"])
    signed_script = client.get(works[0]["script_url"])

    assert own_auth.status_code == 200
    assert signed_playback.status_code == 200
    assert signed_script.status_code == 200
    assert "no-store" in signed_playback.headers["cache-control"]
    assert signed_playback.headers["referrer-policy"]
    assert cross_owner.status_code == missing.status_code == 404
    assert cross_owner.json() == missing.json() == {
        "detail": "未找到数字人作品"
    }
    assert raw_unauthenticated.status_code == 404

    stolen_ticket = works[0]["video_url"].split("ticket=", 1)[1]
    tampered = client.get(
        f"{base}/media/{other_task_id}.mp4?ticket={stolen_ticket}"
    )
    assert tampered.status_code == 404


def test_digital_human_job_status_hides_cross_owner_and_unknown_tasks(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    digital_human_access_scope: tuple[User, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _user, own_task_id, other_task_id = digital_human_access_scope
    base = f"{settings.API_V1_STR}/digital-human/jobs"

    class FakeResult:
        state = "SUCCESS"
        result = {
            "status": "success",
            "progress": 100,
            "message": "渲染完成",
            "stage": "done",
        }
        info = None

    monkeypatch.setattr(digital_human_routes, "AsyncResult", lambda *_args, **_kwargs: FakeResult())
    monkeypatch.setattr(digital_human_routes, "celery", SimpleNamespace())
    monkeypatch.setattr(digital_human_routes, "celery_enabled", lambda: True)

    own = client.get(f"{base}/{own_task_id}", headers=normal_user_token_headers)
    cross_owner = client.get(
        f"{base}/{other_task_id}", headers=normal_user_token_headers
    )
    missing = client.get(f"{base}/{uuid4()}", headers=normal_user_token_headers)

    assert own.status_code == 200
    assert own.json()["status"] == "success"
    assert "ticket=" in own.json()["video_url"]
    assert cross_owner.status_code == missing.status_code == 404
    assert cross_owner.json() == missing.json() == {
        "detail": "未找到数字人任务"
    }


def test_text_job_creation_binds_authenticated_owner_server_side(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    digital_human_access_scope: tuple[User, UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, _own_task_id, _other_task_id = digital_human_access_scope
    captured: dict[str, object] = {}

    def fake_create_text_job(**kwargs):
        captured.update(kwargs)
        return {"task_id": str(uuid4()), "status": "pending", "message": "ok"}

    monkeypatch.setattr(
        digital_human_service, "create_text_job", fake_create_text_job
    )
    response = client.post(
        f"{settings.API_V1_STR}/digital-human/jobs/text-to-video",
        headers=normal_user_token_headers,
        json={"text": "讲解数据库事务"},
    )

    assert response.status_code == 200
    assert captured["owner_id"] == user.id
    assert captured["text"] == "讲解数据库事务"
