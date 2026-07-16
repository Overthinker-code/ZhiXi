from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session

from app.models.profile_update_event import ProfileUpdateEvent
from app.models.user import User  # noqa: F401
from app.models.user_memory_profile import UserMemoryProfile  # noqa: F401
from app.services.profile_update_service import profile_update_service


def _session():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    ProfileUpdateEvent.__table__.create(engine)
    return Session(engine)


def test_chat_analysis_extracts_difficulty_and_preferences() -> None:
    analysis = profile_update_service.analyze_chat_turn(
        user_message="我还是不理解二阶段锁，能用案例一步一步讲解吗？",
        assistant_message="可以。",
        course="数据库",
        knowledge_point="二阶段锁",
    )

    assert analysis["knowledge_point"] == "二阶段锁"
    assert analysis["difficulty"] == "high"
    assert analysis["weakness"] == "概念理解"
    assert analysis["preference_signals"]["example_preference"] == 1.0
    assert analysis["preference_signals"]["step_by_step_preference"] == 1.0


def test_incremental_update_preserves_profile_and_records_audit_event() -> None:
    db = _session()
    user_id = uuid4()
    initial = UserMemoryProfile(
        user_id=user_id,
        memory_profile={
            "school": "演示大学",
            "learning_preference": {"video_preference": 0.6},
            "knowledge_state": {"事务隔离": 0.52},
        },
    )
    db.add(initial)
    db.commit()

    profile, event = profile_update_service.apply_incremental_update(
        db,
        user_id=user_id,
        session_id="session-1",
        analysis={
            "knowledge_point": "事务隔离",
            "observed_mastery": 0.32,
            "difficulty": "high",
            "weakness": "概念理解",
            "preference_signals": {"video_preference": 1.0},
            "behavior_signals": {"chat_turns": 1},
            "cognitive_style": "视觉化理解",
        },
        alpha=0.1,
    )

    assert profile["school"] == "演示大学"
    assert profile["learning_preference"]["video_preference"] == 0.7
    assert profile["knowledge_state"]["事务隔离"] == 0.5
    assert "事务隔离" in profile["weak_points"]
    assert profile["cognitive_style"] == "视觉化理解"
    assert event.before_snapshot["school"] == "演示大学"
    assert event.after_snapshot["profile_version"] == 1


def test_repeated_feedback_updates_instead_of_overwriting() -> None:
    db = _session()
    user_id = uuid4()
    analysis = {
        "preference_signals": {"video_preference": 1.0},
        "behavior_signals": {"resource_feedback_count": 1},
    }
    first, _ = profile_update_service.apply_incremental_update(
        db, user_id=user_id, analysis=analysis, alpha=0.1, source_type="feedback"
    )
    second, _ = profile_update_service.apply_incremental_update(
        db, user_id=user_id, analysis=analysis, alpha=0.1, source_type="feedback"
    )

    assert first["learning_preference"]["video_preference"] == 0.6
    assert second["learning_preference"]["video_preference"] == 0.7
    assert second["learning_behavior"]["resource_feedback_count"] == 2.0
    assert second["profile_version"] == 2
