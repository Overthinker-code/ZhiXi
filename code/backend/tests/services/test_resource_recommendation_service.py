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


def test_six_card_batch_keeps_two_relevant_external_catalog_resources() -> None:
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
        for kind, suffix in (("book", "图书"), ("paper", "论文"), ("video", "讲座")):
            external = ExternalResource(
                title=f"事务隔离 {suffix}", source="Open Catalog", url=f"https://example.edu/{kind}",
                type=kind, provider="test", provider_kind=kind, subject="数据库",
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
        assert len({item.type for item in external_items}) >= 2


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
    ) == "https://example.org/public"


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


def test_catalog_discovery_maps_bounded_provenance_and_persists_library_metadata(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    discovery_module = importlib.import_module(
        "app.services.external_resource_discovery_service"
    )
    calls: list[str] = []
    archive_query = ""

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, url: str, **_kwargs: object) -> object:
            nonlocal archive_query
            calls.append(url)
            if url == discovery_module.INTERNET_ARCHIVE_URL:
                archive_query = str((_kwargs.get("params") or {}).get("q") or "")
            payloads = {
                discovery_module.OPEN_LIBRARY_URL: {"docs": [{"key": "/works/OL1W", "title": "事务处理入门", "author_name": ["Ada"], "first_publish_year": 2020, "language": ["zh"], "cover_i": 12}]},
                discovery_module.OPENALEX_URL: {"results": [{"id": "https://openalex.org/W1", "title": "Transaction Processing Study", "authorships": [{"author": {"display_name": "Grace"}}], "publication_year": 2023, "language": "en", "open_access": {"is_oa": True, "oa_status": "gold"}, "primary_location": {"license": "cc-by", "landing_page_url": "https://doi.org/10.1/example", "source": {"display_name": "Open Journal"}}, "abstract_inverted_index": {"Transaction": [0], "processing": [1]}}]},
                discovery_module.INTERNET_ARCHIVE_URL: {"response": {"docs": [{"identifier": "transaction-lecture", "title": "Transaction Processing Lecture", "creator": "University", "year": "2022", "language": "en", "licenseurl": "https://creativecommons.org/licenses/by/4.0/"}]}},
            }
            import httpx
            return httpx.Response(200, json=payloads[url], request=httpx.Request("GET", url))

    monkeypatch.setattr(discovery_module.httpx, "Client", FakeClient)

    with Session(engine) as session:
        discovered = resource_recommendation_service._discover_external(session, topic="事务")
        assert set(calls) == {
            discovery_module.OPEN_LIBRARY_URL,
            discovery_module.OPENALEX_URL,
            discovery_module.INTERNET_ARCHIVE_URL,
        }
        assert "mediatype:(movies)" in archive_query
        assert {(item.provider, item.type) for item in discovered} == {
            ("open_library", "book"), ("openalex", "paper"), ("internet_archive", "video")
        }
        paper = next(item for item in discovered if item.provider == "openalex")
        assert paper.license_status == "cc-by"
        assert paper.source_metadata["open_access"] is True

        user_id = uuid4()
        recommendation = PersonalizedResourceRecommendation(
            user_id=user_id, origin="external", title=paper.title, type=paper.type,
            subject=paper.subject, knowledge_point=paper.knowledge_point, source=paper.source,
            url=paper.url, external_resource_id=paper.id,
        )
        session.add(recommendation)
        session.commit()
        result = resource_recommendation_service.add_to_library(
            session, user_id=user_id, recommendation_id=recommendation.id
        )
        saved = session.get(Resource, result.resource_id)
        assert saved is not None
        assert saved.content["source_metadata"]["provider"] == "openalex"
        assert saved.content["source_metadata"]["canonical_url"] == paper.url


def test_catalog_discovery_tolerates_failure_and_invalid_payload(monkeypatch) -> None:
    discovery_module = importlib.import_module(
        "app.services.external_resource_discovery_service"
    )

    class FakeClient:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def get(self, url: str, **_kwargs: object) -> object:
            import httpx
            if url == discovery_module.OPEN_LIBRARY_URL:
                raise httpx.ConnectError("offline", request=httpx.Request("GET", url))
            if url == discovery_module.OPENALEX_URL:
                return httpx.Response(200, json={"results": "invalid"}, request=httpx.Request("GET", url))
            return httpx.Response(200, json={"response": {"docs": [{"identifier": "", "title": "<b>bad</b>"}]}}, request=httpx.Request("GET", url))

    monkeypatch.setattr(discovery_module.httpx, "Client", FakeClient)
    assert discovery_module.external_resource_discovery_service.discover(topic="事务") == []


def test_database_topic_alias_is_transparent_and_allows_english_catalog_title() -> None:
    discovery_module = importlib.import_module(
        "app.services.external_resource_discovery_service"
    )
    assert discovery_module.catalog_query_for_topic("事务隔离") == "database transaction isolation"

    ranked = rank_candidates(
        [Candidate(
            title="Database Transaction Isolation Levels", subject="Computer Science",
            source="OpenAlex", knowledge_point="事务隔离", modality="paper",
            difficulty="standard", origin="external",
        )],
        RecommendationContext(
            weak_points=["事务隔离"],
            external_topic_aliases={"事务隔离": "database transaction isolation"},
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
