from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlmodel import Session, delete, select

from app.models import LearningEvidence, User
from app.services.learning_report_service import learning_report_service


def test_portrait_analytics_uses_persisted_longitudinal_evidence(db: Session) -> None:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    prefix = f"portrait-analytics-{uuid4().hex}"
    now = datetime.now(timezone.utc)
    rows = [
        ("事务原理", "transaction-basics", "quiz", 0.52, 76),
        ("事务原理", "transaction-basics", "quiz", 0.68, 44),
        ("并发调度", "serial-schedule", "assignment", 0.72, 20),
        ("并发调度", "serial-schedule", "teacher_assessment", 0.81, 2),
    ]
    for index, (label, point_id, source_type, score, age_days) in enumerate(rows):
        db.add(
            LearningEvidence(
                user_id=user.id,
                course_id=None,
                knowledge_point=point_id,
                display_name=label,
                knowledge_point_id=point_id,
                idempotency_key=f"{prefix}-{index}",
                source_type=source_type,
                source_id=f"{prefix}-{index}",
                event_type="graded",
                observed_at=now - timedelta(days=age_days),
                weight=1.0,
                score=score,
                payload={
                    "knowledge_identity": {"trusted": True},
                    "task_type": "project" if source_type == "assignment" else "quiz",
                    "task_execution": {
                        "completion_rate": min(1.0, score + 0.08),
                    },
                },
            )
        )
    db.commit()
    try:
        analytics = learning_report_service.build_portrait_analytics(
            db,
            user.id,
            now=now,
        )
        assert len(analytics.trend_labels) == 12
        assert len(analytics.capabilities) == 6
        assert analytics.evidence_count >= len(rows)
        assert analytics.overall_score is not None
        assert analytics.confidence is not None
        keys = {series.key for series in analytics.trend_series}
        assert "knowledge_understanding" in keys
        assert "problem_solving" in keys
        assert "self_regulation" in keys
        assert len(analytics.rhythm.activity) == 5
        assert all(len(row) == 7 for row in analytics.rhythm.activity)
        assert len(analytics.rhythm.focus_hours) == 6
        assert analytics.method_version == "portrait_analytics_v1"
    finally:
        db.exec(
            delete(LearningEvidence).where(
                LearningEvidence.source_id.startswith(prefix)
            )
        )
        db.commit()
