from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.models import (
    CourseKnowledgeEdge,
    Course,
    GeneratedResourcePackage,
    LearningEvidence,
    LearningPathUpdateEvent,
    ProfileUpdateEvent,
    Resource,
    ResourceGenerationRun,
    ResourceGenerationStep,
    ResourceKnowledgeLink,
    User,
    UserMemoryProfile,
)
from app.schemas.resource_generation import ResourceGenerationRequest
from app.core.config import settings
from app.tests.utils.user import authentication_token_from_email
from app.services.resource_generation_service import resource_generation_service
from app.services.resource_package_service import (
    ResourcePackagePersistenceError,
    resource_package_service,
)
from app.core.db import engine


DEMO_COURSE_ID = UUID("c1111111-1111-4111-9111-111111111101")


def _demo_student(db: Session) -> User:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    return user


def _delete_package_rows(db: Session, package_id: str) -> None:
    run_ids = db.exec(
        select(ResourceGenerationRun.id).where(ResourceGenerationRun.package_id == package_id)
    ).all()
    if run_ids:
        db.exec(delete(ResourceKnowledgeLink).where(ResourceKnowledgeLink.run_id.in_(run_ids)))
        db.exec(delete(CourseKnowledgeEdge).where(CourseKnowledgeEdge.run_id.in_(run_ids)))
        db.exec(delete(ProfileUpdateEvent).where(ProfileUpdateEvent.run_id.in_(run_ids)))
        db.exec(delete(LearningPathUpdateEvent).where(LearningPathUpdateEvent.run_id.in_(run_ids)))
        db.exec(delete(LearningEvidence).where(LearningEvidence.run_id.in_(run_ids)))
        db.exec(delete(ResourceGenerationStep).where(ResourceGenerationStep.run_id.in_(run_ids)))
    for resource in db.exec(
        select(Resource).where(Resource.package_id == package_id)
    ).all():
        db.delete(resource)
    db.flush()
    package = db.get(GeneratedResourcePackage, package_id)
    if package:
        db.delete(package)
    if run_ids:
        db.exec(delete(ResourceGenerationRun).where(ResourceGenerationRun.id.in_(run_ids)))
    db.commit()


def test_course_package_is_persisted_as_owned_resources(
    db: Session,
    tmp_path,
    monkeypatch,
    client: TestClient,
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
        assert response.run_status == "partial_success"
        assert response.stage_status["linking_graph"] == "completed"
        assert response.stage_status["updating_path"] == "completed"
        assert response.stage_status["updating_profile"] == "completed"
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
        current = next(item for item in recent if item["package_id"] == response.package_id)
        assert len(current["artifacts"]) == 2
        assert {item["resource_id"] for item in current["artifacts"]} == {
            str(resource.id) for resource in resources
        }
        run = resource_package_service.get_run(
            db, run_id=response.run_id, user_id=student.id
        )
        assert run is not None
        assert run.status == "partial_success"
        assert run.package_id == response.package_id
        assert run.result_url == f"/api/v1/resource-generation/packages/{response.package_id}"
        assert {step.step_key for step in run.steps} >= {
            "profiling", "retrieving", "planning", "generating", "reviewing",
            "persisting", "linking_graph", "updating_path", "updating_profile",
        }
        assert all(step.input_digest and step.output_digest for step in run.steps)
        direct = resource_package_service.get_package(
            db,
            package_id=response.package_id,
            user_id=student.id,
        )
        assert direct is not None
        assert direct["run_id"] == response.run_id
        assert direct["artifacts"]
        assert {item["resource_id"] for item in direct["artifacts"]} == {
            str(resource.id) for resource in resources
        }
        api_response = client.get(
            f"{settings.API_V1_STR}/resource-generation/packages/{response.package_id}",
            headers=authentication_token_from_email(
                client=client,
                email=student.email,
                db=db,
            ),
        )
        assert api_response.status_code == 200
        assert {
            item["resource_id"] for item in api_response.json()["artifacts"]
        } == {str(resource.id) for resource in resources}

        superuser = db.exec(select(User).where(User.is_superuser.is_(True))).first()
        assert superuser is not None
        assert resource_package_service.list_recent(
            db,
            owner_id=superuser.id,
            course_id=DEMO_COURSE_ID,
        ) == []
    finally:
        _delete_package_rows(db, response.package_id)


def test_global_package_persists_owned_resource_rows_without_course(
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
        assert response.persistence_status == "resources_persisted"
        assert len(response.persisted_resource_ids) == 1
        assert db.get(GeneratedResourcePackage, response.package_id) is not None
        resources = db.exec(
            select(Resource).where(Resource.package_id == response.package_id)
        ).all()
        assert len(resources) == 1
        assert resources[0].course_id is None
        assert resources[0].knowledge_point == "论证结构"
        assert resources[0].source == "agent"
        assert response.artifacts[0].resource_id == resources[0].id
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


def test_course_permission_is_checked_before_run_or_files(db: Session, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service.generate(
            db,
            ResourceGenerationRequest(
                course_id=DEMO_COURSE_ID,
                subject="数据库系统原理",
                topic="权限测试",
                resource_types=["lecture_markdown"],
            ),
            owner_id=uuid4(),
        )
    assert exc_info.value.code == "COURSE_ACCESS_DENIED"
    assert not tmp_path.exists() or list(tmp_path.iterdir()) == []


def test_graph_failure_returns_partial_success_but_keeps_core_persistence(
    db: Session, tmp_path, monkeypatch
) -> None:
    student = _demo_student(db)
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    monkeypatch.setattr(resource_generation_service, "_generate_ai_contents", lambda *_: ({}, "test"))
    monkeypatch.setattr(
        resource_package_service,
        "_link_graph",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("graph unavailable")),
    )
    response = resource_package_service.generate(
        db,
        ResourceGenerationRequest(
            course_id=DEMO_COURSE_ID,
            subject="数据库系统原理",
            topic="事务恢复",
            resource_types=["lecture_markdown"],
        ),
        owner_id=student.id,
    )
    try:
        assert response.run_status == "partial_success"
        assert response.stage_status["linking_graph"] == "failed"
        assert response.persistence_status == "resources_persisted"
        assert db.get(GeneratedResourcePackage, response.package_id) is not None
        assert db.exec(select(Resource).where(Resource.package_id == response.package_id)).all()
    finally:
        _delete_package_rows(db, response.package_id)


def test_real_profile_query_changes_specialist_runtime_context(db: Session) -> None:
    first = _demo_student(db)
    second = db.exec(select(User).where(User.email == "syudent@example.com")).first()
    assert second is not None
    original: dict[UUID, dict | None] = {}
    runs: list[ResourceGenerationRun] = []
    try:
        for user, goal, weak_point in (
            (first, "补齐事务基础", "事务隔离级别"),
            (second, "准备数据库竞赛", "查询优化"),
        ):
            record = db.exec(
                select(UserMemoryProfile).where(UserMemoryProfile.user_id == user.id)
            ).first()
            original[user.id] = dict(record.memory_profile) if record and record.memory_profile else None
            if not record:
                record = UserMemoryProfile(user_id=user.id)
            record.memory_profile = {
                "current_goal": goal,
                "learning_style": "示例驱动",
                "weak_points": [weak_point],
                "mastery_map": {weak_point: 0.42},
            }
            db.add(record)
        db.commit()
        contexts = []
        for user in (first, second):
            request = ResourceGenerationRequest(subject="数据库系统", topic="事务 ACID")
            run = resource_package_service._start_run(db, request, user.id)
            runs.append(run)
            contexts.append(resource_package_service._load_runtime_context(db, run, request))

        assert contexts[0]["profile_summary"] != contexts[1]["profile_summary"]
        assert "事务隔离级别" in contexts[0]["profile_summary"]
        assert "查询优化" in contexts[1]["profile_summary"]
        assert resource_generation_service._build_context(
            ResourceGenerationRequest(subject="数据库系统", topic="事务 ACID"),
            runtime_context=contexts[0],
        )["profile"] != resource_generation_service._build_context(
            ResourceGenerationRequest(subject="数据库系统", topic="事务 ACID"),
            runtime_context=contexts[1],
        )["profile"]
    finally:
        for run in runs:
            db.exec(delete(ResourceGenerationStep).where(ResourceGenerationStep.run_id == run.id))
            db.exec(delete(ResourceGenerationRun).where(ResourceGenerationRun.id == run.id))
        for user_id, old in original.items():
            record = db.exec(
                select(UserMemoryProfile).where(UserMemoryProfile.user_id == user_id)
            ).first()
            if record:
                record.memory_profile = old
                db.add(record)
        db.commit()


def test_requested_run_is_immediately_queryable_cancelable_and_user_bounded(db: Session) -> None:
    student = _demo_student(db)
    request = ResourceGenerationRequest(
        subject="数据库系统原理",
        topic="可中断运行测试",
        resource_types=["lecture_markdown"],
    )
    run = resource_package_service.create_requested_run(
        db,
        request=request,
        owner_id=student.id,
    )
    try:
        public = resource_package_service.get_run(db, run_id=run.id, user_id=student.id)
        assert public is not None
        assert public.status == "requested"
        with pytest.raises(ResourcePackagePersistenceError) as exc_info:
            resource_package_service.create_requested_run(
                db,
                request=request,
                owner_id=student.id,
            )
        assert exc_info.value.code == "RESOURCE_RUN_ALREADY_ACTIVE"

        cancelled = resource_package_service.request_cancel(
            db,
            run_id=run.id,
            user_id=student.id,
        )
        assert cancelled is not None and cancelled.cancel_requested
        resource_package_service.execute_requested_run(run.id)
        terminal = resource_package_service.get_run(db, run_id=run.id, user_id=student.id)
        assert terminal is not None
        assert terminal.status == "cancelled"
    finally:
        db.exec(delete(ResourceGenerationStep).where(ResourceGenerationStep.run_id == run.id))
        db.exec(delete(ResourceGenerationRun).where(ResourceGenerationRun.id == run.id))
        db.commit()


def test_cancel_during_provider_call_prevents_package_resource_and_graph_writeback(
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
    original_generate = resource_generation_service.generate
    captured: dict[str, str] = {}

    def generate_then_cancel(*args, **kwargs):
        response = original_generate(*args, **kwargs)
        with Session(engine) as cancel_session:
            active = cancel_session.exec(
                select(ResourceGenerationRun).where(
                    ResourceGenerationRun.user_id == student.id,
                    ResourceGenerationRun.status == "running",
                )
            ).first()
            assert active is not None
            captured["run_id"] = active.id
            cancelled = resource_package_service.request_cancel(
                cancel_session,
                run_id=active.id,
                user_id=student.id,
            )
            assert cancelled is not None
            assert cancelled.status == "running"
            assert cancelled.cancel_requested
            assert cancelled.current_step == "cancelling"
        return response

    monkeypatch.setattr(resource_generation_service, "generate", generate_then_cancel)
    before_packages = set(db.exec(select(GeneratedResourcePackage.id)).all())
    before_resources = set(db.exec(select(Resource.id)).all())
    before_links = set(db.exec(select(ResourceKnowledgeLink.id)).all())
    before_edges = set(db.exec(select(CourseKnowledgeEdge.id)).all())

    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service.generate(
            db,
            ResourceGenerationRequest(
                course_id=DEMO_COURSE_ID,
                subject="数据库系统原理",
                topic="取消后不得写回",
                resource_types=["lecture_markdown", "practice_markdown"],
            ),
            owner_id=student.id,
        )

    assert exc_info.value.code == "RUN_CANCELLED"
    assert captured["run_id"] == exc_info.value.run_id
    db.expire_all()
    terminal = resource_package_service.get_run(
        db,
        run_id=captured["run_id"],
        user_id=student.id,
    )
    assert terminal is not None
    assert terminal.status == "cancelled"
    assert terminal.package_id is None
    assert set(db.exec(select(GeneratedResourcePackage.id)).all()) == before_packages
    assert set(db.exec(select(Resource.id)).all()) == before_resources
    assert set(db.exec(select(ResourceKnowledgeLink.id)).all()) == before_links
    assert set(db.exec(select(CourseKnowledgeEdge.id)).all()) == before_edges


def test_cancel_after_core_commit_keeps_files_as_partial_and_resumable(
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
    original_link = resource_package_service._link_graph
    captured: dict[str, str] = {}

    def cancel_after_core(session, run, request, response, resources):
        captured["run_id"] = run.id
        captured["package_id"] = response.package_id
        with Session(engine) as cancel_session:
            persisted = cancel_session.get(ResourceGenerationRun, run.id)
            assert persisted is not None
            assert persisted.package_id == response.package_id
            evidence = resource_package_service.request_cancel(
                cancel_session, run_id=run.id, user_id=student.id
            )
            assert evidence is not None
            assert evidence.status == "running"
            assert evidence.cancel_requested is True
        return original_link(session, run, request, response, resources)

    monkeypatch.setattr(resource_package_service, "_link_graph", cancel_after_core)
    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service.generate(
            db,
            ResourceGenerationRequest(
                course_id=DEMO_COURSE_ID,
                subject="数据库系统原理",
                topic="核心落库后停止",
                resource_types=["lecture_markdown"],
            ),
            owner_id=student.id,
        )

    assert exc_info.value.code == "POST_PERSISTENCE_CANCELLED"
    db.expire_all()
    terminal = resource_package_service.get_run(
        db, run_id=captured["run_id"], user_id=student.id
    )
    assert terminal is not None
    assert terminal.status == "partial_success"
    assert terminal.package_id == captured["package_id"]
    assert terminal.error_code == "POST_PERSISTENCE_CANCELLED"
    assert db.get(GeneratedResourcePackage, captured["package_id"]) is not None
    assert db.exec(
        select(Resource).where(Resource.package_id == captured["package_id"])
    ).all()
    _delete_package_rows(db, captured["package_id"])
    resource_generation_service.delete_package(captured["package_id"])


def test_create_requested_run_is_idempotent_and_rejects_payload_reuse(db: Session) -> None:
    student = _demo_student(db)
    request = ResourceGenerationRequest(
        subject="数据库系统原理",
        topic="幂等运行",
        resource_types=["lecture_docx"],
    )
    run = resource_package_service.create_requested_run(
        db,
        request=request,
        owner_id=student.id,
        idempotency_key="double-click-001",
    )
    try:
        duplicate = resource_package_service.create_requested_run(
            db,
            request=request,
            owner_id=student.id,
            idempotency_key="double-click-001",
        )
        assert duplicate.id == run.id
        with pytest.raises(ResourcePackagePersistenceError) as exc_info:
            resource_package_service.create_requested_run(
                db,
                request=request.model_copy(update={"topic": "不同请求"}),
                owner_id=student.id,
                idempotency_key="double-click-001",
            )
        assert exc_info.value.code == "IDEMPOTENCY_CONFLICT"
    finally:
        db.exec(delete(ResourceGenerationRun).where(ResourceGenerationRun.id == run.id))
        db.commit()


def test_running_cancel_waits_for_worker_fence_before_resume_requeues(
    db: Session,
    monkeypatch,
) -> None:
    student = _demo_student(db)
    request = ResourceGenerationRequest(
        subject="数据库系统原理",
        topic="取消后立即恢复",
        resource_types=["lecture_docx"],
    )
    run = resource_package_service.create_requested_run(
        db,
        request=request,
        owner_id=student.id,
    )
    first_attempt = resource_package_service._prepare_attempt(run.id)
    assert first_attempt
    assert resource_package_service._prepare_attempt(run.id) is None
    db.expire_all()
    claimed = db.get(ResourceGenerationRun, run.id)
    assert claimed is not None
    claimed.status = "running"
    claimed.started_at = datetime.now(timezone.utc)
    db.add(claimed)
    db.commit()
    cancelled = resource_package_service.request_cancel(
        db,
        run_id=run.id,
        user_id=student.id,
    )
    assert cancelled is not None
    assert cancelled.status == "running"
    assert cancelled.cancel_requested is True
    assert cancelled.current_step == "cancelling"
    assert cancelled.lease_expires_at is not None

    enqueued: list[str] = []
    monkeypatch.setattr(
        resource_package_service,
        "enqueue_requested_run",
        lambda run_id: enqueued.append(run_id) or True,
    )
    resumed = resource_package_service.resume(db, run_id=run.id, user_id=student.id)
    assert resumed is not None and resumed.status == "running"
    assert resumed.cancel_requested is True
    assert enqueued == []

    db.expire_all()
    worker_run = db.get(ResourceGenerationRun, run.id)
    assert worker_run is not None
    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service._raise_if_cancelled(
            db,
            worker_run,
            step_key="generating",
            attempt_id=first_attempt,
        )
    assert exc_info.value.code == "RUN_CANCELLED"
    db.expire_all()
    current = db.get(ResourceGenerationRun, run.id)
    assert current is not None
    assert current.active_attempt_id is None
    assert current.status == "cancelled"

    resumed = resource_package_service.resume(db, run_id=run.id, user_id=student.id)
    assert resumed is not None and resumed.status == "requested"
    assert resumed.cancel_requested is False
    assert enqueued == [run.id]


def test_resume_requeues_only_after_execution_lease_expires(
    db: Session,
    monkeypatch,
) -> None:
    student = _demo_student(db)
    run = resource_package_service.create_requested_run(
        db,
        request=ResourceGenerationRequest(
            subject="数据库系统原理",
            topic="租约回收",
            resource_types=["lecture_pdf"],
        ),
        owner_id=student.id,
    )
    run.status = "running"
    run.active_attempt_id = "live-attempt"
    run.lease_expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    db.add(run)
    db.commit()
    enqueued: list[str] = []
    monkeypatch.setattr(
        resource_package_service,
        "enqueue_requested_run",
        lambda run_id: enqueued.append(run_id) or True,
    )
    current = resource_package_service.resume(db, run_id=run.id, user_id=student.id)
    assert current is not None and current.status == "running"
    assert enqueued == []

    run = db.get(ResourceGenerationRun, run.id)
    assert run is not None
    run.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.add(run)
    db.commit()
    recovered = resource_package_service.resume(db, run_id=run.id, user_id=student.id)
    assert recovered is not None and recovered.status == "requested"
    assert recovered.error_code == "STALE_RUN_RECOVERED"
    assert enqueued == [run.id]


@pytest.mark.parametrize("failure_mode", ["empty", "missing"])
def test_artifact_gate_rejects_empty_or_missing_outputs(
    db: Session,
    tmp_path,
    monkeypatch,
    failure_mode: str,
) -> None:
    student = _demo_student(db)
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    monkeypatch.setattr(resource_generation_service, "_generate_ai_contents", lambda *_: ({}, "test"))
    original_generate = resource_generation_service.generate

    def invalid_generate(*args, **kwargs):
        response = original_generate(*args, **kwargs)
        if failure_mode == "empty":
            return response.model_copy(update={"artifacts": []})
        artifact = response.artifacts[0]
        resource_generation_service.resolve_artifact_path(
            response.package_id,
            artifact.file_name,
        ).unlink()
        return response

    monkeypatch.setattr(resource_generation_service, "generate", invalid_generate)
    with pytest.raises(ResourcePackagePersistenceError) as exc_info:
        resource_package_service.generate(
            db,
            ResourceGenerationRequest(
                subject="数据库系统原理",
                topic=f"产物门禁-{failure_mode}",
                resource_types=["lecture_docx"],
            ),
            owner_id=student.id,
        )
    assert exc_info.value.code == "ARTIFACT_QUALITY_FAILED"
    assert db.exec(
        select(GeneratedResourcePackage).where(
            GeneratedResourcePackage.topic == f"产物门禁-{failure_mode}"
        )
    ).first() is None
    assert list(tmp_path.iterdir()) == []


def test_package_read_rejects_missing_file_instead_of_reporting_completed(
    db: Session,
    tmp_path,
    monkeypatch,
) -> None:
    student = _demo_student(db)
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    monkeypatch.setattr(resource_generation_service, "_generate_ai_contents", lambda *_: ({}, "test"))
    response = resource_package_service.generate(
        db,
        ResourceGenerationRequest(
            subject="数据库系统原理",
            topic="读取完整性门禁",
            resource_types=["lecture_docx", "lecture_pdf"],
        ),
        owner_id=student.id,
    )
    try:
        artifact = response.artifacts[0]
        resource_generation_service.resolve_artifact_path(
            response.package_id,
            artifact.file_name,
        ).unlink()
        with pytest.raises(ResourcePackagePersistenceError) as exc_info:
            resource_package_service.get_package(
                db,
                package_id=response.package_id,
                user_id=student.id,
            )
        assert exc_info.value.code == "ARTIFACT_INTEGRITY_FAILED"
        recent = resource_package_service.list_recent(db, owner_id=student.id)
        assert all(item["package_id"] != response.package_id for item in recent)
    finally:
        _delete_package_rows(db, response.package_id)
        resource_generation_service.delete_package(response.package_id)


@pytest.mark.parametrize("corruption", ["truncate", "same_size"])
def test_package_read_and_download_reject_corrupted_artifact(
    db: Session,
    tmp_path,
    monkeypatch,
    corruption: str,
) -> None:
    student = _demo_student(db)
    monkeypatch.setattr(resource_generation_service, "output_root", tmp_path)
    monkeypatch.setattr(
        resource_generation_service, "_generate_ai_contents", lambda *_: ({}, "test")
    )
    response = resource_package_service.generate(
        db,
        ResourceGenerationRequest(
            subject="数据库系统原理",
            topic=f"摘要完整性-{corruption}",
            resource_types=["lecture_docx"],
        ),
        owner_id=student.id,
    )
    try:
        artifact = response.artifacts[0]
        path = resource_generation_service.resolve_artifact_path(
            response.package_id, artifact.file_name
        )
        original = path.read_bytes()
        path.write_bytes(
            b"x" if corruption == "truncate" else bytes([original[0] ^ 0xFF]) + original[1:]
        )
        with pytest.raises(ResourcePackagePersistenceError) as exc_info:
            resource_package_service.get_package(
                db, package_id=response.package_id, user_id=student.id
            )
        assert exc_info.value.code == "ARTIFACT_INTEGRITY_FAILED"
        with pytest.raises(ValueError, match="does not match"):
            resource_generation_service.resolve_verified_artifact_path(
                response.package_id, artifact.file_name
            )
    finally:
        _delete_package_rows(db, response.package_id)
        resource_generation_service.delete_package(response.package_id)
