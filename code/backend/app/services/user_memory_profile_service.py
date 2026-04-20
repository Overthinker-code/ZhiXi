from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from sqlmodel import Session

from app.core.config import settings
from app.core.db import engine
from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.models.user_memory_profile import UserMemoryProfile
from app.services.chat_model_factory import ChatModelFactory


class MemoryProfilePayload(BaseModel):
    weak_points: list[str] = Field(default_factory=list)
    learning_style: str = ""
    current_goal: str = ""


class UserMemoryProfileService:
    def get_record(self, session: Session, user_id: UUID | str) -> UserMemoryProfile | None:
        return session.query(UserMemoryProfile).filter(
            UserMemoryProfile.user_id == user_id
        ).first()

    def get_profile_dict(self, session: Session, user_id: UUID | str) -> dict[str, Any] | None:
        record = self.get_record(session, user_id)
        if not record or not isinstance(record.memory_profile, dict):
            return None
        return record.memory_profile

    def upsert_profile(
        self,
        session: Session,
        *,
        user_id: UUID | str,
        payload: MemoryProfilePayload,
    ) -> UserMemoryProfile:
        record = self.get_record(session, user_id)
        data = payload.model_dump()
        if record:
            record.memory_profile = data
            record.updated_at = datetime.utcnow()
        else:
            record = UserMemoryProfile(
                user_id=user_id,
                memory_profile=data,
                updated_at=datetime.utcnow(),
            )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def build_prompt_injection(
        self, session: Session, user_id: UUID | str | None
    ) -> str:
        if not user_id:
            return ""
        profile = self.get_profile_dict(session, user_id)
        if not profile:
            return ""
        weak_points = profile.get("weak_points") or []
        weak_text = "、".join(str(item).strip() for item in weak_points if str(item).strip())
        current_goal = str(profile.get("current_goal") or "").strip() or "无明确目标"
        learning_style = (
            str(profile.get("learning_style") or "").strip() or "暂无明显学习偏好"
        )
        return (
            "[CRITICAL CONTEXT: USER PROFILE]\n"
            "你必须参考以下学生长期画像来组织回答深度、举例方式与学习建议：\n"
            f"- 当前学习目标：{current_goal}\n"
            f"- 薄弱知识点：{weak_text or '暂无明确薄弱点'}\n"
            f"- 学习偏好：{learning_style}\n"
            "如果本轮问题命中薄弱知识点，请提供更基础、更细化的解释，并补一个小例子。"
        )

    def collect_recent_chat_history(self, session: Session, user_id: UUID | str) -> str:
        limit = max(1, int(settings.MEMORY_PROFILE_MAX_TURNS))
        rows = (
            session.query(Chat)
            .join(ChatThread, ChatThread.thread_id == Chat.thread_id)
            .filter(ChatThread.user_id == str(user_id))
            .order_by(Chat.created_at.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            return ""
        blocks: list[str] = []
        for row in reversed(rows):
            user_input = (row.user_input or "").strip()
            response = (row.response or "").strip()
            if user_input:
                blocks.append(f"学生：{user_input}")
            if response:
                blocks.append(f"助手：{response}")
        merged = "\n".join(blocks)
        max_chars = max(1000, int(settings.MEMORY_PROFILE_MAX_CHARS))
        if len(merged) > max_chars:
            return merged[-max_chars:]
        return merged

    def _extract_json_blob(self, raw: str) -> dict[str, Any]:
        text = (raw or "").strip()
        if not text:
            return {}
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
        return {}

    def infer_profile_from_history(self, chat_history: str) -> MemoryProfilePayload:
        if not chat_history.strip():
            return MemoryProfilePayload()
        prompt = (
            "你是一个学情分析专家。请阅读以下该用户近期的学习聊天记录。\n"
            "你的任务是提取用户的学习特征，并输出严格 JSON。\n"
            "必须包含字段：weak_points（数组）、learning_style（字符串）、current_goal（字符串）。\n"
            "不要输出 JSON 以外的任何内容。\n\n"
            f"聊天记录：\n{chat_history}"
        )
        llm = ChatModelFactory.create(temperature=0.1, max_tokens=800)
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = getattr(response, "content", "") or ""
        if isinstance(raw, list):
            raw = "\n".join(
                str(block.get("text", "")) if isinstance(block, dict) else str(block)
                for block in raw
            )
        data = self._extract_json_blob(str(raw))
        try:
            return MemoryProfilePayload.model_validate(data)
        except Exception:
            weak_points = data.get("weak_points")
            if not isinstance(weak_points, list):
                weak_points = []
            return MemoryProfilePayload(
                weak_points=[str(item).strip() for item in weak_points if str(item).strip()],
                learning_style=str(data.get("learning_style") or "").strip(),
                current_goal=str(data.get("current_goal") or "").strip(),
            )

    def refresh_profile(self, user_id: UUID | str) -> dict[str, Any]:
        with Session(engine) as session:
            history = self.collect_recent_chat_history(session, user_id)
            if not history:
                return {"status": "skipped", "reason": "no_history"}
            payload = self.infer_profile_from_history(history)
            self.upsert_profile(session, user_id=user_id, payload=payload)
            return {
                "status": "success",
                "user_id": str(user_id),
                "profile": payload.model_dump(),
            }


user_memory_profile_service = UserMemoryProfileService()
