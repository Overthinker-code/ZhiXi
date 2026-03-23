from typing import Optional

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/api/content-data")
def content_data():
    return [
        {"x": "Mon", "y": 680},
        {"x": "Tue", "y": 742},
        {"x": "Wed", "y": 695},
        {"x": "Thu", "y": 811},
        {"x": "Fri", "y": 768},
        {"x": "Sat", "y": 902},
        {"x": "Sun", "y": 856},
    ]


@router.get("/api/popular/list")
def popular_list(type: Optional[str] = Query(default="text")):
    topic_map = {
        "text": [
            "Join Query Drill",
            "Window Function Challenge",
            "Transaction Isolation Lab",
        ],
        "image": [
            "ER Modeling Report",
            "Index Tuning Report",
            "Normalization Design Report",
        ],
        "video": [
            "Why Did My SQL Timeout?",
            "How to Avoid Deadlocks?",
            "When to Use Composite Indexes?",
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
