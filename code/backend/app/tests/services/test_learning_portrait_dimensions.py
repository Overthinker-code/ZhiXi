from uuid import uuid4

from app.models.learning_evidence import LearningEvidence
from app.services.learning_report_service import LearningReportService


def _evidence(*, source_type: str, score: float, task_type: str = "") -> LearningEvidence:
    return LearningEvidence(
        user_id=uuid4(),
        knowledge_point="事务并发控制",
        display_name="事务并发控制",
        knowledge_point_id="kp-transaction",
        idempotency_key=uuid4().hex,
        source_type=source_type,
        source_id=uuid4().hex,
        event_type="graded",
        score=score,
        payload={
            "knowledge_identity": {"trusted": True},
            "task_type": task_type,
        },
    )


def test_portrait_contract_always_contains_six_auditable_dimensions() -> None:
    dimensions = LearningReportService.build_portrait_dimensions(
        evidence_confidence={},
        evidence_rows=[],
        classroom_behavior_summary=None,
    )

    assert len(dimensions) == 6
    assert len({item.key for item in dimensions}) == 6
    assert all(item.value is None for item in dimensions)
    assert all(item.state == "insufficient" for item in dimensions)
    assert all(item.sample_size == 0 for item in dimensions)


def test_portrait_values_only_use_persisted_assessment_and_behavior_data() -> None:
    dimensions = LearningReportService.build_portrait_dimensions(
        evidence_confidence={
            "transaction": {
                "mastery_estimate": 0.72,
                "effective_sample_size": 2.0,
            }
        },
        evidence_rows=[
            _evidence(source_type="exercise_grading", score=0.8),
            _evidence(source_type="assignment", score=0.7, task_type="project"),
        ],
        classroom_behavior_summary={
            "recent_avg_lei": 0.76,
            "cognitive_engagement": 0.68,
            "on_task_rate": 0.81,
            "student_count": 1,
        },
    )
    by_key = {item.key: item for item in dimensions}

    assert by_key["knowledge_foundation"].value == 72.0
    assert by_key["problem_solving"].value == 80.0
    assert by_key["transfer_application"].value == 70.0
    assert by_key["learning_engagement"].value == 76.0
    assert by_key["cognitive_engagement"].value == 68.0
    assert by_key["attention_stability"].value == 81.0
    assert all(item.method_version == "portrait_evidence_v1" for item in dimensions)
