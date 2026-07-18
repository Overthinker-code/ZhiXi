"""Safe, bounded discovery from fixed public open-resource catalogs.

This module only reads catalog JSON endpoints.  It never follows a result URL,
proxies target pages, or accepts a caller-controlled provider URL.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import re
from typing import Any, Iterable
from urllib.parse import urlparse

import httpx
from sqlmodel import select

from app.core.config import settings
from app.models import ExternalResource
from app.services.resource_subject_service import resolve_resource_subject


OPEN_LIBRARY_URL = "https://openlibrary.org/search.json"
OPENALEX_URL = "https://api.openalex.org/works"
INTERNET_ARCHIVE_URL = "https://archive.org/advancedsearch.php"

MAX_TITLE = 255
MAX_SUMMARY = 1200
MAX_AUTHORS = 8
MAX_METADATA_ITEMS = 8

# This deliberately small, reviewable map covers the concepts in the seeded
# 数据库系统原理 course.  It is not a translation model and is only used as a
# transparent catalog query alias; the original profile topic remains durable.
TOPIC_QUERY_ALIASES: dict[str, str] = {
    "事务隔离": "database transaction isolation",
    "范式与bcnf": "database normalization BCNF",
    "死锁处理": "database deadlock",
    "日志恢复": "database recovery logging checkpoint",
    "可串行化": "database serializability",
}

# The video catalog indexes lecture titles less precisely than article/book
# catalogs.  These reviewed, deliberately broad queries keep a video result
# useful for the same seeded-course topic without turning the endpoint into a
# general web search.
TOPIC_VIDEO_QUERY_ALIASES: dict[str, str] = {
    "事务隔离": "database transaction",
    "范式与bcnf": "database systems",
    "死锁处理": "database deadlock",
    "日志恢复": "database recovery",
    "可串行化": "database concurrency control",
}


def _text(value: object, limit: int) -> str:
    plain = re.sub(r"<[^>]*>", " ", str(value or ""))
    return " ".join(plain.split())[:limit]


def _safe_url(value: object) -> str | None:
    try:
        parsed = urlparse(str(value or "").strip())
    except (TypeError, ValueError):
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return parsed.geturl()[:1000]


def _strings(value: object, *, limit: int = MAX_AUTHORS, width: int = 160) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(_text(item, width) for item in value if _text(item, width)))[:limit]


def _year(value: object) -> int | None:
    try:
        result = int(str(value))
    except (TypeError, ValueError):
        return None
    return result if 1000 <= result <= 3000 else None


def _abstract(inverted: object) -> str:
    if not isinstance(inverted, dict):
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in inverted.items():
        if isinstance(positions, list):
            for position in positions[:12]:
                if isinstance(position, int) and position >= 0:
                    words.append((position, _text(word, 80)))
    return _text(" ".join(word for _, word in sorted(words)[:400]), MAX_SUMMARY)


def _metadata(value: object) -> dict[str, object]:
    """Keep a small, plain-text display subset of provider metadata."""
    if not isinstance(value, dict):
        return {}
    safe: dict[str, object] = {}
    for raw_key, raw_value in list(value.items())[:MAX_METADATA_ITEMS]:
        key = _text(raw_key, 80)
        if not key:
            continue
        if key.endswith(("url", "_url")):
            safe[key] = _safe_url(raw_value)
        elif isinstance(raw_value, (bool, int, float)) or raw_value is None:
            safe[key] = raw_value
        elif isinstance(raw_value, list):
            safe[key] = _strings(raw_value, limit=MAX_METADATA_ITEMS, width=200)
        else:
            safe[key] = _text(raw_value, 300) or None
    return safe


def catalog_query_for_topic(topic: object) -> str:
    normalized = "".join(_text(topic, 80).casefold().split())
    return TOPIC_QUERY_ALIASES.get(normalized, _text(topic, 80))


def catalog_video_query_for_topic(topic: object) -> str:
    normalized = "".join(_text(topic, 80).casefold().split())
    return TOPIC_VIDEO_QUERY_ALIASES.get(normalized, catalog_query_for_topic(topic))


@dataclass(frozen=True)
class CatalogCandidate:
    provider: str
    provider_kind: str
    title: str
    url: str
    summary: str = ""
    authors: list[str] | None = None
    year: int | None = None
    language: str | None = None
    license_status: str | None = None
    cover_url: str | None = None
    metadata: dict[str, object] | None = None


class ExternalResourceDiscoveryService:
    """Discover books, OA papers and video lectures with failure isolation."""

    def discover(self, *, topic: str) -> list[CatalogCandidate]:
        original_topic = _text(topic, 80)
        query = catalog_query_for_topic(original_topic)
        video_query = catalog_video_query_for_topic(original_topic)
        if len(original_topic) < 2 or len(query) < 2:
            return []
        timeout = httpx.Timeout(max(0.5, min(5.0, settings.EXTERNAL_DISCOVERY_TIMEOUT_SECONDS)))
        provider_limit = max(1, min(5, settings.EXTERNAL_DISCOVERY_MAX_RESULTS_PER_PROVIDER))
        headers = {"User-Agent": settings.EXTERNAL_DISCOVERY_USER_AGENT, "Accept": "application/json"}
        try:
            with httpx.Client(timeout=timeout, headers=headers, follow_redirects=False) as client:
                requests = (
                    (self._open_library, OPEN_LIBRARY_URL, {"q": query, "limit": provider_limit, "fields": "key,title,author_name,first_publish_year,language,cover_i,edition_key"}),
                    (self._openalex, OPENALEX_URL, {"search": query, "filter": "is_oa:true", "per-page": provider_limit, "select": "id,title,authorships,publication_year,language,open_access,primary_location,doi,abstract_inverted_index"}),
                    # Internet Archive's advanced-search parser requires the
                    # media type value to be grouped.  The previous shorthand
                    # silently returned zero video rows for valid course
                    # queries, which made the multi-format catalog look like
                    # a papers-only recommender.
                    (self._internet_archive, INTERNET_ARCHIVE_URL, {"q": f'title:({video_query}) AND mediatype:(movies)', "fl[]": ["identifier", "title", "creator", "year", "description", "language", "licenseurl"], "rows": provider_limit, "output": "json"}),
                )
                # Three fixed provider requests run together.  A provider
                # outage therefore costs one short timeout, not three.
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(client.get, url, params=params) for _, url, params in requests]
                    results: list[CatalogCandidate] = []
                    for (mapper, _, _), future in zip(requests, futures, strict=True):
                        try:
                            response = future.result()
                            response.raise_for_status()
                            results.extend(mapper(response.json()))
                        except (httpx.HTTPError, ValueError, TypeError):
                            continue
        except (httpx.HTTPError, ValueError, TypeError):
            return []
        seen: set[str] = set()
        if query != original_topic:
            results = [
                replace(item, metadata={**(item.metadata or {}), "query_alias": query})
                for item in results
            ]
        if video_query != query:
            results = [
                replace(
                    item,
                    metadata=(
                        {**(item.metadata or {}), "video_query_alias": video_query}
                        if item.provider == "internet_archive"
                        else item.metadata
                    ),
                )
                for item in results
            ]
        return [item for item in results if not (item.url in seen or seen.add(item.url))]

    @staticmethod
    def _open_library(payload: object) -> list[CatalogCandidate]:
        docs = payload.get("docs") if isinstance(payload, dict) else None
        result: list[CatalogCandidate] = []
        for doc in docs if isinstance(docs, list) else []:
            if not isinstance(doc, dict):
                continue
            key, title = _text(doc.get("key"), 160), _text(doc.get("title"), MAX_TITLE)
            url = _safe_url(f"https://openlibrary.org{key}") if key.startswith("/") else None
            cover = _safe_url(f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg") if doc.get("cover_i") else None
            if title and url:
                result.append(CatalogCandidate("open_library", "book", title, url, authors=_strings(doc.get("author_name")), year=_year(doc.get("first_publish_year")), language=(_strings(doc.get("language"), limit=1, width=32) or [None])[0], cover_url=cover, metadata={"catalog_key": key, "edition_key": (_strings(doc.get("edition_key"), limit=1) or [None])[0]}))
        return result

    @staticmethod
    def _openalex(payload: object) -> list[CatalogCandidate]:
        works = payload.get("results") if isinstance(payload, dict) else None
        result: list[CatalogCandidate] = []
        for work in works if isinstance(works, list) else []:
            if not isinstance(work, dict):
                continue
            title, url = _text(work.get("title"), MAX_TITLE), _safe_url(work.get("id"))
            oa = work.get("open_access") if isinstance(work.get("open_access"), dict) else {}
            location = work.get("primary_location") if isinstance(work.get("primary_location"), dict) else {}
            source = location.get("source") if isinstance(location.get("source"), dict) else {}
            authors = [authorship.get("author", {}).get("display_name") for authorship in work.get("authorships", []) if isinstance(authorship, dict) and isinstance(authorship.get("author"), dict)]
            if title and url and oa.get("is_oa") is True:
                result.append(CatalogCandidate("openalex", "paper", title, url, summary=_abstract(work.get("abstract_inverted_index")), authors=_strings(authors), year=_year(work.get("publication_year")), language=_text(work.get("language"), 32) or None, license_status=_text(location.get("license") or oa.get("oa_status"), 160) or "open_access", metadata={"doi": _text(work.get("doi"), 300) or None, "open_access": True, "landing_page": _safe_url(location.get("landing_page_url")), "venue": _text(source.get("display_name"), 160) or None}))
        return result

    @staticmethod
    def _internet_archive(payload: object) -> list[CatalogCandidate]:
        response = payload.get("response") if isinstance(payload, dict) else None
        docs = response.get("docs") if isinstance(response, dict) else None
        result: list[CatalogCandidate] = []
        for doc in docs if isinstance(docs, list) else []:
            if not isinstance(doc, dict):
                continue
            identifier, title = _text(doc.get("identifier"), 160), _text(doc.get("title"), MAX_TITLE)
            url = _safe_url(f"https://archive.org/details/{identifier}") if identifier else None
            if title and url:
                result.append(CatalogCandidate("internet_archive", "video", title, url, summary=_text(doc.get("description"), MAX_SUMMARY), authors=_strings(doc.get("creator") if isinstance(doc.get("creator"), list) else [doc.get("creator")]), year=_year(doc.get("year")), language=(_strings(doc.get("language"), limit=1, width=32) or [None])[0] if isinstance(doc.get("language"), list) else _text(doc.get("language"), 32) or None, license_status=_text(doc.get("licenseurl"), 160) or None, metadata={"identifier": identifier, "license_url": _safe_url(doc.get("licenseurl"))}))
        return result

    def persist(self, session: Any, *, topic: str, candidates: Iterable[CatalogCandidate]) -> list[ExternalResource]:
        existing = {row.url: row for row in session.exec(select(ExternalResource)).all()}
        now = datetime.now(timezone.utc)
        saved: list[ExternalResource] = []
        for candidate in candidates:
            if not _safe_url(candidate.url) or not candidate.title:
                continue
            record = existing.get(candidate.url)
            values = dict(
                title=candidate.title[:MAX_TITLE], source={"open_library": "Open Library", "openalex": "OpenAlex", "internet_archive": "Internet Archive"}[candidate.provider], url=candidate.url, type=candidate.provider_kind, subject=resolve_resource_subject(None, topic, candidate.title), knowledge_point=_text(topic, 160), difficulty="standard", recommend_reason=f"围绕你的“{_text(topic, 80)}”学习信号，匹配到{candidate.provider_kind}形式的公开资料。", provider=candidate.provider, provider_kind=candidate.provider_kind, summary=_text(candidate.summary, MAX_SUMMARY), authors=_strings(candidate.authors or []), published_year=candidate.year, language=_text(candidate.language, 32) or None, license_status=_text(candidate.license_status, 160) or None, cover_url=_safe_url(candidate.cover_url), source_metadata=_metadata(candidate.metadata), discovered_at=now, verified_at=now,
            )
            if record:
                for name, value in values.items():
                    setattr(record, name, value)
            else:
                record = ExternalResource(**values)
                session.add(record)
                existing[record.url] = record
            saved.append(record)
        if saved:
            session.commit()
            for record in saved:
                session.refresh(record)
        return saved


external_resource_discovery_service = ExternalResourceDiscoveryService()
