from __future__ import annotations

from copy import deepcopy
import json
import time
from uuid import uuid4

from sqlmodel import Session, delete, select

from app.models import LearningEvidence, User
from app.services.learning_report_service import learning_report_service
from app.services.user_memory_profile_service import (
    MemoryProfilePayload,
    UserMemoryProfileService,
    user_memory_profile_service,
)


class _JsonResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.content = json.dumps(payload, ensure_ascii=False)


class _JsonModel:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def invoke(self, _messages: object) -> _JsonResponse:
        return _JsonResponse(self.payload)


class _StructuredModel:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def with_structured_output(self, _schema: object) -> "_StructuredModel":
        return self

    def invoke(self, _messages: object) -> dict[str, object]:
        return self.payload


def _student(db: Session) -> User:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    return user


def test_dialogue_builds_eight_versioned_dimensions_without_invented_mastery(
    monkeypatch,
) -> None:
    extracted = {
        "knowledge_foundation": "学过数据库基础和 SQL，事务部分刚入门",
        "weak_points": ["事务隔离级别", "并发异常"],
        "error_patterns": ["混淆不可重复读与幻读"],
        "current_goal": "本周完成事务与并发控制复习",
        "learning_style": "先看图解，再用例题验证",
        "resource_preference": "短讲义、流程图和分层练习",
        "learning_rhythm": "工作日晚间 30 分钟，周末集中复盘",
        "self_regulation": "能按计划学习，但难题后容易中断",
        # Even if a model violates the prompt, dialogue-derived numbers must be
        # discarded by the service boundary.
        "mastery_map": {"事务隔离级别": 0.95},
    }
    monkeypatch.setattr(
        "app.services.user_memory_profile_service.ChatModelFactory.create",
        lambda **_kwargs: _JsonModel(extracted),
    )
    service = UserMemoryProfileService()
    payload = service.infer_profile_from_history(
        "学生：我学过 SQL，希望本周复习事务。我喜欢图解和例题，晚上学习。"
    )
    dimensions = service.build_dialogue_profile_dimensions(
        payload,
        source_ref="chat_digest:test",
        updated_at="2026-07-13T10:00:00+00:00",
    )

    assert len(dimensions) == 8
    assert set(dimensions) == set(service.PROFILE_DIMENSIONS)
    assert sum(item.value is not None for item in dimensions.values()) >= 6
    assert all(item.label for item in dimensions.values())
    assert all(item.source_type == "dialogue_inference" for item in dimensions.values())
    assert all(item.updated_at == "2026-07-13T10:00:00+00:00" for item in dimensions.values())
    assert all(item.version == 1 for item in dimensions.values())
    assert payload.mastery_map == {}


def test_graded_event_updates_profile_but_resource_exposure_does_not(db: Session) -> None:
    user = _student(db)
    record = user_memory_profile_service.get_record(db, user.id)
    original_profile = deepcopy(record.memory_profile) if record else None
    assessed_source = f"dynamic-profile-graded-{uuid4().hex}"
    exposure_source = f"dynamic-profile-exposure-{uuid4().hex}"
    try:
        seed = MemoryProfilePayload(
            knowledge_foundation="已完成关系模型基础",
            weak_points=["事务并发控制"],
            current_goal="掌握事务隔离级别",
            learning_style="示例驱动",
            resource_preference="图解与练习",
            learning_rhythm="晚间短时学习",
            self_regulation="按周计划执行",
            error_patterns=["混淆并发异常"],
        )
        seed.profile_dimensions = user_memory_profile_service.build_dialogue_profile_dimensions(
            seed,
            source_ref="chat_digest:seed",
            updated_at="2026-07-13T10:00:00+00:00",
        )
        user_memory_profile_service.upsert_profile(db, user_id=user.id, payload=seed)

        learning_report_service.record_evidence(
            db,
            user_id=user.id,
            course_id=None,
            knowledge_point="事务隔离级别",
            knowledge_point_id="transaction-isolation",
            source_type="exercise_grading",
            source_id=assessed_source,
            event_type="graded",
            score=0.35,
            payload={
                "error_patterns": ["将幻读误判为不可重复读"],
                "task_execution": {"completed": True, "attempt_count": 2},
            },
        )
        db.commit()
        assessed_profile = deepcopy(
            user_memory_profile_service.get_profile_dict(db, user.id) or {}
        )
        mastery_dimension = assessed_profile["profile_dimensions"]["knowledge_mastery"]
        assert mastery_dimension["source_type"] == "learning_evidence"
        assert mastery_dimension["value"]["mastery_map"]
        assert "将幻读误判为不可重复读" in assessed_profile["error_patterns"]
        assert (
            assessed_profile["profile_dimensions"]["self_regulation"]["value"][
                "attempt_count"
            ]
            == 2
        )

        learning_report_service.record_evidence(
            db,
            user_id=user.id,
            course_id=None,
            knowledge_point="事务隔离级别",
            knowledge_point_id="transaction-isolation",
            source_type="resource_run",
            source_id=exposure_source,
            event_type="resource_opened",
            score=None,
            payload={"exposure_seconds": 120},
        )
        db.commit()
        after_exposure = user_memory_profile_service.get_profile_dict(db, user.id) or {}
        assert after_exposure["mastery_map"] == assessed_profile["mastery_map"]
        assert (
            after_exposure["profile_dimensions"]["knowledge_mastery"]["version"]
            == mastery_dimension["version"]
        )
        assert (
            after_exposure["profile_dimensions"]["knowledge_mastery"]["updated_at"]
            == mastery_dimension["updated_at"]
        )
    finally:
        db.exec(
            delete(LearningEvidence).where(
                LearningEvidence.source_id.in_([assessed_source, exposure_source])
            )
        )
        restored = user_memory_profile_service.get_record(db, user.id)
        if original_profile is None:
            if restored:
                db.delete(restored)
        else:
            assert restored is not None
            restored.memory_profile = original_profile
            db.add(restored)
        db.commit()


def test_legacy_profile_write_preserves_dynamic_dimension_audit(db: Session) -> None:
    user = _student(db)
    record = user_memory_profile_service.get_record(db, user.id)
    original_profile = deepcopy(record.memory_profile) if record else None
    try:
        seed = MemoryProfilePayload(current_goal="先完成章节练习")
        seed.profile_dimensions = user_memory_profile_service.build_dialogue_profile_dimensions(
            seed,
            source_ref="chat_digest:legacy-preserve",
        )
        user_memory_profile_service.upsert_profile(db, user_id=user.id, payload=seed)
        before = deepcopy(
            (user_memory_profile_service.get_profile_dict(db, user.id) or {})[
                "profile_dimensions"
            ]
        )

        user_memory_profile_service.upsert_profile(
            db,
            user_id=user.id,
            payload=MemoryProfilePayload(
                weak_points=["索引选择"],
                mastery_map={"索引选择": 0.5},
            ),
        )
        after = user_memory_profile_service.get_profile_dict(db, user.id) or {}
        assert after["profile_dimensions"] == before
    finally:
        restored = user_memory_profile_service.get_record(db, user.id)
        if original_profile is None:
            if restored:
                db.delete(restored)
        else:
            assert restored is not None
            restored.memory_profile = original_profile
            db.add(restored)
        db.commit()


def test_default_learning_report_is_local_and_never_creates_an_llm(
    db: Session, monkeypatch
) -> None:
    user = _student(db)

    def forbidden_model(**_kwargs: object) -> None:
        raise AssertionError("default learning-report read must not create an LLM")

    monkeypatch.setattr(
        "app.services.learning_report_service.ChatModelFactory.create",
        forbidden_model,
    )
    started = time.perf_counter()
    report = learning_report_service.build_report(
        db,
        str(user.id),
        refresh_profile=False,
    )
    elapsed = time.perf_counter() - started

    assert report.learner_id == str(user.id)
    assert report.summary
    assert len(report.dynamic_profile_dimensions) == 8
    assert elapsed < 2.0


def test_explicit_refresh_still_runs_remote_diagnosis_path(
    db: Session, monkeypatch
) -> None:
    user = _student(db)
    refresh_calls: list[str] = []
    model_calls: list[dict[str, object]] = []

    def fake_refresh(user_id: str) -> dict[str, str]:
        refresh_calls.append(user_id)
        return {"status": "success"}

    def fake_model(**kwargs: object) -> _StructuredModel:
        model_calls.append(kwargs)
        return _StructuredModel(
            {
                "summary": "远程刷新诊断已完成",
                "risk_level": "low",
                "strengths": ["能够主动复盘"],
                "recommended_actions": ["完成一次章节自测"],
                "recommended_resources": ["事务章节讲义"],
                "follow_up_questions": ["下一步应该练习什么？"],
            }
        )

    monkeypatch.setattr(user_memory_profile_service, "refresh_profile", fake_refresh)
    monkeypatch.setattr(
        "app.services.learning_report_service.ChatModelFactory.create",
        fake_model,
    )
    report = learning_report_service.build_report(
        db,
        str(user.id),
        refresh_profile=True,
    )

    assert refresh_calls == [str(user.id)]
    assert len(model_calls) == 1
    assert report.summary == "远程刷新诊断已完成"
    assert report.risk_level == "low"
