"""Idempotent catalog seed for the local Software Engineering course corpus.

The large source corpus stays outside Git.  Resource rows point at a strictly
bounded ``course_sources/`` namespace which the resource endpoint resolves
under the repository's ``原始资料`` directory.  No arbitrary filesystem path
is accepted.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlmodel import Session, select

from app.models import Resource, User


SOFTWARE_ENGINEERING_COURSE_ID = UUID("c1111111-1111-4111-9111-111111111107")
COURSE_SOURCE_PREFIX = "course_sources/"
COURSE_SOURCE_NAME = "课程内置资料"


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


def course_source_root() -> Path:
    return repository_root() / "原始资料"


def resolve_course_source(relative_path: str) -> Path:
    """Resolve a stored course source without permitting path traversal."""
    if not relative_path.startswith(COURSE_SOURCE_PREFIX):
        raise ValueError("不是课程内置资料路径")
    root = course_source_root().resolve()
    target = (root / relative_path.removeprefix(COURSE_SOURCE_PREFIX)).resolve()
    if target == root or root not in target.parents:
        raise ValueError("课程资料路径无效")
    return target


def is_shared_course_resource(resource: Resource) -> bool:
    return (
        getattr(resource, "course_id", None) == SOFTWARE_ENGINEERING_COURSE_ID
        and getattr(resource, "source", None) == COURSE_SOURCE_NAME
        and str(getattr(resource, "file_path", "")).startswith(COURSE_SOURCE_PREFIX)
    )


def _chapter_from_name(name: str) -> tuple[str, str]:
    match = re.search(r"ch(\d{2})[_-]([^_]+)", name, re.IGNORECASE)
    if not match:
        return "课程拓展", Path(name).stem
    chapter = int(match.group(1))
    title = match.group(2).replace("实 现", "实现").replace("维 护", "维护")
    return f"第{chapter}章 {title}", title


def _resource_id(kind: str, relative_path: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"zhixi:software-engineering:{kind}:{relative_path}")


def _upsert_local_resource(
    session: Session,
    *,
    uploader: User,
    path: Path,
    kind: str,
    title: str,
    chapter: str,
    knowledge_point: str,
) -> bool:
    relative = path.relative_to(course_source_root()).as_posix()
    resource_id = _resource_id(kind, relative)
    resource = session.get(Resource, resource_id)
    created = resource is None
    previous_content = resource.content if resource and isinstance(resource.content, dict) else {}
    unchanged = bool(resource and resource.file_size == path.stat().st_size)
    page_count = previous_content.get("page_count") if unchanged else None
    if kind == "ppt" and path.suffix.lower() == ".pdf" and not page_count:
        try:
            from pypdf import PdfReader

            page_count = len(PdfReader(str(path), strict=False).pages)
        except Exception:
            page_count = None
    values = {
        "title": title[:255],
        "type": kind,
        "subject": "软件工程导论",
        "file_name": path.name[:255],
        "file_path": f"{COURSE_SOURCE_PREFIX}{relative}",
        "file_size": path.stat().st_size,
        "content_type": (
            "application/pdf"
            if path.suffix.lower() == ".pdf"
            else "text/markdown; charset=utf-8"
        ),
        "course_id": SOFTWARE_ENGINEERING_COURSE_ID,
        "knowledge_point": knowledge_point[:160],
        "difficulty": "standard",
        "source": COURSE_SOURCE_NAME,
        "content": {
            "category": kind,
            "chapter": chapter,
            "course_material": True,
            "source_scope": "local_course_corpus",
            "page_count": page_count,
        },
        "uploader_id": uploader.id,
    }
    if resource is None:
        resource = Resource(id=resource_id, **values)
    else:
        for key, value in values.items():
            setattr(resource, key, value)
    session.add(resource)
    return created


NETWORK_RESOURCES = (
    {
        "key": "bilibili-complete-course",
        "title": "软件工程导论公开课（50讲）",
        "url": "https://www.bilibili.com/video/BV1Ns41177VM/",
        "source": "哔哩哔哩",
        "kind": "external_video",
        "knowledge_point": "软件生命周期与结构化分析",
        "summary": "覆盖软件工程基础、生命周期、结构化分析、设计、测试、UML 与项目管理，适合系统补课。",
        "tags": ["软件工程", "生命周期", "结构化分析", "UML", "视频"],
    },
    {
        "key": "bilibili-uml-practice",
        "title": "软件工程、软件测试与 UML 基础课程",
        "url": "https://www.bilibili.com/video/BV1s541157qw/",
        "source": "哔哩哔哩",
        "kind": "external_video",
        "knowledge_point": "UML 与软件测试",
        "summary": "包含 UML 用例图、类图、顺序图、活动图以及软件测试专题，适合图形题和薄弱点追练。",
        "tags": ["UML", "软件测试", "用例图", "类图", "视频"],
    },
    {
        "key": "bilibili-lifecycle-models",
        "title": "软件生命周期模型对比学习",
        "url": "https://www.bilibili.com/video/BV1Dg411K77t/",
        "source": "哔哩哔哩",
        "kind": "external_video",
        "knowledge_point": "软件生命周期模型",
        "summary": "以对比方式复习常见过程模型，适合偏好图解、对照表和短时复盘的学习者。",
        "tags": ["生命周期", "过程模型", "对比学习", "视频"],
    },
    {
        "key": "xiaohongshu-se-notes",
        "title": "小红书｜软件工程导论学习笔记",
        "url": "https://www.xiaohongshu.com/search_result?keyword=%E8%BD%AF%E4%BB%B6%E5%B7%A5%E7%A8%8B%E5%AF%BC%E8%AE%BA%20%E5%AD%A6%E4%B9%A0%E7%AC%94%E8%AE%B0",
        "source": "小红书",
        "kind": "external_note",
        "knowledge_point": "软件工程导论复习笔记",
        "summary": "进入平台查看公开发布的软件工程导论笔记；结果会随平台更新，使用前请核对作者与内容质量。",
        "tags": ["软件工程", "学习笔记", "复习", "图解"],
    },
    {
        "key": "xiaohongshu-uml-notes",
        "title": "小红书｜UML 与需求分析笔记",
        "url": "https://www.xiaohongshu.com/search_result?keyword=UML%20%E9%9C%80%E6%B1%82%E5%88%86%E6%9E%90%20%E7%AC%94%E8%AE%B0",
        "source": "小红书",
        "kind": "external_note",
        "knowledge_point": "UML 与需求分析",
        "summary": "进入平台浏览 UML、用例图和需求分析主题笔记，适合作为课程资料之外的多视角补充。",
        "tags": ["UML", "需求分析", "用例图", "笔记"],
    },
)


def _upsert_network_resource(session: Session, *, uploader: User, item: dict) -> bool:
    resource_id = uuid5(NAMESPACE_URL, f"zhixi:software-engineering:network:{item['key']}")
    resource = session.get(Resource, resource_id)
    created = resource is None
    values = {
        "title": item["title"],
        "type": item["kind"],
        "subject": "软件工程导论",
        "file_name": "",
        "file_path": "",
        "file_size": 0,
        "content_type": "text/uri-list",
        "course_id": SOFTWARE_ENGINEERING_COURSE_ID,
        "url": item["url"],
        "knowledge_point": item["knowledge_point"],
        "difficulty": "standard",
        "source": item["source"],
        "content": {
            "external": True,
            "provider": item["source"],
            "kind": "video" if item["kind"] == "external_video" else "note",
            "summary": item["summary"],
            "profile_tags": item["tags"],
            "canonical_url": item["url"],
            "verified_at": "2026-07-19",
        },
        "uploader_id": uploader.id,
    }
    if resource is None:
        resource = Resource(id=resource_id, **values)
    else:
        for key, value in values.items():
            setattr(resource, key, value)
    session.add(resource)
    return created


def seed_software_engineering_course_resources(
    session: Session, *, uploader: User
) -> dict[str, int]:
    """Index local course files and reviewed external links into Resource."""
    root = course_source_root()
    counts = {"ppt": 0, "notes": 0, "questions": 0, "network": 0}
    if root.is_dir():
        specs = (
            ("ppt", root / "PPT", "*.pdf", "课件"),
            ("lecture_markdown", root / "学习笔记", "*.md", "学习笔记"),
            ("practice_markdown", root / "课后习题", "*.md", "课后习题"),
        )
        for kind, folder, pattern, suffix in specs:
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob(pattern)):
                chapter, point = _chapter_from_name(path.name)
                title = path.stem if kind == "ppt" else f"{chapter} · {suffix}"
                _upsert_local_resource(
                    session,
                    uploader=uploader,
                    path=path,
                    kind=kind,
                    title=title,
                    chapter=chapter,
                    knowledge_point=point,
                )
                counts[{"ppt": "ppt", "lecture_markdown": "notes", "practice_markdown": "questions"}[kind]] += 1
    for item in NETWORK_RESOURCES:
        _upsert_network_resource(session, uploader=uploader, item=item)
        counts["network"] += 1
    session.commit()
    return counts
