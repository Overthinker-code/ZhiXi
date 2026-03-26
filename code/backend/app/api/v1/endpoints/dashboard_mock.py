from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/api/content-data")
def content_data():
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


@router.get("/api/popular/list")
def popular_list(type: Optional[str] = Query(default="text")):
    topic_map = {
        "text": [
            "MySQL入门教程",
            "数据库原理",
            "计算机组成原理",
        ],
        "image": [
            "数据库实验指导书",
            "索引优化资料包",
            "关系模型设计案例集",
        ],
        "video": [
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
    topics = topic_map.get(type or "text", topic_map["text"])
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
