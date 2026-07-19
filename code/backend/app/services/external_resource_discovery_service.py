"""Bounded discovery for auditable, China-accessible learning platforms.

This feature deliberately does not crawl arbitrary pages, proxy resource URLs,
or expose general web-search results as course materials.  The provider map is
small, reviewed, and HTTPS-only.  When a provider cannot return an audited
catalog item, we return a clearly-labelled *search entry* for that provider;
students still have to select a concrete resource on the provider's site.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Callable, Iterable
from urllib.parse import quote_plus, urlparse

from sqlmodel import select

from app.core.config import settings
from app.models import ExternalResource
from app.services.resource_subject_service import resolve_resource_subject


MAX_TITLE = 255
MAX_SUMMARY = 1200
MAX_AUTHORS = 8
MAX_METADATA_ITEMS = 8


@dataclass(frozen=True)
class DomesticProvider:
    key: str
    name: str
    domain: str
    kind: str
    quality_tier: str
    search_url: Callable[[str], str]


@dataclass(frozen=True)
class CuratedResource:
    """A reviewed concrete course page, never a scraped search result."""

    provider: str
    title: str
    url: str
    kind: str
    quality_tier: str
    topics: tuple[str, ...]
    summary: str


DOMESTIC_PROVIDERS: tuple[DomesticProvider, ...] = (
    DomesticProvider(
        "smartedu", "国家高等教育智慧教育平台", "higher.smartedu.cn", "course",
        "national_platform", lambda query: f"https://higher.smartedu.cn/search?keyword={quote_plus(query)}",
    ),
    DomesticProvider(
        "icourse163", "中国大学MOOC（爱课程）", "icourse163.org", "course",
        "national_mooc", lambda query: f"https://www.icourse163.org/search.htm?search={quote_plus(query)}",
    ),
    DomesticProvider(
        "xuetangx", "学堂在线", "xuetangx.com", "course",
        "university_mooc", lambda query: f"https://www.xuetangx.com/search?query={quote_plus(query)}",
    ),
    DomesticProvider(
        "bilibili", "哔哩哔哩", "bilibili.com", "video",
        "video_platform", lambda query: f"https://search.bilibili.com/all?keyword={quote_plus(query)}",
    ),
)
PROVIDER_BY_KEY = {provider.key: provider for provider in DOMESTIC_PROVIDERS}
ALLOWED_DOMESTIC_DOMAINS = frozenset(provider.domain for provider in DOMESTIC_PROVIDERS)

# Small, auditable directory.  Course titles and direct URLs below were
# checked against their official platform pages on 2026-07-19.  It is not a
# crawler and must grow only through a reviewed code change with a source URL.
CURATED_DOMESTIC_RESOURCES: tuple[CuratedResource, ...] = (
    CuratedResource(
        "smartedu", "数据结构", "https://higher.smartedu.cn/course/622aca59bee70ef79f441af1",
        "course", "national_platform",
        ("数据结构", "栈", "队列", "LIFO", "push", "pop", "线性表", "树", "图", "排序"),
        "国家高等教育智慧教育平台课程，覆盖线性表、栈、队列、树、图、查找和排序。",
    ),
    CuratedResource(
        "smartedu", "数据结构与算法Python版", "https://higher.smartedu.cn/course/66eb6480130d17e111b59462",
        "course", "national_platform",
        ("数据结构", "栈", "队列", "LIFO", "push", "pop", "Python", "算法"),
        "北京大学课程，包含栈和队列抽象数据类型及 Python 实现。",
    ),
    CuratedResource(
        "smartedu", "（第十四期）数据结构", "https://higher.smartedu.cn/course/68ac63b3d5f9b8b6cf61fc55",
        "course", "national_platform",
        ("数据结构", "栈", "队列", "线性表", "树", "图"),
        "国家高等教育智慧教育平台上的数据结构课程。",
    ),
    CuratedResource(
        "icourse163", "数据结构与算法（大连理工大学）", "https://www.icourse163.org/course/DUT-1205981804",
        "course", "national_mooc",
        ("数据结构", "栈", "队列", "LIFO", "push", "pop", "算法"),
        "中国大学MOOC 的大连理工大学数据结构与算法课程。",
    ),
    CuratedResource(
        "icourse163", "数据结构（南京师范大学）", "https://www.icourse163.org/course/NJNU-1474462161",
        "course", "national_mooc",
        ("数据结构", "栈", "队列", "LIFO", "push", "pop", "线性表"),
        "中国大学MOOC 的南京师范大学数据结构课程。",
    ),
    CuratedResource(
        "smartedu", "数据库系统", "https://higher.smartedu.cn/course/66d78e1a711dc30c34a0e833",
        "course", "national_platform",
        ("数据库系统", "事务隔离", "可串行化", "日志恢复", "范式", "BCNF", "并发控制", "事务", "恢复"),
        "国家高等教育智慧教育平台课程，包含规范化理论、恢复技术和并发控制。",
    ),
    CuratedResource(
        "smartedu", "数据库系统原理与开发", "https://higher.smartedu.cn/course/687eb4e316c43a09c0e584a6",
        "course", "national_platform",
        ("数据库系统", "事务隔离", "可串行化", "日志恢复", "范式", "BCNF", "SQL", "数据库设计"),
        "国家高等教育智慧教育平台课程，覆盖数据库系统原理、SQL、设计与开发。",
    ),
    CuratedResource(
        "icourse163", "数据库原理（理论）（武汉大学）", "https://www.icourse163.org/course/WHU-1474003161",
        "course", "national_mooc",
        ("数据库系统", "事务隔离", "可串行化", "日志恢复", "范式", "BCNF", "并发控制", "恢复"),
        "中国大学MOOC 的数据库原理课程，覆盖恢复技术、并发控制和关系数据理论。",
    ),
)


def _text(value: object, limit: int) -> str:
    plain = re.sub(r"<[^>]*>", " ", str(value or ""))
    return " ".join(plain.split())[:limit]


def allowed_domestic_url(value: object) -> str | None:
    """Return a normalized URL only for an HTTPS allowlisted platform host."""
    try:
        parsed = urlparse(str(value or "").strip())
    except (TypeError, ValueError):
        return None
    hostname = (parsed.hostname or "").casefold().removesuffix(".")
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or not any(hostname == domain or hostname.endswith(f".{domain}") for domain in ALLOWED_DOMESTIC_DOMAINS)
    ):
        return None
    return parsed.geturl()[:1000]


def provider_for_url(value: object) -> DomesticProvider | None:
    safe_url = allowed_domestic_url(value)
    if not safe_url:
        return None
    hostname = (urlparse(safe_url).hostname or "").casefold()
    return next(
        (
            provider
            for provider in DOMESTIC_PROVIDERS
            if hostname == provider.domain or hostname.endswith(f".{provider.domain}")
        ),
        None,
    )


def catalog_query_for_topic(topic: object) -> str:
    """Use the learner's Chinese topic directly; no English alias translation."""
    return _text(topic, 80)


# Kept as an empty compatibility export while callers migrate away from the
# former English-only catalog aliases.  It must never be populated by runtime
# model output or used to translate a learner's topic.
TOPIC_QUERY_ALIASES: dict[str, str] = {}


@dataclass(frozen=True)
class CatalogCandidate:
    provider: str
    provider_kind: str
    title: str
    url: str
    summary: str = ""
    authors: list[str] | None = None
    year: int | None = None
    language: str | None = "zh-CN"
    license_status: str | None = None
    cover_url: str | None = None
    metadata: dict[str, object] | None = None


class ExternalResourceDiscoveryService:
    """Create fixed, truthful provider search-entry candidates.

    Provider builders are isolated so a future audited provider parser can
    fail without suppressing the remaining fixed providers.
    """

    def discover(self, *, topic: str) -> list[CatalogCandidate]:
        query = catalog_query_for_topic(topic)
        if not query or (len(query) < 2 and not any("\u4e00" <= char <= "\u9fff" for char in query)):
            return []
        curated = self._curated_candidates(query)
        if curated:
            return curated
        candidates: list[CatalogCandidate] = []
        for provider in DOMESTIC_PROVIDERS:
            try:
                candidate = self._provider_search_entry(provider, query)
            except (TypeError, ValueError, RuntimeError):
                continue
            if candidate:
                candidates.append(candidate)
        seen: set[str] = set()
        return [item for item in candidates if not (item.url in seen or seen.add(item.url))]

    @staticmethod
    def _topic_matches(query: str, topic: str) -> bool:
        normalized_query = "".join(query.casefold().split())
        normalized_topic = "".join(topic.casefold().split())
        return bool(
            normalized_query
            and normalized_topic
            and (
                normalized_query in normalized_topic
                or normalized_topic in normalized_query
            )
        )

    def _curated_candidates(self, query: str) -> list[CatalogCandidate]:
        result: list[CatalogCandidate] = []
        for resource in CURATED_DOMESTIC_RESOURCES:
            if not any(self._topic_matches(query, topic) for topic in resource.topics):
                continue
            provider = PROVIDER_BY_KEY[resource.provider]
            url = allowed_domestic_url(resource.url)
            if not url:
                continue
            result.append(
                CatalogCandidate(
                    provider=resource.provider,
                    provider_kind=resource.kind,
                    title=resource.title,
                    url=url,
                    summary=resource.summary,
                    language="zh-CN",
                    metadata={
                        "entry_type": "resource",
                        "topics": list(resource.topics),
                        "provider_name": provider.name,
                        "quality_tier": resource.quality_tier,
                        "catalog_reviewed_at": "2026-07-19",
                    },
                )
            )
        return result

    @staticmethod
    def _provider_search_entry(provider: DomesticProvider, query: str) -> CatalogCandidate | None:
        url = allowed_domestic_url(provider.search_url(query))
        if not url:
            return None
        return CatalogCandidate(
            provider=provider.key,
            provider_kind=provider.kind,
            title=f"{provider.name}：搜索“{query}”",
            url=url,
            summary=(
                f"这是 {provider.name} 的站内搜索入口，不代表某一具体课程或视频已被平台核验。"
                "请在打开后查看课程发布方、章节和适用范围。"
            ),
            language="zh-CN",
            metadata={
                "entry_type": "search_entry",
                "query": query,
                "provider_name": provider.name,
                "quality_tier": provider.quality_tier,
            },
        )

    def persist(self, session: Any, *, topic: str, candidates: Iterable[CatalogCandidate]) -> list[ExternalResource]:
        existing = {row.url: row for row in session.exec(select(ExternalResource)).all()}
        now = datetime.now(timezone.utc)
        saved: list[ExternalResource] = []
        for candidate in candidates:
            safe_url = allowed_domestic_url(candidate.url)
            provider = PROVIDER_BY_KEY.get(candidate.provider)
            if not safe_url or not provider or not candidate.title:
                continue
            metadata = dict(candidate.metadata or {})
            entry_type = str(metadata.get("entry_type") or "search_entry")
            if entry_type not in {"resource", "search_entry"}:
                continue
            metadata["entry_type"] = entry_type
            metadata["provider_name"] = provider.name
            metadata["quality_tier"] = provider.quality_tier
            values = dict(
                title=_text(candidate.title, MAX_TITLE),
                source=provider.name,
                url=safe_url,
                type=provider.kind,
                subject=resolve_resource_subject(None, topic, candidate.title),
                knowledge_point=_text(topic, 160),
                difficulty="standard",
                recommend_reason=f"围绕“{_text(topic, 80)}”的国内正规平台搜索入口。",
                provider=provider.key,
                provider_kind=provider.kind,
                summary=_text(candidate.summary, MAX_SUMMARY),
                authors=[],
                published_year=None,
                language="zh-CN",
                license_status=None,
                cover_url=None,
                source_metadata=metadata,
                discovered_at=now,
                verified_at=now,
            )
            record = existing.get(safe_url)
            if record:
                for name, value in values.items():
                    setattr(record, name, value)
            else:
                record = ExternalResource(**values)
                session.add(record)
                existing[safe_url] = record
            saved.append(record)
        if saved:
            session.commit()
            for record in saved:
                session.refresh(record)
        return saved


external_resource_discovery_service = ExternalResourceDiscoveryService()
