from types import SimpleNamespace
from types import ModuleType
import sys
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.models import (
    Course,
    ExternalResource,
    LearningEvidence,
    PersonalizedResourceRecommendation,
    Resource,
    UserMemoryProfile,
    UserResourceConfig,
)
from app.services.quiz_service import quiz_service
from app.services.generated_knowledge_graph_service import knowledge_graph_service
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

        assert result.agent_trace == ["学习画像分析", "资料匹配", "学习形式规划"]
        assert {item.origin for item in result.items} == {"generated", "external"}
        assert str(old_resource.id) not in {item.id for item in result.items}
        generated_types = {item.type for item in result.items if item.origin == "generated"}
        assert {"document", "question", "knowledge_graph", "video", "code", "image"} <= generated_types
        external = next(item for item in result.items if item.origin == "external")
        assert external.url == "https://example.edu/tcp-congestion"
        assert external.source == "verified-teaching-site"
        assert external.source_domain == "example.edu"
        assert all(item.source == "智屿个性化生成" for item in result.items if item.origin == "generated")
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


def test_refresh_keeps_favorites_and_cools_down_explicitly_dismissed_pair() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        session.add(UserMemoryProfile(
            user_id=user_id,
            memory_profile={"weak_points": ["事务隔离", "死锁处理", "日志恢复"]},
        ))
        session.commit()
        initial = resource_recommendation_service.recommend(session, user_id=user_id, limit=6)
        favorite = initial.items[0]
        dismissed = initial.items[-1]
        resource_recommendation_service.favorite(
            session, user_id=user_id, recommendation_id=UUID(favorite.id), favorite=True,
        )
        resource_recommendation_service.dismiss(
            session, user_id=user_id, recommendation_id=UUID(dismissed.id),
        )

        refreshed = resource_recommendation_service.recommend(
            session, user_id=user_id, limit=6, refresh=True,
        )

        assert any(item.id == favorite.id and item.favorite for item in refreshed.items)
        assert not any(
            item.type == dismissed.type and item.knowledge_point == dismissed.knowledge_point
            for item in refreshed.items
        )


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


def test_preview_materializes_generated_resource_once_and_keeps_it_hidden(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    calls = 0
    with Session(engine) as session:
        item = PersonalizedResourceRecommendation(
            user_id=user_id,
            origin="generated",
            title="事务讲解",
            type="document",
            subject="数据库",
            knowledge_point="事务",
            generation=3,
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        def fake_generate(db: Session, request: object, *, owner_id: object) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            resource = Resource(
                title="事务讲解",
                type="lecture_markdown",
                subject="数据库",
                file_name="transaction.md",
                file_path="generated_resources/transaction.md",
                content_type="text/markdown",
                source="agent",
                uploader_id=owner_id,
            )
            db.add(resource)
            db.flush([resource])
            return SimpleNamespace(persisted_resource_ids=[resource.id])

        monkeypatch.setattr(resource_package_service, "generate", fake_generate)
        first = resource_recommendation_service.preview(
            session, user_id=user_id, recommendation_id=item.id
        )
        second = resource_recommendation_service.preview(
            session, user_id=user_id, recommendation_id=item.id
        )

        session.refresh(item)
        assert first.resource is not None and second.resource is not None
        config = session.exec(
            select(UserResourceConfig).where(
                UserResourceConfig.user_id == user_id,
                UserResourceConfig.resource_id == first.resource.id,
            )
        ).one()
        assert calls == 1
        assert first.resource.id == second.resource.id
        assert item.generation == 3
        assert item.status == "active"
        assert config.is_hidden is True
        assert "file_path" not in first.resource.model_dump()


def test_preview_is_owner_only_and_external_urls_are_sanitized() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    owner_id, other_id = uuid4(), uuid4()
    with Session(engine) as session:
        item = PersonalizedResourceRecommendation(
            user_id=owner_id,
            origin="external",
            title="不安全链接",
            type="document",
            source="不可信来源",
            url="javascript:alert(1)",
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        result = resource_recommendation_service.preview(
            session, user_id=owner_id, recommendation_id=item.id
        )
        assert result.resource is None
        assert result.recommendation.url is None
        assert result.recommendation.source == "来源暂不可用"
        try:
            resource_recommendation_service.preview(
                session, user_id=other_id, recommendation_id=item.id
            )
        except LookupError:
            pass
        else:
            raise AssertionError("another user must not preview this recommendation")


def test_knowledge_graph_preview_returns_only_validated_graph_content(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        item = PersonalizedResourceRecommendation(
            user_id=user_id,
            origin="generated",
            title="事务知识图谱",
            type="knowledge_graph",
            subject="数据库",
            knowledge_point="事务",
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        def fake_generate(db: Session, **kwargs: object) -> SimpleNamespace:
            resource = Resource(
                title="事务知识图谱",
                type="knowledge_graph",
                subject="数据库",
                content_type="application/json",
                content={
                    "nodes": [{"id": "transaction", "name": "事务", "mastery_score": None}],
                    "edges": [],
                    "file_path": "/private/graph.json",
                    "internal_note": "do not expose",
                },
                file_path="generated_resources/private.json",
                source="agent",
                uploader_id=user_id,
            )
            db.add(resource)
            db.flush([resource])
            return SimpleNamespace(resource_id=str(resource.id))

        monkeypatch.setattr(knowledge_graph_service, "generate", fake_generate)
        result = resource_recommendation_service.preview(
            session, user_id=user_id, recommendation_id=item.id
        )

        assert result.resource is not None
        assert result.resource.content == {
            "nodes": [{"id": "transaction", "name": "事务", "mastery_score": None}],
            "edges": [],
        }
        assert "file_path" not in result.resource.model_dump()
        assert "internal_note" not in result.resource.content

        invalid = Resource(
            title="损坏图谱",
            type="knowledge_graph",
            subject="数据库",
            content={"nodes": "not-a-list", "edges": []},
            uploader_id=user_id,
        )
        assert resource_recommendation_service._preview_resource(invalid).content is None


def test_external_discovery_persists_only_safe_title_and_url_metadata(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    calls: list[str] = []

    class FakeSearch:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def invoke(self, query: str) -> list[dict[str, str]]:
            calls.append(query)
            return [
                {"title": "事务公开课", "link": "https://example.edu/transaction"},
                {"title": "不安全", "link": "javascript:alert(1)"},
            ]

    community = ModuleType("langchain_community")
    tools = ModuleType("langchain_community.tools")
    tools.DuckDuckGoSearchResults = FakeSearch
    community.tools = tools
    monkeypatch.setitem(sys.modules, "langchain_community", community)
    monkeypatch.setitem(sys.modules, "langchain_community.tools", tools)

    with Session(engine) as session:
        discovered = resource_recommendation_service._discover_external(session, topic="事务")
        assert calls == ["事务 教学 视频 课程 练习"]
        assert len(discovered) == 1
        assert discovered[0].title == "事务公开课"
        assert discovered[0].url == "https://example.edu/transaction"
        assert discovered[0].source == "example.edu"
