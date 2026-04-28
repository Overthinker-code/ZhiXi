from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from sqlmodel import Session, select, or_

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
    mastery_map: dict[str, float] = Field(default_factory=dict)
    mastery_update: dict[str, Any] = Field(default_factory=dict)


class UserMemoryProfileService:
    MASTERY_DEFAULT = 0.52
    MASTERY_RELIABILITY = 0.28
    MASTERY_WEAK_POINT_OBSERVATION = 0.42
    MASTERY_FORMULA = (
        "M_new = clamp((1-r) * M_old + r * O_recent, 0, 1), "
        "r=0.28；O_recent 来自近期问答表现、薄弱点与模型提取的知识点掌握度"
    )

    def get_record(self, session: Session, user_id: UUID | str) -> UserMemoryProfile | None:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        return session.exec(
            select(UserMemoryProfile).where(UserMemoryProfile.user_id == uid)
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
            f"- 知识点掌握度：{self._format_mastery_for_prompt(profile)}\n"
            "如果本轮问题命中薄弱知识点，请提供更基础、更细化的解释，并补一个小例子。"
        )

    def collect_recent_chat_history(self, session: Session, user_id: UUID | str) -> str:
        limit = max(1, int(settings.MEMORY_PROFILE_MAX_TURNS))
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        rows = session.exec(
            select(Chat)
            .join(ChatThread, ChatThread.thread_id == Chat.thread_id)
            .where(ChatThread.user_id == uid)
            .order_by(Chat.created_at.desc())
            .limit(limit)
        ).all()
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

    def _clamp_mastery(self, value: Any, default: float = MASTERY_DEFAULT) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = default
        return round(max(0.0, min(1.0, score)), 4)

    def _normalize_topic(self, topic: Any) -> str:
        return re.sub(r"\s+", "", str(topic or "").strip())[:24]

    def _format_mastery_for_prompt(self, profile: dict[str, Any]) -> str:
        mastery_map = profile.get("mastery_map") or {}
        if not isinstance(mastery_map, dict) or not mastery_map:
            return "暂无稳定估计"
        rows = []
        for topic, score in sorted(mastery_map.items(), key=lambda item: float(item[1]))[:6]:
            rows.append(f"{topic}:{round(float(score) * 100)}%")
        return "、".join(rows) if rows else "暂无稳定估计"

    def _fallback_observed_mastery(
        self,
        weak_points: list[str],
        current_goal: str,
    ) -> dict[str, float]:
        observed: dict[str, float] = {}
        for point in weak_points:
            topic = self._normalize_topic(point)
            if topic:
                observed[topic] = self.MASTERY_WEAK_POINT_OBSERVATION
        goal = self._normalize_topic(current_goal)
        if goal and goal not in observed:
            observed[goal] = 0.58
        return observed

    def _merge_behavioral_observations(
        self,
        user_id: str | UUID,
        current_mastery: dict[str, float],
        session: Session,
    ) -> dict[str, float]:
        """
        教育学参数联动4：将课堂行为观察融合到 mastery_map 中。
        使用传入的session避免嵌套事务（由refresh_profile统一提供）
        
        逻辑：
        - 如果学生在某知识点授课时段的LEI<0.5且认知状态为mind_wandering/task_switching，
          将该知识点的掌握度向下调整（学生可能没听懂）
        - 如果LEI>0.8且认知深度高，掌握度向上微调
        """
        try:
            from uuid import UUID
            from sqlalchemy import desc, or_
            from app.models import BehaviorSummaryRecord
            
            try:
                uid = UUID(str(user_id))
            except ValueError:
                uid = None
            
            # 优先查询该学生的个人记录；若无，则查询课堂整体记录（student_id=NULL）
            sid = UUID(uid) if isinstance(uid, str) and uid else uid
            records = session.exec(
                select(BehaviorSummaryRecord)
                .where(
                    or_(
                        BehaviorSummaryRecord.student_id == sid,
                        BehaviorSummaryRecord.student_id.is_(None),
                    )
                )
                .order_by(desc(BehaviorSummaryRecord.session_date))
                .limit(5)
            ).all()
            if not records:
                return current_mastery
            
            avg_lei = sum(r.avg_lei for r in records) / len(records)
            avg_mw = sum(r.mind_wandering_rate for r in records) / len(records)
            
            adjusted = dict(current_mastery)
            
            # 课堂整体表现差 → 对所有知识点掌握度打折扣
            if avg_lei < 0.4:
                discount = 0.85
                for topic in adjusted:
                    adjusted[topic] = self._clamp_mastery(adjusted[topic] * discount)
            elif avg_lei < 0.6:
                discount = 0.92
                for topic in adjusted:
                    adjusted[topic] = self._clamp_mastery(adjusted[topic] * discount)
            elif avg_lei > 0.8 and avg_mw < 0.1:
                # 表现优秀 → 轻微上调
                boost = 1.05
                for topic in adjusted:
                    adjusted[topic] = self._clamp_mastery(adjusted[topic] * boost)
            
            return adjusted
        except Exception:
            return current_mastery

    def _merge_mastery_map(
        self,
        previous_profile: dict[str, Any] | None,
        payload: MemoryProfilePayload,
        user_id: str | UUID | None = None,
        session: Session | None = None,
    ) -> tuple[dict[str, float], dict[str, Any]]:
        previous_mastery = {}
        if previous_profile and isinstance(previous_profile.get("mastery_map"), dict):
            previous_mastery = {
                self._normalize_topic(topic): self._clamp_mastery(score)
                for topic, score in previous_profile["mastery_map"].items()
                if self._normalize_topic(topic)
            }

        observed = {
            self._normalize_topic(topic): self._clamp_mastery(score)
            for topic, score in (payload.mastery_map or {}).items()
            if self._normalize_topic(topic)
        }
        if not observed:
            observed = self._fallback_observed_mastery(
                payload.weak_points,
                payload.current_goal,
            )

        topics = sorted(set(previous_mastery) | set(observed))
        updated: dict[str, float] = {}
        deltas: dict[str, float] = {}
        weak_set = {self._normalize_topic(point) for point in payload.weak_points}

        for topic in topics:
            old_score = previous_mastery.get(topic, self.MASTERY_DEFAULT)
            recent_observation = observed.get(
                topic,
                self.MASTERY_WEAK_POINT_OBSERVATION if topic in weak_set else old_score,
            )
            reliability = self.MASTERY_RELIABILITY
            if topic in weak_set and topic not in observed:
                reliability = 0.34
            new_score = self._clamp_mastery(
                (1 - reliability) * old_score + reliability * recent_observation
            )
            updated[topic] = new_score
            deltas[topic] = round(new_score - old_score, 4)

        # 教育学参数联动4：融合课堂行为观察
        if user_id is not None and session is not None:
            updated = self._merge_behavioral_observations(user_id, updated, session)

        low_topics = [
            topic for topic, score in sorted(updated.items(), key=lambda item: item[1])
            if score < 0.6
        ][:5]
        return updated, {
            "formula": self.MASTERY_FORMULA,
            "reliability": self.MASTERY_RELIABILITY,
            "observed_mastery": observed,
            "delta": deltas,
            "low_mastery_topics": low_topics,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def infer_profile_from_history(self, chat_history: str) -> MemoryProfilePayload:
        if not chat_history.strip():
            return MemoryProfilePayload()
        prompt = (
            "你是一个学情分析专家。请阅读以下该用户近期的学习聊天记录。\n"
            "你的任务是提取用户的学习特征，并输出严格 JSON。\n"
            "必须包含字段：weak_points（数组）、learning_style（字符串）、current_goal（字符串）、"
            "mastery_map（对象，key 为知识点，value 为 0-1 的近期掌握度估计）。\n"
            "mastery_map 最多输出 6 个知识点；不确定时给 0.45-0.6，不要给极端值。\n"
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
                mastery_map={
                    self._normalize_topic(topic): self._clamp_mastery(score)
                    for topic, score in (data.get("mastery_map") or {}).items()
                    if self._normalize_topic(topic)
                },
            )

    def refresh_profile(self, user_id: UUID | str) -> dict[str, Any]:
        with Session(engine) as session:
            history = self.collect_recent_chat_history(session, user_id)
            if not history:
                return {"status": "skipped", "reason": "no_history"}
            previous_profile = self.get_profile_dict(session, user_id) or {}
            payload = self.infer_profile_from_history(history)
            # 传入user_id和session以启用课堂行为观察融合（联动4）
            mastery_map, mastery_update = self._merge_mastery_map(previous_profile, payload, user_id=user_id, session=session)
            payload.mastery_map = mastery_map
            payload.mastery_update = mastery_update
            self.upsert_profile(session, user_id=user_id, payload=payload)
            return {
                "status": "success",
                "user_id": str(user_id),
                "profile": payload.model_dump(),
            }


user_memory_profile_service = UserMemoryProfileService()
