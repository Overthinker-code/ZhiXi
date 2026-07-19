from types import SimpleNamespace
import importlib
from uuid import UUID, uuid4

import pytest
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
from app.services.recommendation_ranking_service import Candidate, RecommendationContext, rank_candidates
from app.schemas.resource_recommendation import RecommendationItem


def test_recommendations_are_new_profile_candidates_or_external_not_old_resources() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        session.add(
            UserMemoryProfile(
                user_id=user_id,
                memory_profile={
                    "weak_points": ["数据结构"],
                    "learning_style": "视觉化学习",
                    "current_goal": "掌握数据结构",
                    "mastery_map": {"数据结构": 0.35},
                },
            )
        )
        old_resource = Resource(
            title="以前生成的数据结构知识图谱",
            type="knowledge_graph",
            knowledge_point="数据结构",
            source="agent",
            uploader_id=user_id,
        )
        session.add(old_resource)
        session.add(
            ExternalResource(
                title="数据结构",
                source="国家高等教育智慧教育平台",
                url="https://higher.smartedu.cn/course/622aca59bee70ef79f441af1",
                type="course",
                provider="smartedu",
                knowledge_point="数据结构",
                difficulty="foundation",
                created_by=user_id,
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
        assert external.url == "https://higher.smartedu.cn/course/622aca59bee70ef79f441af1"
        assert external.source == "国家高等教育智慧教育平台"
        assert external.source_domain == "higher.smartedu.cn"
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
        assert saved.url == "https://higher.smartedu.cn/course/622aca59bee70ef79f441af1"


def test_refresh_keeps_favorites_and_cools_down_explicitly_dismissed_pair(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    # This case verifies recommendation-state rotation, not public catalog
    # connectivity.  Keeping it offline makes the unit suite deterministic;
    # provider integration is exercised separately through the real API path.
    monkeypatch.setattr(
        resource_recommendation_service,
        "_discover_external",
        lambda *_args, **_kwargs: [],
    )
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


def test_six_card_batch_keeps_relevant_domestic_catalog_resources() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        session.add(UserMemoryProfile(user_id=user_id, memory_profile={"weak_points": ["事务隔离"]}))
        for item_type in ("document", "question", "knowledge_graph", "video", "code", "image"):
            session.add(PersonalizedResourceRecommendation(
                user_id=user_id, origin="generated", title=f"事务隔离 {item_type}",
                type=item_type, subject="数据库", knowledge_point="事务隔离",
            ))
        for url, provider, title in (
            (
                "https://higher.smartedu.cn/course/66d78e1a711dc30c34a0e833",
                "smartedu",
                "数据库系统",
            ),
            (
                "https://higher.smartedu.cn/course/687eb4e316c43a09c0e584a6",
                "smartedu",
                "数据库系统原理与开发",
            ),
            (
                "https://www.icourse163.org/course/WHU-1474003161",
                "icourse163",
                "数据库原理（理论）（武汉大学）",
            ),
        ):
            external = ExternalResource(
                title=title, source="国内课程目录", url=url,
                type="course", provider=provider, provider_kind="course", subject="数据库",
                knowledge_point="事务隔离", discovered_at=None,
            )
            session.add(external)
        session.commit()
        for external in session.exec(select(ExternalResource)).all():
            session.add(PersonalizedResourceRecommendation(
                user_id=user_id, origin="external", title=external.title, type=external.type,
                subject=external.subject, knowledge_point=external.knowledge_point,
                source=external.source, url=external.url, external_resource_id=external.id,
            ))
        session.commit()

        items = resource_recommendation_service.recommend(session, user_id=user_id, limit=6).items

        external_items = [item for item in items if item.origin == "external"]
        assert len(items) == 6
        assert len(external_items) >= 2
        assert all(item.url and "example.edu" not in item.url for item in external_items)


def test_external_catalog_alias_keeps_chinese_profile_reason_and_english_title() -> None:
    """A catalog alias may improve matching, but never replaces the learner's topic."""
    context = RecommendationContext(
        weak_points=["事务隔离"],
        external_topic_aliases={"事务隔离": "database transaction isolation"},
    )
    ranked = rank_candidates(
        [
            Candidate(
                title="Transaction Isolation in Database Systems",
                subject="数据库",
                source="OpenAlex",
                knowledge_point="事务隔离",
                modality="paper",
                difficulty="standard",
                origin="external",
            )
        ],
        context,
    )[0]

    assert ranked.external_relevant is True
    assert "事务隔离" in ranked.reason


def test_trusted_catalog_query_can_match_a_general_textbook_title() -> None:
    context = RecommendationContext(
        weak_points=["事务隔离"],
        external_topic_aliases={"事务隔离": "database transaction isolation"},
    )
    ranked = rank_candidates(
        [
            Candidate(
                title="Database System Concepts",
                subject="数据库",
                source="Open Library",
                knowledge_point="事务隔离",
                modality="book",
                difficulty="standard",
                origin="external",
                trusted_catalog_context="database transaction isolation",
            )
        ],
        context,
    )[0]

    assert ranked.external_relevant is True
    assert "事务隔离" in ranked.reason


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
        external = ExternalResource(
            title="数据库系统",
            source="国家高等教育智慧教育平台",
            url="https://higher.smartedu.cn/course/66d78e1a711dc30c34a0e833",
            type="course",
            provider="smartedu",
            provider_kind="course",
            subject="数据库",
            knowledge_point="ACID",
        )
        session.add(external)
        session.flush()
        item = PersonalizedResourceRecommendation(
            user_id=user_id,
            origin="external",
            title=external.title,
            type=external.type,
            subject="数据库",
            knowledge_point="ACID",
            url=external.url,
            source=external.source,
            external_resource_id=external.id,
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


def test_preview_returns_immediate_typed_outline_without_materializing(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
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

        monkeypatch.setattr(
            resource_recommendation_service,
            "_materialize_generated",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("preview must not generate")),
        )
        first = resource_recommendation_service.preview(
            session, user_id=user_id, recommendation_id=item.id
        )
        second = resource_recommendation_service.preview(
            session, user_id=user_id, recommendation_id=item.id
        )

        assert first.resource is None and second.resource is None
        assert first.content_preview is not None
        assert first.content_preview.type == "document"
        assert first.content_preview.sections[0]["kind"] == "outline"
        assert "学习重点" in first.message
        assert item.generation == 3
        assert item.status == "active"


def test_preview_reuses_existing_materialized_resource() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        resource = Resource(
            title="事务讲解", type="lecture_markdown", subject="数据库",
            file_name="transaction.md", file_path="generated_resources/transaction.md",
            content_type="text/markdown", source="agent", uploader_id=user_id,
        )
        session.add(resource)
        session.flush()
        item = PersonalizedResourceRecommendation(
            user_id=user_id, origin="generated", title="事务讲解", type="document",
            subject="数据库", knowledge_point="事务", resource_id=resource.id,
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        result = resource_recommendation_service.preview(session, user_id=user_id, recommendation_id=item.id)

        assert result.resource is not None and result.resource.id == resource.id
        assert result.content_preview is None


@pytest.mark.parametrize(
    ("resource_type", "expected_kind"),
    [
        ("document", "outline"),
        ("question", "sample_question"),
        ("knowledge_graph", "graph"),
        ("image", "graph"),
        ("video", "storyboard"),
        ("code", "code_task"),
    ],
)
def test_immediate_preview_has_nonempty_type_specific_content(
    resource_type: str, expected_kind: str
) -> None:
    item = PersonalizedResourceRecommendation(
        user_id=uuid4(), origin="generated", title="事务学习", type=resource_type,
        subject="数据库", knowledge_point="事务", difficulty="standard", reason="巩固薄弱点",
    )

    preview = resource_recommendation_service._instant_content_preview(item)

    assert preview.type == resource_type
    assert preview.sections and preview.sections[0]["kind"] == expected_kind
    assert preview.note and "学习重点" in preview.note


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


def test_external_url_rejects_embedded_credentials() -> None:
    assert resource_recommendation_service._safe_external_url(
        "https://reader:secret@example.org/private"
    ) is None
    assert resource_recommendation_service._safe_external_url(
        "https://example.org/public"
    ) is None
    assert resource_recommendation_service._safe_external_url(
        "https://higher.smartedu.cn/course/622aca59bee70ef79f441af1"
    ) == "https://higher.smartedu.cn/course/622aca59bee70ef79f441af1"


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
        session.add(resource)
        session.flush()
        item.resource_id = resource.id
        session.add(item)
        session.commit()
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


def test_catalog_discovery_maps_domestic_provenance_and_persists_library_metadata() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    discovery_module = importlib.import_module(
        "app.services.external_resource_discovery_service"
    )

    with Session(engine) as session:
        discovered = resource_recommendation_service._discover_external(session, topic="事务隔离")
        assert discovered
        assert {item.provider for item in discovered} <= {"smartedu", "icourse163"}
        assert all(item.source_metadata["entry_type"] == "resource" for item in discovered)
        course = next(item for item in discovered if item.provider == "smartedu")
        assert course.source_metadata["quality_tier"] == "national_platform"

        user_id = uuid4()
        recommendation = PersonalizedResourceRecommendation(
            user_id=user_id, origin="external", title=course.title, type=course.type,
            subject=course.subject, knowledge_point=course.knowledge_point, source=course.source,
            url=course.url, external_resource_id=course.id,
        )
        session.add(recommendation)
        session.commit()
        result = resource_recommendation_service.add_to_library(
            session, user_id=user_id, recommendation_id=recommendation.id
        )
        saved = session.get(Resource, result.resource_id)
        assert saved is not None
        assert saved.content["source_metadata"]["provider"] == course.provider
        assert saved.content["source_metadata"]["canonical_url"] == course.url


def test_catalog_discovery_tolerates_failure_and_invalid_payload(monkeypatch) -> None:
    discovery_module = importlib.import_module(
        "app.services.external_resource_discovery_service"
    )

    original = discovery_module.external_resource_discovery_service._provider_search_entry

    def failing_entry(provider: object, query: str) -> object:
        if getattr(provider, "key", "") == "xuetangx":
            raise RuntimeError("provider unavailable")
        return original(provider, query)

    monkeypatch.setattr(
        discovery_module.external_resource_discovery_service,
        "_provider_search_entry",
        failing_entry,
    )
    discovered = discovery_module.external_resource_discovery_service.discover(topic="机器学习")
    assert {item.provider for item in discovered} == {"smartedu", "icourse163", "bilibili"}
    assert all((item.metadata or {})["entry_type"] == "search_entry" for item in discovered)


def test_domestic_topic_query_keeps_chinese_and_ranks_chinese_catalog_title() -> None:
    discovery_module = importlib.import_module(
        "app.services.external_resource_discovery_service"
    )
    assert discovery_module.catalog_query_for_topic("事务隔离") == "事务隔离"

    ranked = rank_candidates(
        [Candidate(
            title="数据库系统：事务隔离级别", subject="数据库",
            source="国家高等教育智慧教育平台", knowledge_point="事务隔离", modality="course",
            difficulty="standard", origin="external",
            url="https://higher.smartedu.cn/course/66d78e1a711dc30c34a0e833",
            provider="smartedu", language="zh",
        )],
        RecommendationContext(
            weak_points=["事务隔离"],
        ),
    )
    assert ranked[0].external_relevant is True
    assert ranked[0].score > 0


def test_recommendation_response_source_metadata_is_additive() -> None:
    legacy = RecommendationItem.model_validate({
        "id": "legacy", "origin": "generated", "title": "事务讲解", "type": "document",
        "reason": "围绕事务学习",
    })
    external = RecommendationItem.model_validate({
        "id": "external", "origin": "external", "title": "Transaction Paper", "type": "paper",
        "reason": "关联事务隔离", "source_metadata": {"provider": "openalex", "open_access": True},
    })
    assert legacy.source_metadata == {}
    assert external.source_metadata == {"provider": "openalex", "open_access": True}
