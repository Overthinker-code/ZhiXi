from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.profile_update_event import ProfileUpdateEvent
from app.models.user_memory_profile import UserMemoryProfile
from app.services.learning_session_service import analyze_learning_session
from app.services.user_memory_profile_service import user_memory_profile_service


class ProfileUpdateService:
    DEFAULT_ALPHA = 0.1

    @staticmethod
    def _clamp(value: Any, default: float = 0.5) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        return round(max(0.0, min(1.0, number)), 4)

    def analyze_chat_turn(
        self,
        *,
        user_message: str,
        assistant_message: str = "",
        course: str | None = None,
        knowledge_point: str | None = None,
    ) -> dict[str, Any]:
        message = (user_message or "").strip()
        session_analysis = analyze_learning_session(message)
        topic = knowledge_point or session_analysis.knowledge_point
        resolved_course = course or session_analysis.course

        if re.search(r"还是不理解|完全不懂|完全不会|一直不会|太难|没听懂", message):
            difficulty, observed_mastery = "high", 0.32
        elif re.search(r"不理解|不会|为什么|怎么|如何|讲解", message):
            difficulty, observed_mastery = "medium", 0.46
        else:
            difficulty, observed_mastery = "low", 0.62

        if re.search(r"不理解|为什么|原理|概念", message):
            weakness = "概念理解"
        elif re.search(r"不会做|代码|实现|项目|应用", message):
            weakness = "知识应用"
        elif re.search(r"忘了|记不住|混淆", message):
            weakness = "知识记忆"
        else:
            weakness = ""

        preferences: dict[str, float] = {}
        preference_patterns = {
            "example_preference": r"例子|案例|举例",
            "video_preference": r"视频|动画|演示",
            "visual_preference": r"思维导图|图解|画图|流程图",
            "practice_preference": r"练习|习题|测试|测验",
            "step_by_step_preference": r"一步一步|详细|分步骤|慢慢",
            "code_preference": r"代码|编程|实现|实操",
        }
        for key, pattern in preference_patterns.items():
            if re.search(pattern, message):
                preferences[key] = 1.0

        if "example_preference" in preferences:
            cognitive_style = "案例驱动"
        elif "visual_preference" in preferences or "video_preference" in preferences:
            cognitive_style = "视觉化理解"
        elif "step_by_step_preference" in preferences:
            cognitive_style = "分步推理"
        else:
            cognitive_style = ""

        return {
            "course": resolved_course,
            "knowledge_point": topic,
            "difficulty": difficulty,
            "weakness": weakness,
            "observed_mastery": observed_mastery,
            "learning_style": cognitive_style or "待持续观察",
            "cognitive_style": cognitive_style,
            "preference_signals": preferences,
            "behavior_signals": {
                "chat_turns": 1.0,
                "help_seeking": 1.0 if difficulty in {"medium", "high"} else 0.0,
            },
            "assistant_response_length": len(assistant_message or ""),
        }

    def apply_incremental_update(
        self,
        session: Session,
        *,
        user_id: UUID | str,
        analysis: dict[str, Any],
        session_id: str | None = None,
        message_id: int | None = None,
        source_type: str = "chat",
        alpha: float = DEFAULT_ALPHA,
        evidence: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], ProfileUpdateEvent]:
        alpha = max(0.01, min(1.0, float(alpha)))
        previous = user_memory_profile_service.get_profile_dict(session, user_id) or {}
        before = dict(previous)
        profile = dict(previous)

        knowledge_state = dict(profile.get("knowledge_state") or profile.get("mastery_map") or {})
        topic = str(analysis.get("knowledge_point") or "").strip()
        if topic and analysis.get("observed_mastery") is not None:
            old = self._clamp(knowledge_state.get(topic), 0.52)
            observed = self._clamp(analysis.get("observed_mastery"), old)
            knowledge_state[topic] = self._clamp(old + alpha * (observed - old))

        preferences = dict(profile.get("learning_preference") or {})
        for key, signal in (analysis.get("preference_signals") or {}).items():
            old = self._clamp(preferences.get(key), 0.5)
            signed_signal = max(-1.0, min(1.0, float(signal)))
            preferences[key] = self._clamp(old + alpha * signed_signal)

        behavior = dict(profile.get("learning_behavior") or {})
        for key, amount in (analysis.get("behavior_signals") or {}).items():
            behavior[key] = round(float(behavior.get(key) or 0) + float(amount), 4)
        behavior["last_chat_at"] = datetime.now(timezone.utc).isoformat()

        weak_points = [str(item) for item in (profile.get("weak_points") or []) if str(item).strip()]
        if topic and analysis.get("difficulty") in {"medium", "high"} and topic not in weak_points:
            weak_points.append(topic)
        weak_points = weak_points[-12:]

        cognitive_style = str(analysis.get("cognitive_style") or "").strip()
        if cognitive_style:
            profile["cognitive_style"] = cognitive_style
            profile["learning_style"] = cognitive_style
        profile["knowledge_state"] = knowledge_state
        profile["mastery_map"] = knowledge_state
        profile["learning_preference"] = preferences
        profile["learning_behavior"] = behavior
        profile["weak_points"] = weak_points
        if analysis.get("learning_goal"):
            profile["learning_goal"] = analysis["learning_goal"]
            profile["current_goal"] = analysis["learning_goal"]
        profile["profile_version"] = int(profile.get("profile_version") or 0) + 1
        profile["last_analysis"] = {
            "course": analysis.get("course"),
            "knowledge_point": topic,
            "difficulty": analysis.get("difficulty"),
            "weakness": analysis.get("weakness"),
            "source_type": source_type,
        }

        uid = UUID(str(user_id))
        record = user_memory_profile_service.get_record(session, uid)
        if record:
            record.memory_profile = profile
            record.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            record = UserMemoryProfile(user_id=uid, memory_profile=profile)
        session.add(record)

        patch = {
            "knowledge_state": knowledge_state,
            "learning_preference": preferences,
            "learning_behavior": behavior,
            "weak_points": weak_points,
            "cognitive_style": profile.get("cognitive_style", ""),
            "profile_version": profile["profile_version"],
        }
        event = ProfileUpdateEvent(
            user_id=str(uid),
            session_id=session_id,
            message_id=message_id,
            source_type=source_type,
            alpha=alpha,
            evidence=evidence or analysis,
            profile_patch=patch,
            before_snapshot=before,
            after_snapshot=profile,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return profile, event

    def analyze_and_update_turn(
        self,
        session: Session,
        *,
        user_id: UUID | str,
        session_id: str,
        user_message: str,
        assistant_message: str,
        message_id: int | None = None,
        course: str | None = None,
        knowledge_point: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], ProfileUpdateEvent]:
        analysis = self.analyze_chat_turn(
            user_message=user_message,
            assistant_message=assistant_message,
            course=course,
            knowledge_point=knowledge_point,
        )
        profile, event = self.apply_incremental_update(
            session,
            user_id=user_id,
            analysis=analysis,
            session_id=session_id,
            message_id=message_id,
            source_type="chat",
            evidence={"user_message": user_message[:1000], "analysis": analysis},
        )
        return analysis, profile, event


profile_update_service = ProfileUpdateService()
