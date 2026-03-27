from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


def _visits_data():
    return [
        {"x": "2025-05-23", "y": 1234},
        {"x": "2025-05-24", "y": 1380},
        {"x": "2025-05-25", "y": 1498},
        {"x": "2025-05-26", "y": 1572},
        {"x": "2025-05-27", "y": 1641},
        {"x": "2025-05-28", "y": 1703},
        {"x": "2025-05-29", "y": 1766},
        {"x": "2025-05-30", "y": 1820},
    ]


def _popular_topic_map():
    return {
        "course": [
            "MySQL入门教程",
            "数据库原理",
            "计算机组成原理",
        ],
        "resource": [
            "数据库实验指导书",
            "索引优化资料包",
            "关系模型设计案例集",
        ],
        "discussion": [
            "并发控制讨论专区",
            "数据库调优问答精华",
            "SQL性能排查交流帖",
        ],
        "homework": [
            "数据库原理第一章课后作业",
            "事务并发控制练习",
            "MySQL 锁机制作业",
        ],
    }


@router.get("/dashboard/overview")
def dashboard_overview():
    return {
        "total_classes": 3735,
        "total_teachers": 768,
        "total_resources": 8874,
    }


@router.get("/dashboard/visits-trend")
def visits_trend(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    # Competition demo: fixed weekly trend, parameters reserved for future expansion.
    _ = (start_date, end_date)
    return _visits_data()


@router.get("/dashboard/popular")
def dashboard_popular(type: Optional[str] = Query(default="course")):
    topic_map = _popular_topic_map()
    normalized = {
        "text": "course",
        "image": "resource",
        "video": "discussion",
        "course": "course",
        "resource": "resource",
        "discussion": "discussion",
        "homework": "homework",
    }.get((type or "course").lower(), "course")
    topics = topic_map[normalized]
    return [
        {
            "key": 1,
            "clickNumber": "1.8k",
            "title": topics[0],
            "increases": 14,
        },
        {
            "key": 2,
            "clickNumber": "1.3k",
            "title": topics[1],
            "increases": 11,
        },
        {
            "key": 3,
            "clickNumber": "1.1k",
            "title": topics[2],
            "increases": 8,
        },
    ]


@router.get("/dashboard/content-distribution")
def content_distribution():
    return {
        "total": 9285,
        "items": [
            {"name": "resources", "value": 5179},
            {"name": "courses", "value": 2301},
            {"name": "homework", "value": 1116},
            {"name": "discussions", "value": 689},
        ],
    }


@router.get("/api/content-data")
def content_data():
    # Legacy path kept for compatibility with old frontend code.
    return _visits_data()


@router.get("/api/popular/list")
def popular_list(type: Optional[str] = Query(default="text")):
    topic_map = _popular_topic_map()
    normalized = {
        "text": "course",
        "image": "resource",
        "video": "discussion",
        "course": "course",
        "resource": "resource",
        "discussion": "discussion",
        "homework": "homework",
    }.get((type or "text").lower(), "course")
    topics = topic_map[normalized]
    return [
        {
            "key": 1,
            "clickNumber": "1.8k",
            "title": topics[0],
            "increases": 14,
        },
        {
            "key": 2,
            "clickNumber": "1.3k",
            "title": topics[1],
            "increases": 11,
        },
        {
            "key": 3,
            "clickNumber": "1.1k",
            "title": topics[2],
            "increases": 8,
        },
    ]
