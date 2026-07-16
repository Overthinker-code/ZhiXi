from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.api.v1.endpoints import resource_workshop
from app.core.config import settings
from app.models import CourseKnowledgeNode, LearningEvidence, User
from app.services.knowledge_graph_service import ensure_course_graph
from app.services.learning_report_service import learning_report_service
from app.services.user_memory_profile_service import user_memory_profile_service
from app.tests.utils.user import authentication_token_from_email


COURSE_ONE = UUID("c1111111-1111-4111-9111-111111111101")
COURSE_TWO = UUID("c1111111-1111-4111-9111-111111111102")


@pytest.fixture
def student_token_headers(client: TestClient, db: Session) -> dict[str, str]:
    return authentication_token_from_email(
        client=client,
        email="student@example.com",
        db=db,
    )


def _student(db: Session) -> User:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    return user


def _concept_node(db: Session, course_id: UUID) -> CourseKnowledgeNode:
    ensure_course_graph(db, course_id=course_id)
    node = db.exec(
        select(CourseKnowledgeNode)
        .where(
            CourseKnowledgeNode.course_id == course_id,
            CourseKnowledgeNode.node_type == "concept",
        )
        .order_by(CourseKnowledgeNode.label)
    ).first()
    assert node is not None
    return node


def _exercise_payload(
    *,
    node: CourseKnowledgeNode,
    idempotency_key: str,
    source_resource_id: str,
    question: str | None = None,
) -> dict[str, object]:
    return {
        "subject": "数据库系统",
        "topic": node.label,
        "question": question or f"请解释{node.label}的核心含义。",
        "student_answer": "事务中的操作要么全部完成，要么全部回滚。",
        "reference_answer": "原子性保证事务中的操作全部成功或全部回滚。",
        "max_score": 100,
        "course_id": str(node.course_id),
        "knowledge_point_id": str(node.id),
        "source_resource_id": source_resource_id,
        "idempotency_key": idempotency_key,
    }


def test_grade_records_one_evidence_for_idempotent_replay(
    client: TestClient,
    db: Session,
    student_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_calls = 0

    def deterministic_grade(_request: resource_workshop.ExerciseGradeRequest):
        nonlocal model_calls
        model_calls += 1
        return 86.0, ["核心概念正确"], [], "回答正确"

    monkeypatch.setattr(resource_workshop, "_grade_exercise_llm", deterministic_grade)
    student = _student(db)
    original = user_memory_profile_service.get_record(db, student.id)
    original_profile = deepcopy(original.memory_profile) if original else None
    marker = f"grade-idempotent-{uuid4().hex}"
    node = _concept_node(db, COURSE_ONE)
    payload = _exercise_payload(
        node=node,
        idempotency_key=marker,
        source_resource_id=marker,
    )

    try:
        first = client.post(
            f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
            headers=student_token_headers,
            json=payload,
        )
        replay = client.post(
            f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
            headers=student_token_headers,
            json=payload,
        )

        assert first.status_code == 200, first.text
        assert replay.status_code == 200, replay.text
        assert first.json()["mastery_update"]["evidence_created"] is True
        assert first.json()["mastery_update"]["mastery_eligible"] is True
        assert replay.json()["mastery_update"]["idempotent_replay"] is True
        assert replay.json()["mastery_delta"] == 0
        assert replay.json()["score"] == first.json()["score"]
        assert replay.json()["feedback"] == first.json()["feedback"]
        assert model_calls == 1
        assert {
            "topic",
            "score",
            "is_correct",
            "mastery_before",
            "mastery_after",
            "mastery_delta",
            "feedback",
            "strengths",
            "gaps",
            "follow_up",
            "mastery_update",
        } <= replay.json().keys()

        db.expire_all()
        rows = db.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.source_id == marker,
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].course_id == COURSE_ONE
        assert rows[0].source_type == "exercise_grading"
        assert rows[0].event_type == "graded"
    finally:
        db.rollback()
        db.exec(
            delete(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.source_id == marker,
            )
        )
        record = user_memory_profile_service.get_record(db, student.id)
        if original_profile is None:
            if record:
                db.delete(record)
        else:
            assert record is not None
            record.memory_profile = original_profile
            db.add(record)
        db.commit()


def test_same_client_key_is_scoped_by_course(
    client: TestClient,
    db: Session,
    student_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def course_specific_grade(request: resource_workshop.ExerciseGradeRequest):
        score = 90.0 if request.course_id == COURSE_ONE else 10.0
        return score, [], [], "course-scoped test grade"

    monkeypatch.setattr(resource_workshop, "_grade_exercise_llm", course_specific_grade)
    student = _student(db)
    original = user_memory_profile_service.get_record(db, student.id)
    original_profile = deepcopy(original.memory_profile) if original else None
    shared_key = f"grade-cross-course-{uuid4().hex}"
    sources = [f"{shared_key}-one", f"{shared_key}-two"]
    nodes = [_concept_node(db, COURSE_ONE), _concept_node(db, COURSE_TWO)]

    try:
        responses = [
            client.post(
                f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
                headers=student_token_headers,
                json=_exercise_payload(
                    node=node,
                    idempotency_key=shared_key,
                    source_resource_id=source_id,
                ),
            )
            for node, source_id in zip(nodes, sources, strict=True)
        ]
        assert [response.status_code for response in responses] == [200, 200]
        assert responses[0].json()["mastery_after"] > responses[1].json()["mastery_after"]

        db.expire_all()
        rows = db.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.source_id.in_(sources),
            )
        ).all()
        assert len(rows) == 2
        assert {row.course_id for row in rows} == {COURSE_ONE, COURSE_TWO}
        assert len({row.idempotency_key for row in rows}) == 2
    finally:
        db.rollback()
        db.exec(
            delete(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.source_id.in_(sources),
            )
        )
        record = user_memory_profile_service.get_record(db, student.id)
        if original_profile is None:
            if record:
                db.delete(record)
        else:
            assert record is not None
            record.memory_profile = original_profile
            db.add(record)
        db.commit()


def test_grade_rejects_inaccessible_course_before_model_call(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_model_call(_request: object) -> None:
        raise AssertionError("grading model called before course authorization")

    monkeypatch.setattr(resource_workshop, "_grade_exercise_llm", forbidden_model_call)
    marker = f"grade-denied-{uuid4().hex}"
    node = _concept_node(db, COURSE_ONE)
    response = client.post(
        f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
        headers=normal_user_token_headers,
        json=_exercise_payload(
            node=node,
            idempotency_key=marker,
            source_resource_id=marker,
        ),
    )

    assert response.status_code == 404


def test_legacy_grade_payload_remains_supported(
    client: TestClient,
    db: Session,
    student_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resource_workshop, "_grade_exercise_llm", lambda _request: None)
    student = _student(db)
    original = user_memory_profile_service.get_record(db, student.id)
    original_profile = deepcopy(original.memory_profile) if original else None
    before_ids = set(
        db.exec(
            select(LearningEvidence.id).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.course_id.is_(None),
            )
        ).all()
    )

    try:
        response = client.post(
            f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
            headers=student_token_headers,
            json={
                "subject": "数据库系统",
                "topic": "ACID",
                "question": "什么是事务原子性？",
                "student_answer": "事务要么全部成功，要么全部回滚。",
                "reference_answer": "事务中的操作全部成功或全部回滚。",
                "max_score": 100,
            },
        )

        assert response.status_code == 200, response.text
        assert response.json()["mastery_update"]["course_id"] is None
        assert response.json()["mastery_update"]["mastery_eligible"] is False
        assert response.json()["mastery_delta"] == 0
        db.expire_all()
        after_rows = db.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.course_id.is_(None),
            )
        ).all()
        created = [row for row in after_rows if row.id not in before_ids]
        assert len(created) == 1
        assert created[0].source_type == "exercise_grading"
        assert created[0].score is None
        assert created[0].knowledge_point == learning_report_service.UNSCOPED_INTERACTION_KEY
    finally:
        db.rollback()
        db.exec(
            delete(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.course_id.is_(None),
                LearningEvidence.id.notin_(before_ids),
            )
        )
        record = user_memory_profile_service.get_record(db, student.id)
        if original_profile is None:
            if record:
                db.delete(record)
        else:
            assert record is not None
            record.memory_profile = original_profile
            db.add(record)
        db.commit()


def test_reusing_key_for_different_question_is_rejected(
    client: TestClient,
    db: Session,
    student_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resource_workshop, "_grade_exercise_llm", lambda _request: None)
    student = _student(db)
    original = user_memory_profile_service.get_record(db, student.id)
    original_profile = deepcopy(original.memory_profile) if original else None
    marker = f"grade-conflict-{uuid4().hex}"
    node = _concept_node(db, COURSE_ONE)

    try:
        first = client.post(
            f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
            headers=student_token_headers,
            json=_exercise_payload(
                node=node,
                idempotency_key=marker,
                source_resource_id=marker,
            ),
        )
        conflict = client.post(
            f"{settings.API_V1_STR}/resource-workshop/exercises/grade",
            headers=student_token_headers,
            json=_exercise_payload(
                node=node,
                idempotency_key=marker,
                source_resource_id=marker,
                question="请解释 ACID 中一致性的含义。",
            ),
        )

        assert first.status_code == 200, first.text
        assert conflict.status_code == 409
    finally:
        db.rollback()
        db.exec(
            delete(LearningEvidence).where(
                LearningEvidence.user_id == student.id,
                LearningEvidence.source_id == marker,
            )
        )
        record = user_memory_profile_service.get_record(db, student.id)
        if original_profile is None:
            if record:
                db.delete(record)
        else:
            assert record is not None
            record.memory_profile = original_profile
            db.add(record)
        db.commit()
