#!/usr/bin/env python3
"""Seed demo learning data for答辩/Golden Path 演示."""

from __future__ import annotations

import argparse
import uuid
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.core.db import engine
from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.models.user import User
from app.models.user_memory_profile import UserMemoryProfile

DEMO_CHATS = [
    (
        "B+树的分裂和合并条件是什么？",
        "B+树分裂发生在节点满时，通常将中间键上推；合并发生在删除后节点元素低于最小填充因子时。",
    ),
    (
        "事务的 ACID 特性中，隔离级别有哪些？",
        "标准隔离级别包括：读未提交、读已提交、可重复读、串行化。InnoDB 默认可重复读。",
    ),
    (
        "索引失效的常见场景有哪些？",
        "常见场景：对索引列使用函数、隐式类型转换、前导模糊查询、OR 连接非索引列、不符合最左前缀等。",
    ),
    (
        "请给我两道关于索引优化的练习题。",
        "好的。第一题：分析 WHERE YEAR(create_time)=2024 为何可能不走索引。第二题：设计覆盖索引优化分页查询。",
    ),
]

DEMO_PROFILE = {
    "current_goal": "掌握数据库索引优化与 B+ 树原理",
    "learning_style": "偏好分步讲解 + 例题练习",
    "weak_points": ["索引优化", "B+树分裂", "事务隔离级别"],
    "mastery_map": {
        "索引基础": 0.72,
        "B+树结构": 0.58,
        "事务与并发": 0.65,
        "SQL 优化": 0.48,
    },
    "strengths": ["主动提问", "愿意完成练习题"],
}


def seed_for_user(session: Session, email: str) -> None:
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        raise SystemExit(f"User not found: {email}")

    thread_id = f"seed_{uuid.uuid4().hex[:12]}"
    existing_thread = session.exec(
        select(ChatThread).where(ChatThread.user_id == user.id).limit(1)
    ).first()
    if existing_thread:
        thread_id = existing_thread.thread_id
    else:
        session.add(
            ChatThread(
                thread_id=thread_id,
                user_id=str(user.id),
                title="数据库学习对话",
                created_at=datetime.utcnow(),
            )
        )
        session.flush()

    existing_count = session.query(Chat).filter(Chat.thread_id == thread_id).count()
    if existing_count >= len(DEMO_CHATS):
        print(f"Chat history already seeded for {email}")
    else:
        base_time = datetime.utcnow() - timedelta(hours=2)
        for i, (question, answer) in enumerate(DEMO_CHATS):
            session.add(
                Chat(
                    thread_id=thread_id,
                    user_input=question,
                    response=answer,
                    created_at=base_time + timedelta(minutes=i * 15),
                )
            )
        print(f"Seeded {len(DEMO_CHATS)} chat messages for {email}")

    profile = session.exec(
        select(UserMemoryProfile).where(UserMemoryProfile.user_id == user.id)
    ).first()
    if profile:
        profile.memory_profile = {**(profile.memory_profile or {}), **DEMO_PROFILE}
        profile.updated_at = datetime.utcnow()
        session.add(profile)
    else:
        session.add(
            UserMemoryProfile(
                user_id=user.id,
                memory_profile=DEMO_PROFILE,
            )
        )
    print(f"Seeded memory profile for {email}")
    session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo learning data")
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Target user email (default: admin@example.com)",
    )
    args = parser.parse_args()
    with Session(engine) as session:
        seed_for_user(session, args.email)


if __name__ == "__main__":
    main()
