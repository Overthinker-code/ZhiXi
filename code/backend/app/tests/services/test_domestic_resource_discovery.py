from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.models import (
    ExternalResource,
    PersonalizedResourceRecommendation,
    UserMemoryProfile,
)
from app.services.external_resource_discovery_service import (
    CURATED_DOMESTIC_RESOURCES,
    DOMESTIC_PROVIDERS,
    allowed_domestic_url,
    external_resource_discovery_service,
)
from app.services.recommendation_ranking_service import (
    Candidate,
    RecommendationContext,
    rank_candidates,
)
from app.services.resource_recommendation_service import resource_recommendation_service


def _domestic_external(*, topic: str = "事务隔离") -> ExternalResource:
    return ExternalResource(
        title=f"国家高等教育智慧教育平台：搜索“{topic}”",
        source="国家高等教育智慧教育平台",
        url=f"https://higher.smartedu.cn/search?keyword={topic}",
        type="course",
        provider="smartedu",
        provider_kind="course",
        subject="数据库",
        knowledge_point=topic,
        language="zh-CN",
        source_metadata={"entry_type": "search_entry", "quality_tier": "national_platform"},
    )


def test_domestic_allowlist_requires_https_and_rejects_foreign_or_credential_urls() -> None:
    assert allowed_domestic_url("https://higher.smartedu.cn/course/123")
    assert allowed_domestic_url("https://www.icourse163.org/course/ABC")
    assert allowed_domestic_url("https://www.xuetangx.com/course/ABC")
    assert allowed_domestic_url("https://www.bilibili.com/video/BV1xx")
    assert allowed_domestic_url("http://higher.smartedu.cn/course/123") is None
    assert allowed_domestic_url("https://higher.smartedu.cn.evil.example/course") is None
    assert allowed_domestic_url("https://reader:secret@higher.smartedu.cn/course") is None
    assert allowed_domestic_url("https://openlibrary.org/works/OL1") is None
    assert allowed_domestic_url("https://github.com/example/course") is None
    assert allowed_domestic_url("https://www.youtube.com/watch?v=1") is None


def test_discovery_uses_chinese_topics_and_truthful_search_entries() -> None:
    candidates = external_resource_discovery_service.discover(topic="机器学习基础")
    assert {candidate.provider for candidate in candidates} == {
        provider.key for provider in DOMESTIC_PROVIDERS
    }
    assert all("机器学习基础" in candidate.title for candidate in candidates)
    assert all(candidate.metadata and candidate.metadata["entry_type"] == "search_entry" for candidate in candidates)
    assert all("搜索入口" in candidate.summary for candidate in candidates)
    assert all("database transaction" not in candidate.url for candidate in candidates)


def test_provider_failure_isolated(monkeypatch) -> None:
    original = external_resource_discovery_service._provider_search_entry

    def isolated(provider, query):
        if provider.key == "xuetangx":
            raise RuntimeError("provider unavailable")
        return original(provider, query)

    monkeypatch.setattr(external_resource_discovery_service, "_provider_search_entry", isolated)
    candidates = external_resource_discovery_service.discover(topic="机器学习基础")
    assert {candidate.provider for candidate in candidates} == {
        "smartedu", "icourse163", "bilibili"
    }


def test_persist_deduplicates_provider_search_entries() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    candidates = external_resource_discovery_service.discover(topic="机器学习基础")
    with Session(engine) as session:
        first = external_resource_discovery_service.persist(
            session, topic="机器学习基础", candidates=candidates
        )
        second = external_resource_discovery_service.persist(
            session, topic="机器学习基础", candidates=candidates
        )
        assert len(first) == len(DOMESTIC_PROVIDERS)
        assert len(second) == len(DOMESTIC_PROVIDERS)
        assert len(session.exec(select(ExternalResource)).all()) == len(DOMESTIC_PROVIDERS)


def test_curated_database_and_data_structure_courses_precede_search_entries() -> None:
    database = external_resource_discovery_service.discover(topic="事务隔离")
    stack = external_resource_discovery_service.discover(topic="栈")
    assert database and stack
    assert all(item.metadata and item.metadata["entry_type"] == "resource" for item in database)
    assert all(item.metadata and item.metadata["entry_type"] == "resource" for item in stack)
    assert any(item.title == "数据库系统" for item in database)
    assert any(item.title == "数据结构与算法Python版" for item in stack)
    assert len(CURATED_DOMESTIC_RESOURCES) >= 8


def test_domestic_ranking_explains_authority_chinese_and_search_entry_boundary() -> None:
    candidate = Candidate(
        title="国家高等教育智慧教育平台：搜索“事务隔离”",
        subject="数据库",
        source="国家高等教育智慧教育平台",
        knowledge_point="事务隔离",
        modality="course",
        difficulty="standard",
        origin="external",
        url="https://higher.smartedu.cn/search?keyword=%E4%BA%8B%E5%8A%A1%E9%9A%94%E7%A6%BB",
        provider="smartedu",
        language="zh-CN",
        entry_type="search_entry",
    )
    detail = rank_candidates([candidate], RecommendationContext(weak_points=["事务隔离"]))[0]
    assert detail.external_relevant is True
    assert "权威来源：国家高等教育智慧教育平台" in detail.reason
    assert "中文学习资源" in detail.reason
    assert "搜索入口" in detail.reason


def test_old_foreign_and_manual_records_never_enter_new_public_batch_or_replacement() -> None:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    user_id = uuid4()
    with Session(engine) as session:
        session.add(UserMemoryProfile(user_id=user_id, memory_profile={"weak_points": ["事务隔离"]}))
        foreign = ExternalResource(
            title="Transaction Isolation on foreign site",
            source="Open Library",
            url="https://openlibrary.org/works/OL1",
            type="book",
            provider="open_library",
            subject="数据库",
            knowledge_point="事务隔离",
        )
        own_manual_foreign = ExternalResource(
            title="个人收藏的境外资料",
            source="manual",
            url="https://github.com/example/course",
            type="document",
            provider="manual",
            created_by=user_id,
            subject="数据库",
            knowledge_point="事务隔离",
        )
        own_manual_domestic = ExternalResource(
            title="我收藏的数据结构课程",
            source="manual",
            url="https://higher.smartedu.cn/course/622aca59bee70ef79f441af1",
            type="course",
            provider="manual",
            created_by=user_id,
            subject="数据结构",
            knowledge_point="数据结构",
        )
        domestic = _domestic_external()
        session.add_all([foreign, own_manual_foreign, own_manual_domestic, domestic])
        session.commit()
        for external in (foreign, own_manual_foreign, domestic):
            session.add(
                PersonalizedResourceRecommendation(
                    user_id=user_id,
                    origin="external",
                    title=external.title,
                    type=external.type,
                    source=external.source,
                    url=external.url,
                    subject=external.subject,
                    knowledge_point=external.knowledge_point,
                    external_resource_id=external.id,
                )
            )
        session.commit()

        result = resource_recommendation_service.recommend(session, user_id=user_id, limit=10)
        public_urls = {item.url for item in result.items if item.origin == "external"}
        assert public_urls == {domestic.url}

        old_recommendation = session.exec(
            select(PersonalizedResourceRecommendation).where(
                PersonalizedResourceRecommendation.external_resource_id == foreign.id
            )
        ).one()
        replacement = resource_recommendation_service._next_external(
            session, item=old_recommendation, user_id=user_id
        )
        assert replacement is not None
        assert allowed_domestic_url(replacement.url) == replacement.url
        assert replacement.id not in {foreign.id, own_manual_foreign.id}

        refreshed = resource_recommendation_service.recommend(
            session, user_id=user_id, limit=6, refresh=True
        )
        refreshed_external_urls = {
            item.url for item in refreshed.items if item.origin == "external"
        }
        assert refreshed_external_urls
        assert foreign.url not in refreshed_external_urls
        assert all(allowed_domestic_url(url) == url for url in refreshed_external_urls)
        assert resource_recommendation_service._is_automatic_domestic_external(
            own_manual_domestic, user_id=user_id
        )
        assert not resource_recommendation_service._is_automatic_domestic_external(
            own_manual_domestic, user_id=uuid4()
        )
