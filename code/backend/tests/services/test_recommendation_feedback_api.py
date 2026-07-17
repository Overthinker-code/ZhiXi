from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.api.v1.endpoints.resource_hub import recommendation_feedback
from app.models import LearningEvidence, PersonalizedResourceRecommendation, PracticeRecord, UserMemoryProfile
from app.schemas.resource_recommendation import RecommendationFeedbackRequest
from app.services.resource_recommendation_service import resource_recommendation_service
from app.services.recommendation_ranking_service import RecommendationContext
from app.services.user_memory_profile_service import user_memory_profile_service


def test_source_opened_feedback_is_enumerated_and_owner_scoped() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    owner, other = uuid4(), uuid4()
    with Session(engine) as session:
        item = PersonalizedResourceRecommendation(
            user_id=owner, origin="external", title="事务隔离讲解", type="video",
            subject="数据库", knowledge_point="事务隔离", source="example.edu",
            url="https://example.edu/transaction",
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        with pytest.raises(HTTPException) as error:
            recommendation_feedback(
                session=session, current_user=SimpleNamespace(id=other), recommendation_id=item.id,
                request=RecommendationFeedbackRequest(action="source_opened"),
            )
        assert error.value.status_code == 404
    with pytest.raises(ValidationError):
        RecommendationFeedbackRequest.model_validate({"action": "arbitrary_weight"})


def test_repeated_preview_is_idempotent_and_never_changes_mastery() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        session.add(UserMemoryProfile(user_id=user_id, memory_profile={"mastery_map": {"可信评分": 0.66}}))
        item = PersonalizedResourceRecommendation(
            user_id=user_id, origin="external", title="事务隔离讲解", type="video",
            subject="数据库", knowledge_point="事务隔离", source="example.edu",
            url="https://example.edu/transaction",
        )
        session.add(item)
        session.commit()
        resource_recommendation_service.preview(session, user_id=user_id, recommendation_id=item.id)
        resource_recommendation_service.preview(session, user_id=user_id, recommendation_id=item.id)
        events = session.query(LearningEvidence).filter(LearningEvidence.event_type == "recommendation_previewed").all()
        profile = session.exec(select(UserMemoryProfile).where(UserMemoryProfile.user_id == user_id)).one()
        assert len(events) == 1
        assert profile is not None and profile.memory_profile["mastery_map"] == {"可信评分": 0.66}
        assert profile.memory_profile["recommendation_feedback"]["modalities"]["video"]["affinity"] > 0


def test_public_recommendations_keep_mmr_order_after_favorite_bonus(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        rows = [
            PersonalizedResourceRecommendation(user_id=user_id, origin="generated", title="事务隔离讲解", type="document", knowledge_point="事务隔离", favorite=True),
            PersonalizedResourceRecommendation(user_id=user_id, origin="generated", title="事务隔离案例", type="document", knowledge_point="事务隔离"),
            PersonalizedResourceRecommendation(user_id=user_id, origin="generated", title="事务隔离视频", type="video", knowledge_point="事务隔离"),
        ]
        session.add_all(rows)
        session.commit()
        monkeypatch.setattr(
            resource_recommendation_service,
            "_recommendation_context",
            lambda *_args, **_kwargs: RecommendationContext(weak_points=["事务隔离"]),
        )
        result = resource_recommendation_service._rank_public_items(
            session, user_id=user_id, items=rows, limit=3
        )
        assert result[0].id == str(rows[0].id)
        # The second document is still relevant, but the public order retains
        # MMR's topic/modality diversity instead of a final score-only sort.
        assert result[1].id == str(rows[2].id)


def test_behavioral_preference_uses_decayed_signed_feedback_and_keeps_explicit_interest() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        session.add(
            UserMemoryProfile(
                user_id=user_id,
                memory_profile={
                    "interest_topics": ["显式兴趣"],
                    "explicit_interest_topics": ["显式兴趣"],
                },
            )
        )
        for index, (event_type, observed_at, topic, modality, signed) in enumerate([
            ("recommendation_dismissed", now - timedelta(days=60), "旧负主题", "document", -0.8),
            ("recommendation_dismissed", now - timedelta(days=59), "旧负主题", "document", -0.8),
            ("resource_favorited", now, "新正主题", "video", 0.85),
            ("source_opened", now - timedelta(minutes=2), "新正主题", "video", 0.35),
        ]):
            session.add(LearningEvidence(
                user_id=user_id, knowledge_point=topic, display_name=topic,
                idempotency_key=f"feedback-{index}", source_type="resource_interaction",
                source_id=f"resource-{index}", event_type=event_type, observed_at=observed_at,
                payload={"signed_preference_weight": signed, "resource_type": modality, "topic": topic},
            ))
        session.flush()
        evidence_id = session.exec(select(LearningEvidence)).first().id
        user_memory_profile_service.apply_behavioral_evidence_update(
            session, user_id=user_id, evidence_id=evidence_id, observed_at=now
        )
        session.commit()
        profile = session.exec(select(UserMemoryProfile).where(UserMemoryProfile.user_id == user_id)).one().memory_profile
        assert "显式兴趣" in profile["interest_topics"]
        assert "新正主题" in profile["interest_topics"]
        assert "旧负主题" not in profile["interest_topics"]
        assert profile["resource_preference"] == "video"
        dimension = profile["profile_dimensions"]["resource_preference"]["value"]
        assert dimension["method_version"] == "recommendation_feedback_v1"
        assert dimension["affinity_summary"][0]["sample_count"] >= 2


def test_recommendation_context_uses_latest_practice_observation_per_topic() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        # A poor historical attempt must not override the newest successful one.
        session.add_all([
            PracticeRecord(user_id=user_id, subject="数据库", topic="事务隔离", total_questions=10, correct_count=2, practiced_at=now - timedelta(days=10)),
            PracticeRecord(user_id=user_id, subject="数据库", topic="事务隔离", total_questions=10, correct_count=9, practiced_at=now),
        ])
        session.commit()
        context = resource_recommendation_service._recommendation_context(session, user_id=user_id)
        assert "事务隔离" not in context.practice_gaps
