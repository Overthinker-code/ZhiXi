from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.models import (
    Course,
    ExternalResource,
    LearningEvidence,
    PersonalizedResourceRecommendation,
    Resource,
    UserMemoryProfile,
)
from app.services.quiz_service import quiz_service
from app.services.resource_package_service import resource_package_service
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


def test_database_recommendation_materialization_keeps_course_scope(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    course = Course(
        name="数据库系统原理",
        identifier=f"DB-{uuid4().hex[:8]}",
        ud_id=uuid4(),
    )
    captured: dict[str, object] = {}
    with Session(engine) as session:
        session.add(course)
        item = PersonalizedResourceRecommendation(
            user_id=user_id,
            origin="generated",
            title="ACID 专项练习",
            type="question",
            subject="数据库",
            knowledge_point="ACID",
        )
        session.add(item)
        session.commit()
        session.refresh(course)
        session.refresh(item)

        def fake_generate(db: Session, **kwargs: object) -> SimpleNamespace:
            captured.update(kwargs)
            resource = Resource(
                title="ACID 专项练习",
                type="question",
                subject="数据库",
                knowledge_point="ACID",
                source="agent",
                uploader_id=user_id,
                course_id=kwargs.get("course_id"),
            )
            db.add(resource)
            db.flush([resource])
            return SimpleNamespace(resource_id=resource.id)

        monkeypatch.setattr(quiz_service, "generate", fake_generate)
        result = resource_recommendation_service.add_to_library(
            session,
            user_id=user_id,
            recommendation_id=item.id,
        )

        resource = session.get(Resource, result.resource_id)
        evidence = session.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == user_id,
                LearningEvidence.source_type == "resource_interaction",
            )
        ).one()
        assert captured["course_id"] == course.id
        assert resource is not None and resource.course_id == course.id
        assert evidence.course_id == course.id
        assert evidence.payload["course_id"] == str(course.id)


def test_document_recommendation_passes_course_id_to_resource_request(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    course = Course(
        name="数据库系统原理",
        identifier=f"DB-{uuid4().hex[:8]}",
        ud_id=uuid4(),
    )
    captured: dict[str, object] = {}
    with Session(engine) as session:
        session.add(course)
        item = PersonalizedResourceRecommendation(
            user_id=user_id,
            origin="generated",
            title="事务讲解",
            type="document",
            subject="数据库",
            knowledge_point="事务 ACID",
        )
        session.add(item)
        session.commit()
        session.refresh(course)
        session.refresh(item)

        def fake_generate(
            db: Session, request: object, *, owner_id: object
        ) -> SimpleNamespace:
            captured["request"] = request
            resource = Resource(
                title="事务讲解",
                type="document",
                subject="数据库",
                knowledge_point="事务 ACID",
                source="agent",
                uploader_id=owner_id,
                course_id=request.course_id,
            )
            db.add(resource)
            db.flush([resource])
            return SimpleNamespace(persisted_resource_ids=[resource.id])

        monkeypatch.setattr(resource_package_service, "generate", fake_generate)
        result = resource_recommendation_service.add_to_library(
            session,
            user_id=user_id,
            recommendation_id=item.id,
        )

        request = captured["request"]
        resource = session.get(Resource, result.resource_id)
        assert request.course_id == course.id
        assert resource is not None and resource.course_id == course.id


def test_external_recommendation_resource_and_evidence_keep_course_scope() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    course = Course(
        name="数据库系统原理",
        identifier=f"DB-{uuid4().hex[:8]}",
        ud_id=uuid4(),
    )
    with Session(engine) as session:
        session.add(course)
        item = PersonalizedResourceRecommendation(
            user_id=user_id,
            origin="external",
            title="ACID 公开课",
            type="video",
            subject="数据库",
            knowledge_point="ACID",
            url="https://example.edu/acid",
            source="example.edu",
        )
        session.add(item)
        session.commit()
        session.refresh(course)
        session.refresh(item)

        result = resource_recommendation_service.add_to_library(
            session,
            user_id=user_id,
            recommendation_id=item.id,
        )

        resource = session.get(Resource, result.resource_id)
        evidence = session.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == user_id,
                LearningEvidence.source_type == "resource_interaction",
            )
        ).one()
        assert resource is not None and resource.course_id == course.id
        assert evidence.course_id == course.id


def test_course_resolution_does_not_guess_from_vague_or_ambiguous_text() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all(
            [
                Course(
                    name="数据库系统原理",
                    identifier=f"DB-{uuid4().hex[:8]}",
                    ud_id=uuid4(),
                ),
                Course(
                    name="数据库应用开发",
                    identifier=f"DBAPP-{uuid4().hex[:8]}",
                    ud_id=uuid4(),
                ),
            ]
        )
        session.commit()

        assert resource_recommendation_service._resolve_course_id(
            session, subject="数据", topic="事务"
        ) is None
        assert resource_recommendation_service._resolve_course_id(
            session, subject="数据库", topic="ACID"
        ) is None
