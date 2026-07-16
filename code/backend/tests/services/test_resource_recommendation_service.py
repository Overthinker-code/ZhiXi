from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.models import (
    ExternalResource,
    PersonalizedResourceRecommendation,
    Resource,
    UserMemoryProfile,
)
from app.services.resource_recommendation_service import resource_recommendation_service


def test_recommendations_are_new_profile_candidates_or_external_not_old_resources() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        session.add(
            UserMemoryProfile(
                user_id=user_id,
                memory_profile={
                    "weak_points": ["TCP拥塞控制"],
                    "learning_style": "视觉化学习",
                    "current_goal": "掌握计算机网络",
                    "mastery_map": {"TCP拥塞控制": 0.35},
                },
            )
        )
        old_resource = Resource(
            title="以前生成的TCP知识图谱",
            type="knowledge_graph",
            knowledge_point="TCP拥塞控制",
            source="agent",
            uploader_id=user_id,
        )
        session.add(old_resource)
        session.add(
            ExternalResource(
                title="TCP拥塞控制动画讲解",
                source="verified-teaching-site",
                url="https://example.edu/tcp-congestion",
                type="video",
                knowledge_point="TCP拥塞控制",
                difficulty="foundation",
            )
        )
        session.commit()
        session.refresh(old_resource)

        result = resource_recommendation_service.recommend(
            session,
            user_id=user_id,
            limit=10,
        )

        assert result.agent_trace == ["student_profile_agent", "resource_agent", "multimodal_planner"]
        assert {item.origin for item in result.items} == {"generated", "external"}
        assert str(old_resource.id) not in {item.id for item in result.items}
        generated_types = {item.type for item in result.items if item.origin == "generated"}
        assert {"document", "question", "knowledge_graph", "video", "code", "image"} <= generated_types
        external = next(item for item in result.items if item.origin == "external")
        assert external.url == "https://example.edu/tcp-congestion"
        assert any("薄弱知识点" in signal for signal in result.profile_signals)

        resource_recommendation_service.favorite(
            session,
            user_id=user_id,
            recommendation_id=next(
                row.id
                for row in session.exec(select(PersonalizedResourceRecommendation)).all()
                if row.origin == "generated"
            ),
            favorite=True,
        )
        external_row = session.exec(
            select(PersonalizedResourceRecommendation).where(
                PersonalizedResourceRecommendation.origin == "external"
            )
        ).one()
        added = resource_recommendation_service.add_to_library(
            session,
            user_id=user_id,
            recommendation_id=external_row.id,
        )
        saved = session.get(Resource, added.resource_id)
        assert saved is not None
        assert saved.type == "external"
        assert saved.url == "https://example.edu/tcp-congestion"
