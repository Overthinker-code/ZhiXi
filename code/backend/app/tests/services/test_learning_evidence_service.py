from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, delete, select

from app.models import CourseKnowledgeNode, LearningEvidence, User
from app.services.user_memory_profile_service import (
    MemoryProfilePayload,
    user_memory_profile_service,
)
from app.services.knowledge_graph_service import ensure_course_graph
from app.services.learning_report_service import learning_report_service


COURSE_ID = UUID("c1111111-1111-4111-9111-111111111101")


def _student(db: Session) -> User:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    return user


def test_evidence_aliases_and_replay_are_idempotent(db: Session) -> None:
    user = _student(db)
    source_id = "quiz-idempotency-test"
    first = learning_report_service.record_evidence(
        db,
        user_id=user.id,
        course_id=None,
        knowledge_point="ACID",
        knowledge_point_id="acid",
        source_type="quiz",
        source_id=source_id,
        event_type="graded",
        score=0.8,
        weight=1.0,
    )
    replay = learning_report_service.record_evidence(
        db,
        user_id=user.id,
        course_id=None,
        knowledge_point="事务 ACID 特性",
        knowledge_point_id="acid",
        source_type="quiz",
        source_id=source_id,
        event_type="graded",
        score=0.8,
        weight=1.0,
    )
    db.commit()
    try:
        assert first.id == replay.id
        summary = learning_report_service.evidence_confidence(
            db, user.id, exact_course_scope=True
        )
        point = summary["数据库事务acid特性"]
        assert point["evidence_count"] == 1
        assert point["independent_source_count"] == 1
    finally:
        db.exec(delete(LearningEvidence).where(LearningEvidence.source_id == source_id))
        db.commit()


def test_untrusted_free_text_is_interaction_not_mastery(db: Session) -> None:
    user = _student(db)
    source_id = "resource-exposure-confidence-test"
    evidence = learning_report_service.record_evidence(
        db,
        user_id=user.id,
        course_id=COURSE_ID,
        knowledge_point="仅资源暴露测试知识点",
        source_type="quiz",
        source_id=source_id,
        event_type="graded",
        score=0.9,
        weight=0.25,
    )
    db.commit()
    try:
        summary = learning_report_service.evidence_confidence(db, user.id, course_id=COURSE_ID)
        assert evidence.knowledge_point == learning_report_service.UNSCOPED_INTERACTION_KEY
        assert evidence.score is None
        assert evidence.payload["observed_score"] == 0.9
        assert evidence.payload["knowledge_identity"]["trusted"] is False
        assert evidence.knowledge_point not in summary
    finally:
        db.exec(delete(LearningEvidence).where(LearningEvidence.source_id == source_id))
        db.commit()


def test_beta_posterior_confidence_is_monotonic_and_conflict_sensitive(db: Session) -> None:
    user = _student(db)
    prefix = "beta-posterior-test"
    now = datetime.now(timezone.utc)

    def add(
        point: str,
        point_id: str,
        source_type: str,
        source_id: str,
        score: float,
        observed_at: datetime,
    ) -> None:
        learning_report_service.record_evidence(
            db,
            user_id=user.id,
            course_id=None,
            knowledge_point=point,
            knowledge_point_id=point_id,
            source_type=source_type,
            source_id=f"{prefix}-{source_id}",
            event_type="graded",
            score=score,
            weight=1.0,
            observed_at=observed_at,
        )

    add("单证据", "single", "quiz", "one", 0.9, now)
    add("独立双证据", "double", "quiz", "two-a", 0.9, now)
    add("独立双证据", "double", "teacher_assessment", "two-b", 0.9, now)
    add("旧证据", "old", "quiz", "old", 0.9, now - timedelta(days=180))
    add("一致证据", "consistent", "quiz", "consistent-a", 0.9, now)
    add("一致证据", "consistent", "teacher_assessment", "consistent-b", 0.9, now)
    add("冲突证据", "conflict", "quiz", "conflict-a", 0.9, now)
    add("冲突证据", "conflict", "teacher_assessment", "conflict-b", 0.1, now)
    db.commit()
    try:
        result = learning_report_service.evidence_confidence(
            db, user.id, exact_course_scope=True, now=now
        )
        assert result["double"]["effective_sample_size"] > result["single"]["effective_sample_size"]
        assert result["double"]["confidence"] > result["single"]["confidence"]
        assert result["old"]["effective_sample_size"] < result["single"]["effective_sample_size"]
        assert (
            result["conflict"]["posterior"]["interval_width"]
            > result["consistent"]["posterior"]["interval_width"]
        )
    finally:
        db.exec(delete(LearningEvidence).where(LearningEvidence.source_id.startswith(prefix)))
        db.commit()


def test_verified_curriculum_node_can_update_mastery(db: Session) -> None:
    user = _student(db)
    ensure_course_graph(db, course_id=COURSE_ID)
    node = db.exec(
        select(CourseKnowledgeNode).where(
            CourseKnowledgeNode.course_id == COURSE_ID,
            CourseKnowledgeNode.node_type == "concept",
            CourseKnowledgeNode.label == "事务与原子性",
        )
    ).first()
    assert node is not None
    source_ids = [
        f"verified-node-id-{uuid4().hex}",
        f"verified-node-label-{uuid4().hex}",
    ]
    evidence = learning_report_service.record_evidence(
        db,
        user_id=user.id,
        course_id=COURSE_ID,
        knowledge_point=node.label,
        knowledge_point_id=str(node.id),
        source_type="quiz",
        source_id=source_ids[0],
        event_type="graded",
        score=0.9,
    )
    label_verified = learning_report_service.record_evidence(
        db,
        user_id=user.id,
        course_id=COURSE_ID,
        knowledge_point=node.label,
        knowledge_point_id=None,
        source_type="teacher_assessment",
        source_id=source_ids[1],
        event_type="graded",
        score=0.8,
    )
    db.commit()
    try:
        summary = learning_report_service.evidence_confidence(
            db, user.id, course_id=COURSE_ID
        )
        assert evidence.knowledge_point == node.normalized_key
        assert evidence.knowledge_point_id == str(node.id)
        assert evidence.score == 0.9
        assert label_verified.knowledge_point_id == str(node.id)
        assert label_verified.score == 0.8
        assert summary[node.normalized_key]["mastery_estimate"] is not None
    finally:
        db.exec(delete(LearningEvidence).where(LearningEvidence.source_id.in_(source_ids)))
        db.commit()


def test_historical_query_like_scored_row_is_filtered_from_mastery(db: Session) -> None:
    user = _student(db)
    source_id = f"historical-query-{uuid4().hex}"
    row = LearningEvidence(
        user_id=user.id,
        course_id=None,
        knowledge_point="学习高数很难怎么办请给我三条可执行建议",
        display_name="学习高数很难怎么办，请给我三条可执行建议",
        knowledge_point_id=None,
        idempotency_key=uuid4().hex,
        source_type="quiz",
        source_id=source_id,
        event_type="graded",
        score=0.9,
    )
    db.add(row)
    db.commit()
    try:
        summary = learning_report_service.evidence_confidence(
            db, user.id, exact_course_scope=True
        )
        assert row.knowledge_point not in summary
    finally:
        db.delete(row)
        db.commit()


def test_learning_report_ignores_untrusted_profile_mastery_keys(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unavailable_model(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("model disabled in deterministic report test")

    monkeypatch.setattr(
        "app.services.learning_report_service.ChatModelFactory.create",
        unavailable_model,
    )
    user = _student(db)
    record = user_memory_profile_service.get_record(db, user.id)
    original_profile = deepcopy(record.memory_profile) if record else None
    noisy_key = "学习高数很难怎么办请给我三条可执行建议"
    try:
        user_memory_profile_service.upsert_profile(
            db,
            user_id=user.id,
            payload=MemoryProfilePayload(
                mastery_map={noisy_key: 0.91},
                weak_points=["高等数学"],
            ),
        )
        report = learning_report_service.build_report(db, str(user.id))
        assert noisy_key not in report.mastery_map
        assert all(noisy_key not in key for key in report.evidence_confidence)
    finally:
        restored = user_memory_profile_service.get_record(db, user.id)
        if original_profile is None:
            if restored:
                db.delete(restored)
                db.commit()
        else:
            assert restored is not None
            restored.memory_profile = original_profile
            db.add(restored)
            db.commit()
