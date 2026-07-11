from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from app.models import Course, GeneratedResourcePackage, Resource, User
from app.schemas.resource_generation import ResourceGenerationRequest
from app.services.resource_generation_service import resource_generation_service
from app.services.resource_package_service import (
    ResourcePackagePersistenceError,
    resource_package_service,
)


DEMO_COURSE_ID = UUID("c1111111-1111-4111-9111-111111111101")


def _demo_student(db: Session) -> User:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    return user


def _delete_package_rows(db: Session, package_id: str) -> None:
    for resource in db.exec(
        select(Resource).where(Resource.package_id == package_id)
    ).all():
        db.delete(resource)
    db.flush()
    package = db.get(GeneratedResourcePackage, package_id)
    if package:
        db.delete(package)
    db.commit()


def test_course_package_is_persisted_as_owned_resources(
    db: Session,
    tmp_path,
    monkeypatch,
) -> None:
    student = _demo_student(db)
    assert db.get(Course, DEMO_COURSE_ID) is not None
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    monkeypatch.setattr(
        resource_generation_service,
        "_generate_ai_contents",
        lambda *_: ({}, "test"),
    )

    response = resource_package_service.generate(
        db,
        ResourceGenerationRequest(
            course_id=DEMO_COURSE_ID,
            subject="数据库系统原理",
            topic="关系模型",
            resource_types=["lecture_markdown", "practice_markdown"],
        ),
        owner_id=student.id,
    )
    try:
        assert response.persistence_status == "resources_persisted"
        assert len(response.persisted_resource_ids) == 2

        package = db.get(GeneratedResourcePackage, response.package_id)
        assert package is not None
        assert package.user_id == student.id
        assert package.course_id == DEMO_COURSE_ID

        resources = db.exec(
            select(Resource).where(Resource.package_id == response.package_id)
        ).all()
        assert {resource.id for resource in resources} == set(
            response.persisted_resource_ids
        )
        assert all(resource.uploader_id == student.id for resource in resources)
        assert all(resource.course_id == DEMO_COURSE_ID for resource in resources)

        manifest = json.loads(
            (tmp_path / response.package_id / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert manifest["owner_id"] == str(student.id)
        assert manifest["persistence_status"] == "resources_persisted"
        assert set(manifest["persisted_resource_ids"]) == {
            str(item) for item in response.persisted_resource_ids
        }

        recent = resource_package_service.list_recent(
            db,
            owner_id=student.id,
            course_id=DEMO_COURSE_ID,
        )
        assert recent[0]["package_id"] == response.package_id
        assert len(recent[0]["artifacts"]) == 2

        superuser = db.exec(select(User).where(User.is_superuser.is_(True))).first()
        assert superuser is not None
        assert resource_package_service.list_recent(
            db,
            owner_id=superuser.id,
            course_id=DEMO_COURSE_ID,
        ) == []
    finally:
        _delete_package_rows(db, response.package_id)


def test_global_package_persists_metadata_without_course_resource_rows(
    db: Session,
    tmp_path,
    monkeypatch,
) -> None:
    student = _demo_student(db)
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    monkeypatch.setattr(
        resource_generation_service,
        "_generate_ai_contents",
        lambda *_: ({}, "test"),
    )

    response = resource_package_service.generate(
        db,
        ResourceGenerationRequest(
            subject="通用学习",
            topic="论证结构",
            resource_types=["lecture_markdown"],
        ),
        owner_id=student.id,
    )
    try:
        assert response.persistence_status == "package_persisted"
        assert response.persisted_resource_ids == []
        assert db.get(GeneratedResourcePackage, response.package_id) is not None
        assert db.exec(
            select(Resource).where(Resource.package_id == response.package_id)
        ).all() == []
    finally:
        _delete_package_rows(db, response.package_id)


def test_unknown_course_fails_before_creating_files(
    db: Session,
    tmp_path,
    monkeypatch,
) -> None:
    student = _demo_student(db)
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)

    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service.generate(
            db,
            ResourceGenerationRequest(
                course_id=uuid4(),
                subject="不存在的课程",
                topic="无效主题",
                resource_types=["lecture_markdown"],
            ),
            owner_id=student.id,
        )

    assert exc_info.value.code == "COURSE_NOT_FOUND"
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []
