from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

from app.models import (
    LearningActivity,
    QuizAttempt,
    Resource,
    ResourceFavorite,
    Student,
    StudentProfile,
    UD,
    User,
)
from app.models.conversation_message import ConversationMessage
from app.models.profile_update_event import ProfileUpdateEvent
from app.services.user_memory_profile_service import user_memory_profile_service


class StudentProfileAgent:
    """Build and continuously synchronize the learner digital twin.

    Quantitative mastery is updated only from scored quiz attempts. Browsing and
    chat signals can affect preference/behavior, but never improve mastery.
    """

    MASTERY_HISTORY_WEIGHT = 0.7
    PREFERENCE_ALPHA = 0.2
    DIMENSION_LABELS = {
        "knowledge_state": "知识掌握能力",
        "learning_goal": "学习目标",
        "learning_preference": "学习偏好",
        "cognitive_style": "认知风格",
        "learning_behavior": "学习行为",
        "problem_solving": "问题解决能力",
        "learning_motivation": "学习动力",
        "knowledge_graph_state": "知识网络状态",
    }

    @staticmethod
    def _clamp(value: Any, default: float = 0.5) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        return round(max(0.0, min(1.0, number)), 4)

    @staticmethod
    def _average(values: list[float], default: float = 0.0) -> float:
        return sum(values) / len(values) if values else default

    @staticmethod
    def _clean_list(values: Any, *, limit: int = 8) -> list[str]:
        result: list[str] = []
        for value in values or []:
            label = str(value or "").strip()
            if label and label not in result:
                result.append(label)
        return result[:limit]

    def _update_mastery(self, old: Any, observation: Any) -> float:
        previous = self._clamp(old, 0.5)
        result = self._clamp(observation, previous)
        weight = self.MASTERY_HISTORY_WEIGHT
        return self._clamp(weight * previous + (1 - weight) * result)

    def _merge_preferences(self, memory: dict[str, Any]) -> dict[str, float]:
        aliases = {
            "video_preference": "视频",
            "document_preference": "文档",
            "example_preference": "案例",
            "code_preference": "代码实践",
            "practice_preference": "练习",
            "visual_preference": "图解",
            "step_by_step_preference": "分步讲解",
        }
        merged: dict[str, float] = {}
        source = memory.get("learning_preference") or {}
        if isinstance(source, dict):
            for key, raw in source.items():
                if isinstance(raw, (int, float)):
                    merged[aliases.get(str(key), str(key))] = self._clamp(raw)

        feedback = memory.get("recommendation_feedback") or {}
        modalities = feedback.get("modalities") if isinstance(feedback, dict) else {}
        if isinstance(modalities, dict):
            for key, item in modalities.items():
                affinity = item.get("affinity", 0) if isinstance(item, dict) else item
                current = merged.get(str(key), 0.5)
                observation = self._clamp(0.5 + float(affinity or 0) / 6)
                alpha = self.PREFERENCE_ALPHA
                merged[str(key)] = self._clamp((1 - alpha) * current + alpha * observation)
        return dict(sorted(merged.items(), key=lambda item: item[1], reverse=True)[:8])

    def _knowledge_graph(self, knowledge: dict[str, float]) -> dict[str, list[dict[str, Any]]]:
        nodes: dict[str, dict[str, Any]] = {
            "learner": {"id": "learner", "name": "我的知识网络", "mastery": 1.0}
        }
        edges: list[dict[str, str]] = []
        for index, (topic, mastery) in enumerate(
            sorted(knowledge.items(), key=lambda item: item[1])[:12]
        ):
            parts = [part.strip() for part in str(topic).replace("/", ".").split(".") if part.strip()]
            leaf_id = f"kp-{index}"
            if len(parts) > 1:
                group_id = f"group-{parts[0]}"
                if group_id not in nodes:
                    nodes[group_id] = {"id": group_id, "name": parts[0], "mastery": mastery}
                    edges.append({"source": "learner", "target": group_id})
                nodes[leaf_id] = {"id": leaf_id, "name": parts[-1], "mastery": mastery}
                edges.append({"source": group_id, "target": leaf_id})
            else:
                nodes[leaf_id] = {"id": leaf_id, "name": str(topic), "mastery": mastery}
                edges.append({"source": "learner", "target": leaf_id})
        return {"nodes": list(nodes.values()), "edges": edges}

    def _build_summary(
        self,
        *,
        major: str,
        stage: str,
        style: str,
        strengths: list[str],
        weaknesses: list[str],
    ) -> str:
        identity = f"一名{major}学生" if major else "一名持续成长的学习者"
        strength_text = "、".join(strengths[:2]) or "主动学习与持续反馈"
        weak_text = "、".join(weaknesses[:3]) or "尚需积累更多有效学习证据"
        return (
            f"你是{identity}，目前处于{stage}。你的主要优势是{strength_text}；"
            f"近期建议重点关注{weak_text}。从已有行为看，你更适合{style}，"
            "系统会将这份画像提供给规划、资源推荐和学习评估 Agent 作为协同决策依据。"
        )

    def synchronize(self, session: Session, user_id: UUID | str) -> StudentProfile:
        uid = UUID(str(user_id))
        row = session.exec(select(StudentProfile).where(StudentProfile.user_id == uid)).first()
        is_new = row is None
        memory = dict(user_memory_profile_service.get_profile_dict(session, uid) or {})
        knowledge = {
            str(key): self._clamp(value)
            for key, value in (memory.get("knowledge_state") or memory.get("mastery_map") or {}).items()
            if str(key).strip()
        }
        cursor = dict(row.evidence_cursor or {}) if row else {}
        processed = set(cursor.get("quiz_attempt_ids") or [])
        attempts = session.exec(
            select(QuizAttempt)
            .where(QuizAttempt.user_id == uid)
            .order_by(QuizAttempt.created_time.asc())
        ).all()
        updates: list[str] = []
        for attempt in attempts:
            attempt_id = str(attempt.id)
            if attempt_id in processed:
                continue
            resource = session.get(Resource, attempt.resource_id)
            topic = str(getattr(resource, "knowledge_point", "") or "").strip()
            if topic:
                before = knowledge.get(topic, 0.5)
                knowledge[topic] = self._update_mastery(before, attempt.score)
                delta = round((knowledge[topic] - before) * 100)
                if delta:
                    updates.append(f"{topic}掌握度{'提升' if delta > 0 else '调整'}{abs(delta)}%")
            for weak in self._clean_list(attempt.wrong_knowledge_points, limit=12):
                knowledge[weak] = self._update_mastery(knowledge.get(weak, 0.5), 0)
            processed.add(attempt_id)

        user = session.get(User, uid)
        student = session.exec(select(Student).where(Student.user_id == uid)).first()
        ud = session.get(UD, student.ud_id) if student else None
        major = str(getattr(ud, "department", "") or memory.get("major") or "").strip()
        school = str(getattr(ud, "university", "") or memory.get("school") or "").strip()
        goal = str(memory.get("learning_goal") or memory.get("current_goal") or "").strip()
        cognitive_style = str(memory.get("cognitive_style") or memory.get("learning_style") or "持续观察中")
        preferences = self._merge_preferences(memory)

        chat_turns = len(session.exec(select(ConversationMessage.id).where(
            ConversationMessage.user_id == str(uid), ConversationMessage.role == "user"
        )).all())
        activities = (
            session.exec(select(LearningActivity).where(LearningActivity.student_id == student.id)).all()
            if student else []
        )
        favorite_count = len(session.exec(select(ResourceFavorite.id).where(ResourceFavorite.user_id == uid)).all())
        correct = sum(int(item.correct_count or 0) for item in attempts)
        total = sum(int(item.total_questions or 0) for item in attempts)
        accuracy = correct / total if total else 0.0
        behavior = dict(memory.get("learning_behavior") or {})
        behavior.update({
            "chat_turns": chat_turns,
            "resource_visits": len(activities),
            "favorites": favorite_count,
            "quiz_attempts": len(attempts),
            "answered_questions": total,
            "accuracy": round(accuracy, 4),
            "school": school,
            "major": major,
        })

        evidence_count = chat_turns + len(activities) + len(attempts)
        if evidence_count >= 20:
            stage = "能力提升期"
        elif evidence_count >= 6:
            stage = "课程强化阶段"
        else:
            stage = "画像形成期"
        if preferences:
            top_preference = next(iter(preferences))
            style = f"{top_preference}驱动型学习者"
        elif cognitive_style and cognitive_style != "持续观察中":
            style = f"{cognitive_style}学习者"
        else:
            style = "持续观察型学习者"

        def display_topic(value: Any) -> str:
            return str(value).rsplit(".", 1)[-1].strip()
        low_topics = [display_topic(key) for key, value in sorted(knowledge.items(), key=lambda item: item[1]) if value < 0.55]
        weak_memory = memory.get("weak_points") or []
        weaknesses = self._clean_list([*low_topics, *weak_memory], limit=6)
        strong_topics = [display_topic(key) for key, value in sorted(knowledge.items(), key=lambda item: item[1], reverse=True) if value >= 0.72]
        strengths = self._clean_list(strong_topics, limit=4)
        if accuracy >= 0.75 and total >= 3:
            strengths = self._clean_list(["问题解决与练习表现", *strengths], limit=4)
        if preferences.get("代码实践", 0) >= 0.65:
            strengths = self._clean_list(["代码实践能力", *strengths], limit=4)

        knowledge_score = self._average(list(knowledge.values()), 0.45)
        behavior_score = min(1.0, 0.25 + min(evidence_count, 30) / 40)
        feedback_score = min(1.0, 0.35 + favorite_count * 0.08 + len(preferences) * 0.03)
        overall = 0.38 * knowledge_score + 0.22 * behavior_score + 0.30 * accuracy + 0.10 * feedback_score
        preference_confidence = min(1.0, 0.35 + len(preferences) * 0.08)
        graph_score = min(1.0, 0.25 + len(knowledge) * 0.05) * (0.6 + knowledge_score * 0.4)
        dimensions = {
            "knowledge_state": round(knowledge_score * 100),
            "learning_goal": 82 if goal else 42,
            "learning_preference": round(preference_confidence * 100),
            "cognitive_style": 78 if cognitive_style != "持续观察中" else 46,
            "learning_behavior": round(behavior_score * 100),
            "problem_solving": round((accuracy if total else 0.45) * 100),
            "learning_motivation": round(min(1.0, 0.4 + evidence_count / 35) * 100),
            "knowledge_graph_state": round(graph_score * 100),
        }
        behavior["overall_score"] = round(overall * 100)

        recent_events = session.exec(
            select(ProfileUpdateEvent)
            .where(ProfileUpdateEvent.user_id == str(uid))
            .order_by(ProfileUpdateEvent.created_at.desc())
            .limit(4)
        ).all()
        for event in recent_events:
            evidence = event.evidence if isinstance(event.evidence, dict) else {}
            analysis = evidence.get("analysis") if isinstance(evidence.get("analysis"), dict) else evidence
            topic = str(analysis.get("knowledge_point") or "").strip()
            if topic:
                updates.append(f"AI从近期交互中识别到关注点：{topic}")
        if attempts and not updates:
            updates.append(f"已纳入最近{min(len(attempts), 5)}次练习表现")
        if preferences:
            updates.append(f"当前更偏好{next(iter(preferences))}类资源")
        updates = self._clean_list(updates, limit=5)

        graph = self._knowledge_graph(knowledge)
        summary = self._build_summary(
            major=major,
            stage=stage,
            style=style,
            strengths=strengths,
            weaknesses=weaknesses,
        )
        cursor["quiz_attempt_ids"] = list(processed)[-200:]
        cursor["source"] = "profile_agent_v1"

        if not row:
            row = StudentProfile(user_id=uid)
        changed = any([
            row.knowledge_state != knowledge,
            row.learning_behavior != behavior,
            row.learning_preference != preferences,
            row.ai_summary != summary,
            row.learning_goal != goal,
        ])
        row.learning_stage = stage
        row.learning_goal = goal
        row.learning_style = style
        row.strengths = strengths
        row.weaknesses = weaknesses
        row.knowledge_state = knowledge
        row.learning_behavior = behavior
        row.learning_preference = preferences
        row.cognitive_style = cognitive_style
        row.knowledge_graph = graph
        row.dimension_scores = dimensions
        row.ai_summary = summary
        row.last_updates = updates or list(row.last_updates or [])
        row.evidence_cursor = cursor
        if changed:
            row.profile_version = 1 if is_new else int(row.profile_version or 0) + 1
            row.updated_time = datetime.now(timezone.utc)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def public_dict(self, row: StudentProfile) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "learning_stage": row.learning_stage,
            "learning_goal": row.learning_goal,
            "learning_style": row.learning_style,
            "strengths": row.strengths,
            "weaknesses": row.weaknesses,
            "knowledge_state": row.knowledge_state,
            "learning_behavior": row.learning_behavior,
            "learning_preference": row.learning_preference,
            "cognitive_style": row.cognitive_style,
            "knowledge_graph": row.knowledge_graph,
            "dimensions": [
                {"key": key, "label": self.DIMENSION_LABELS[key], "score": score}
                for key, score in row.dimension_scores.items()
            ],
            "overall_score": int((row.learning_behavior or {}).get("overall_score") or 0),
            "ai_summary": row.ai_summary,
            "last_updates": row.last_updates,
            "profile_version": row.profile_version,
            "updated_time": row.updated_time,
            "agent_links": {
                "planner_agent": "使用画像生成个性化学习路径",
                "resource_agent": "使用画像匹配和生成学习资源",
                "evaluator_agent": "使用画像评估学习效果",
            },
        }


student_profile_agent = StudentProfileAgent()
