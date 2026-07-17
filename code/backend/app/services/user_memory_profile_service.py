from __future__ import annotations

import json
import hashlib
import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import HumanMessage
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import engine
from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.models.user_memory_profile import UserMemoryProfile
from app.services.chat_model_factory import ChatModelFactory


logger = logging.getLogger(__name__)


class ProfileDimensionRecord(BaseModel):
    """Versioned value for one longitudinal learner-profile dimension.

    Raw chat text is deliberately not persisted here. ``source_ref`` is a
    non-reversible digest or a durable evidence id so an update can be audited
    without duplicating sensitive conversation content in the profile row.
    """

    key: str
    label: str
    value: Any | None = None
    source_type: str = "insufficient"
    source_ref: str | None = None
    updated_at: str | None = None
    version: int = Field(default=1, ge=1)
    method_version: str = "dynamic_profile_v2"


class MemoryProfilePayload(BaseModel):
    weak_points: list[str] = Field(default_factory=list)
    learning_style: str = ""
    current_goal: str = ""
    mastery_map: dict[str, float] = Field(default_factory=dict)
    mastery_update: dict[str, Any] = Field(default_factory=dict)
    knowledge_foundation: str = ""
    error_patterns: list[str] = Field(default_factory=list)
    resource_preference: str = ""
    learning_rhythm: str = ""
    self_regulation: str = ""
    interest_topics: list[str] = Field(default_factory=list)
    explicit_interest_topics: list[str] = Field(default_factory=list)
    activity_summary: dict[str, Any] = Field(default_factory=dict)
    knowledge_base_context: dict[str, Any] = Field(default_factory=dict)
    recommendation_feedback: dict[str, Any] = Field(default_factory=dict)
    profile_dimensions: dict[str, ProfileDimensionRecord] = Field(default_factory=dict)
    profile_schema_version: str = "dynamic_profile_v2"


class UserMemoryProfileService:
    PROFILE_SCHEMA_VERSION = "dynamic_profile_v2"
    PROFILE_DIMENSIONS: dict[str, str] = {
        "knowledge_foundation": "知识基础",
        "knowledge_mastery": "知识掌握与薄弱点",
        "error_patterns": "易错模式",
        "current_goal": "当前目标",
        "learning_style": "学习风格",
        "resource_preference": "资源偏好",
        "learning_rhythm": "学习节律",
        "self_regulation": "自我调节与任务执行",
    }
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
        data = payload.model_dump(mode="json")
        if (
            "interest_topics" in payload.model_fields_set
            and "explicit_interest_topics" not in payload.model_fields_set
        ):
            # Dialogue extraction is the authoritative source of explicit
            # interests. Behavioral aggregation must not infer that status from
            # a legacy mixed interest list.
            data["explicit_interest_topics"] = list(data.get("interest_topics") or [])
        if record:
            existing = record.memory_profile if isinstance(record.memory_profile, dict) else {}
            # Callers that only know the legacy payload must not erase the
            # longitudinal audit trail. New fields are replaced only when the
            # caller explicitly supplied them.
            for field in (
                "knowledge_foundation",
                "error_patterns",
                "resource_preference",
                "learning_rhythm",
                "self_regulation",
                "interest_topics",
                "explicit_interest_topics",
                "activity_summary",
                "knowledge_base_context",
                "recommendation_feedback",
                "profile_dimensions",
                "profile_schema_version",
            ):
                if field not in payload.model_fields_set and field in existing:
                    data[field] = existing[field]
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

    def _store_profile_without_commit(
        self,
        session: Session,
        *,
        user_id: UUID | str,
        profile: dict[str, Any],
    ) -> UserMemoryProfile:
        """Stage a profile update in the caller's evidence transaction."""

        record = self.get_record(session, user_id)
        now = datetime.utcnow()
        if record:
            record.memory_profile = profile
            record.updated_at = now
        else:
            record = UserMemoryProfile(
                user_id=user_id,
                memory_profile=profile,
                updated_at=now,
            )
        session.add(record)
        session.flush([record])
        return record

    @staticmethod
    def _meaningful(value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return bool(value)
        return True

    def _dimension_record(
        self,
        *,
        key: str,
        value: Any,
        source_type: str,
        source_ref: str | None,
        previous: dict[str, Any] | ProfileDimensionRecord | None,
        updated_at: str,
    ) -> ProfileDimensionRecord:
        prior: ProfileDimensionRecord | None = None
        if previous:
            try:
                prior = (
                    previous
                    if isinstance(previous, ProfileDimensionRecord)
                    else ProfileDimensionRecord.model_validate(previous)
                )
            except ValidationError:
                prior = None
        if not self._meaningful(value):
            if prior and self._meaningful(prior.value):
                return prior
            return ProfileDimensionRecord(
                key=key,
                label=self.PROFILE_DIMENSIONS[key],
                value=None,
                source_type="insufficient",
                updated_at=prior.updated_at if prior else None,
                version=prior.version if prior else 1,
            )
        if prior and prior.value == value and prior.source_type == source_type:
            return prior
        return ProfileDimensionRecord(
            key=key,
            label=self.PROFILE_DIMENSIONS[key],
            value=value,
            source_type=source_type,
            source_ref=source_ref,
            updated_at=updated_at,
            version=(prior.version + 1) if prior else 1,
        )

    def build_dialogue_profile_dimensions(
        self,
        payload: MemoryProfilePayload,
        *,
        previous_dimensions: dict[str, Any] | None = None,
        source_ref: str | None = None,
        updated_at: str | None = None,
    ) -> dict[str, ProfileDimensionRecord]:
        """Create the fixed eight-dimension contract from dialogue extraction.

        These values are qualitative dialogue inferences. They must never be
        interpreted as scored mastery observations. Quantitative mastery is
        overwritten only by ``apply_learning_evidence_update``.
        """

        previous = previous_dimensions or {}
        timestamp = updated_at or datetime.now(timezone.utc).isoformat()
        dialogue_values: dict[str, Any] = {
            "knowledge_foundation": payload.knowledge_foundation,
            "knowledge_mastery": (
                {"weak_points": payload.weak_points}
                if payload.weak_points
                else None
            ),
            "error_patterns": payload.error_patterns,
            "current_goal": payload.current_goal,
            "learning_style": payload.learning_style,
            "resource_preference": payload.resource_preference,
            "learning_rhythm": payload.learning_rhythm,
            "self_regulation": payload.self_regulation,
        }
        return {
            key: self._dimension_record(
                key=key,
                value=dialogue_values[key],
                source_type="dialogue_inference",
                source_ref=source_ref,
                previous=previous.get(key),
                updated_at=timestamp,
            )
            for key in self.PROFILE_DIMENSIONS
        }

    def apply_learning_evidence_update(
        self,
        session: Session,
        *,
        user_id: UUID | str,
        evidence_summary: dict[str, dict[str, Any]],
        evidence_id: UUID | str,
        evidence_payload: dict[str, Any] | None = None,
        observed_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Stage a trusted assessment update without committing its transaction.

        The caller must invoke this only for a trusted, scored assessment event.
        Resource generation, browsing and document exposure are intentionally
        excluded at the call boundary and therefore cannot improve mastery.
        """

        profile = dict(self.get_profile_dict(session, user_id) or {})
        existing_dimensions = profile.get("profile_dimensions") or {}
        timestamp = (observed_at or datetime.now(timezone.utc)).isoformat()
        try:
            current_payload = MemoryProfilePayload.model_validate(profile)
        except ValidationError:
            current_payload = MemoryProfilePayload(
                weak_points=[
                    str(item).strip()
                    for item in (profile.get("weak_points") or [])
                    if str(item).strip()
                ],
                learning_style=str(profile.get("learning_style") or "").strip(),
                current_goal=str(profile.get("current_goal") or "").strip(),
                knowledge_foundation=str(
                    profile.get("knowledge_foundation") or ""
                ).strip(),
                error_patterns=[
                    str(item).strip()
                    for item in (profile.get("error_patterns") or [])
                    if str(item).strip()
                ],
                resource_preference=str(
                    profile.get("resource_preference") or ""
                ).strip(),
                learning_rhythm=str(profile.get("learning_rhythm") or "").strip(),
                self_regulation=str(profile.get("self_regulation") or "").strip(),
            )
        baseline_dimensions = self.build_dialogue_profile_dimensions(
            current_payload,
            previous_dimensions=existing_dimensions,
            source_ref=None,
            updated_at=timestamp,
        )
        dimensions: dict[str, ProfileDimensionRecord] = {}
        for key in self.PROFILE_DIMENSIONS:
            try:
                dimensions[key] = ProfileDimensionRecord.model_validate(
                    existing_dimensions[key]
                )
            except (KeyError, TypeError, ValidationError):
                dimensions[key] = baseline_dimensions[key]
        mastery_map = {
            str(details.get("display_name") or point): self._clamp_mastery(estimate)
            for point, details in evidence_summary.items()
            if (estimate := details.get("mastery_estimate")) is not None
        }
        weak_points = [
            topic
            for topic, score in sorted(mastery_map.items(), key=lambda item: item[1])
            if score < 0.6
        ][:6]
        dimensions["knowledge_mastery"] = self._dimension_record(
            key="knowledge_mastery",
            value={"mastery_map": mastery_map, "weak_points": weak_points},
            source_type="learning_evidence",
            source_ref=str(evidence_id),
            previous=existing_dimensions.get("knowledge_mastery"),
            updated_at=timestamp,
        )

        payload = evidence_payload or {}
        grading = payload.get("grading_result") if isinstance(payload.get("grading_result"), dict) else {}
        explicit_errors: list[str] = []
        for candidate in (
            payload.get("error_patterns"),
            payload.get("error_pattern"),
            payload.get("mistake_type"),
            grading.get("gaps"),
        ):
            if isinstance(candidate, list):
                explicit_errors.extend(str(item).strip() for item in candidate if str(item).strip())
            elif isinstance(candidate, str) and candidate.strip():
                explicit_errors.append(candidate.strip())
        if explicit_errors:
            merged_errors = list(dict.fromkeys([*explicit_errors, *(profile.get("error_patterns") or [])]))[:8]
            profile["error_patterns"] = merged_errors
            dimensions["error_patterns"] = self._dimension_record(
                key="error_patterns",
                value=merged_errors,
                source_type="learning_evidence",
                source_ref=str(evidence_id),
                previous=existing_dimensions.get("error_patterns"),
                updated_at=timestamp,
            )

        task_execution = payload.get("task_execution")
        if isinstance(task_execution, dict) and task_execution:
            dimensions["self_regulation"] = self._dimension_record(
                key="self_regulation",
                value=task_execution,
                source_type="learning_evidence",
                source_ref=str(evidence_id),
                previous=existing_dimensions.get("self_regulation"),
                updated_at=timestamp,
            )

        profile.update(
            {
                "weak_points": (
                    weak_points if mastery_map else list(profile.get("weak_points") or [])
                ),
                "mastery_map": mastery_map,
                "mastery_update": {
                    "formula": "trusted_learning_evidence_weighted_beta_v1",
                    "source": "learning_evidence",
                    "evidence_id": str(evidence_id),
                    "topic_count": len(mastery_map),
                    "updated_at": timestamp,
                },
                "profile_dimensions": {
                    key: value.model_dump(mode="json") for key, value in dimensions.items()
                },
                "profile_schema_version": self.PROFILE_SCHEMA_VERSION,
            }
        )
        self._store_profile_without_commit(session, user_id=user_id, profile=profile)
        return profile

    def apply_behavioral_evidence_update(
        self,
        session: Session,
        *,
        user_id: UUID | str,
        evidence_id: UUID | str,
        observed_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Fold activity into qualitative dimensions without changing mastery."""

        from app.models.learning_evidence import LearningEvidence

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        rows = session.exec(
            select(LearningEvidence)
            .where(LearningEvidence.user_id == uid)
            .order_by(LearningEvidence.observed_at.desc())
            .limit(200)
        ).all()
        profile = dict(self.get_profile_dict(session, uid) or {})
        dimensions = dict(profile.get("profile_dimensions") or {})
        timestamp = (observed_at or datetime.now(timezone.utc)).isoformat()

        from app.services.recommendation_feedback_service import aggregate_feedback

        source_counts = Counter(row.source_type for row in rows)
        explicit_interests = [
            str(value).strip()
            for value in (profile.get("explicit_interest_topics") or [])
            if str(value).strip()
        ][:8]
        rhythm_buckets: Counter[str] = Counter()
        task_events: list[dict[str, Any]] = []
        kb_documents: list[dict[str, str]] = []
        kb_event_topics: list[str] = []
        seen_documents: set[tuple[str, str]] = set()

        for row in rows:
            payload = row.payload if isinstance(row.payload, dict) else {}
            task_execution = payload.get("task_execution")
            if isinstance(task_execution, dict) and task_execution:
                task_events.append(task_execution)
            citations = payload.get("citations")
            if isinstance(citations, list):
                topic = str(row.display_name or row.knowledge_point or "").strip()
                if topic and topic != "unscopedlearninginteraction":
                    kb_event_topics.append(topic)
                for citation in citations[:8]:
                    if not isinstance(citation, dict):
                        continue
                    title = str(
                        citation.get("title")
                        or citation.get("document")
                        or citation.get("source")
                        or ""
                    ).strip()
                    source = str(
                        citation.get("source_type")
                        or citation.get("source")
                        or "课程知识库"
                    ).strip()
                    if not title or (title, source) in seen_documents:
                        continue
                    seen_documents.add((title, source))
                    kb_documents.append({"title": title[:160], "source": source[:80]})
            observed = row.observed_at
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            hour = observed.astimezone().hour
            bucket = (
                "清晨"
                if 5 <= hour < 9
                else "上午"
                if 9 <= hour < 12
                else "下午"
                if 12 <= hour < 18
                else "晚间"
                if 18 <= hour < 24
                else "深夜"
            )
            rhythm_buckets[bucket] += 1

        # Use only decayed, signed feedback for implicit preferences. A single
        # incidental preview cannot replace dialogue-provided interests.
        feedback = aggregate_feedback(rows)

        def positive_labels(group: str) -> list[tuple[str, dict[str, Any]]]:
            values = feedback.get(group)
            if not isinstance(values, dict):
                return []
            selected: list[tuple[str, dict[str, Any]]] = []
            for label, details in values.items():
                if not isinstance(details, dict):
                    continue
                try:
                    affinity = float(details.get("affinity", 0))
                    positive_weight = float(details.get("positive_weight", 0))
                    samples = int(details.get("sample_count", 0))
                except (TypeError, ValueError):
                    continue
                if affinity > 0 and positive_weight >= 0.25 and samples >= 2:
                    selected.append((str(label), details))
            return sorted(selected, key=lambda item: float(item[1].get("affinity", 0)), reverse=True)

        implicit_topics = [label for label, _ in positive_labels("topics")[:6]]
        interest_topics = list(dict.fromkeys([*explicit_interests, *implicit_topics]))[:8]
        if explicit_interests:
            profile["explicit_interest_topics"] = explicit_interests
        profile["interest_topics"] = interest_topics
        profile["activity_summary"] = {
            "event_count": len(rows),
            "source_counts": dict(source_counts),
            "last_activity_at": rows[0].observed_at.isoformat() if rows else timestamp,
        }
        existing_kb = profile.get("knowledge_base_context")
        existing_kb = existing_kb if isinstance(existing_kb, dict) else {}
        existing_documents = [
            item
            for item in (existing_kb.get("recent_documents") or [])
            if isinstance(item, dict) and str(item.get("title") or "").strip()
        ]
        merged_documents: list[dict[str, str]] = []
        merged_document_keys: set[tuple[str, str]] = set()
        for item in [*kb_documents, *existing_documents]:
            title = str(item.get("title") or "").strip()[:160]
            source = str(item.get("source") or "课程知识库").strip()[:80]
            if not title or (title, source) in merged_document_keys:
                continue
            merged_document_keys.add((title, source))
            merged_documents.append({"title": title, "source": source})
        existing_kb_topics = [
            str(value).strip()
            for value in (existing_kb.get("topic_signals") or [])
            if str(value).strip()
        ]
        profile["knowledge_base_context"] = {
            "recent_documents": merged_documents[:12],
            "topic_signals": list(
                dict.fromkeys([*kb_event_topics, *existing_kb_topics])
            )[:6],
        }
        # Kept separate from broad activity summaries so rankers can use
        # bounded, signed and time-decayed affinities without interpreting
        # browsing as mastery or a negative action as interest.
        profile["recommendation_feedback"] = feedback

        preferred_modalities = positive_labels("modalities")[:3]
        if preferred_modalities:
            preference = {
                "method_version": feedback.get("method_version"),
                "dominant_types": [name for name, _ in preferred_modalities],
                "affinity_summary": [
                    {
                        "modality": name,
                        "affinity": round(float(details.get("affinity", 0)), 4),
                        "sample_count": int(details.get("sample_count", 0)),
                    }
                    for name, details in preferred_modalities
                ],
                "sample_count": sum(int(details.get("sample_count", 0)) for _, details in preferred_modalities),
            }
            profile["resource_preference"] = "、".join(preference["dominant_types"])
            dimensions["resource_preference"] = self._dimension_record(
                key="resource_preference",
                value=preference,
                source_type="behavioral_evidence",
                source_ref=str(evidence_id),
                previous=dimensions.get("resource_preference"),
                updated_at=timestamp,
            ).model_dump(mode="json")
        elif isinstance(dimensions.get("resource_preference"), dict) and (
            dimensions["resource_preference"].get("source_type") == "behavioral_evidence"
        ):
            # Do not keep a former implicit preference when only negative or
            # insufficiently supported feedback remains. Dialogue preference
            # records are left untouched.
            profile["resource_preference"] = ""

        if rhythm_buckets:
            dominant_period, _ = rhythm_buckets.most_common(1)[0]
            rhythm = {
                "dominant_period": dominant_period,
                "distribution": dict(rhythm_buckets),
                "sample_count": sum(rhythm_buckets.values()),
            }
            profile["learning_rhythm"] = f"近期主要在{dominant_period}学习"
            dimensions["learning_rhythm"] = self._dimension_record(
                key="learning_rhythm",
                value=rhythm,
                source_type="behavioral_evidence",
                source_ref=str(evidence_id),
                previous=dimensions.get("learning_rhythm"),
                updated_at=timestamp,
            ).model_dump(mode="json")

        if task_events:
            latest_task = task_events[0]
            completed = sum(
                1
                for item in task_events
                if bool(item.get("completed"))
                or item.get("status") == "completed"
                or float(item.get("progress") or 0) >= 100
            )
            progress = max(0, min(100, int(latest_task.get("progress") or 0)))
            self_regulation = {
                # Preserve auditable task-level observations such as attempt
                # count and completion flags while adding stable aggregates.
                **latest_task,
                "active_goal": str(latest_task.get("goal") or "")[:300],
                "latest_progress": progress,
                "completed_events": completed,
                "observed_task_events": len(task_events),
            }
            profile["self_regulation"] = f"当前任务进度 {progress}%"
            if self_regulation["active_goal"]:
                profile["current_goal"] = self_regulation["active_goal"]
                dimensions["current_goal"] = self._dimension_record(
                    key="current_goal",
                    value=self_regulation["active_goal"],
                    source_type="explicit_task",
                    source_ref=str(evidence_id),
                    previous=dimensions.get("current_goal"),
                    updated_at=timestamp,
                ).model_dump(mode="json")
            dimensions["self_regulation"] = self._dimension_record(
                key="self_regulation",
                value=self_regulation,
                source_type="behavioral_evidence",
                source_ref=str(evidence_id),
                previous=dimensions.get("self_regulation"),
                updated_at=timestamp,
            ).model_dump(mode="json")

        profile["profile_dimensions"] = dimensions
        profile["profile_schema_version"] = self.PROFILE_SCHEMA_VERSION
        self._store_profile_without_commit(session, user_id=uid, profile=profile)
        return profile

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
        knowledge_foundation = (
            str(profile.get("knowledge_foundation") or "").strip() or "暂无稳定描述"
        )
        error_patterns = "、".join(
            str(item).strip()
            for item in (profile.get("error_patterns") or [])
            if str(item).strip()
        )
        resource_preference = (
            str(profile.get("resource_preference") or "").strip() or "暂无明确偏好"
        )
        learning_rhythm = (
            str(profile.get("learning_rhythm") or "").strip() or "暂无稳定节律"
        )
        self_regulation = (
            str(profile.get("self_regulation") or "").strip() or "暂无任务执行观察"
        )
        interest_topics = "、".join(
            str(item).strip()
            for item in (profile.get("interest_topics") or [])[:6]
            if str(item).strip()
        )
        kb_context = profile.get("knowledge_base_context") or {}
        kb_topics = "、".join(
            str(item).strip()
            for item in (kb_context.get("topic_signals") or [])[:6]
            if str(item).strip()
        )
        return (
            "[CRITICAL CONTEXT: USER PROFILE]\n"
            "你必须参考以下学生长期画像来组织回答深度、举例方式与学习建议：\n"
            f"- 知识基础：{knowledge_foundation}\n"
            f"- 当前学习目标：{current_goal}\n"
            f"- 薄弱知识点：{weak_text or '暂无明确薄弱点'}\n"
            f"- 易错模式：{error_patterns or '暂无稳定易错模式'}\n"
            f"- 学习偏好：{learning_style}\n"
            f"- 资源偏好：{resource_preference}\n"
            f"- 学习节律：{learning_rhythm}\n"
            f"- 自我调节与任务执行：{self_regulation}\n"
            f"- 近期学习主题：{interest_topics or '暂无稳定主题'}\n"
            f"- 知识库关联主题：{kb_topics or '暂无稳定关联'}\n"
            f"- 知识点掌握度：{self._format_mastery_for_prompt(profile)}\n"
            "如果本轮问题命中薄弱知识点，请提供更基础、更细化的解释，并补一个小例子。"
        )

    def collect_recent_chat_history(self, session: Session, user_id: UUID | str) -> str:
        limit = max(1, int(settings.MEMORY_PROFILE_MAX_TURNS))
        # ChatThread.user_id is a legacy varchar column, while UserMemoryProfile.user_id is UUID.
        # Keep profile writes UUID-native, but compare chat history using the stored string value.
        thread_user_id = str(user_id)
        rows = session.exec(
            select(Chat)
            .join(ChatThread, ChatThread.thread_id == Chat.thread_id)
            .where(ChatThread.user_id == thread_user_id)
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
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {}
        return {}

    def _clamp_mastery(self, value: Any, default: float = MASTERY_DEFAULT) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = default
        if not math.isfinite(score):
            score = default
        return round(max(0.0, min(1.0, score)), 4)

    def _normalize_topic(self, topic: Any) -> str:
        return re.sub(r"\s+", "", str(topic or "").strip())[:24]

    def _format_mastery_for_prompt(self, profile: dict[str, Any]) -> str:
        mastery_map = profile.get("mastery_map") or {}
        if not isinstance(mastery_map, dict) or not mastery_map:
            return "暂无稳定估计"
        normalized_scores = [
            (str(topic), self._clamp_mastery(score))
            for topic, score in mastery_map.items()
            if str(topic).strip()
        ]
        rows = [
            f"{topic}:{round(score * 100)}%"
            for topic, score in sorted(normalized_scores, key=lambda item: item[1])[:6]
        ]
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
            logger.debug("behavioral mastery merge skipped", exc_info=True)
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
            "你的任务是提取用户明确表达或可从上下文稳定推断的学习特征，并输出严格 JSON。\n"
            "必须包含字段：knowledge_foundation（知识基础描述）、weak_points（薄弱点数组）、"
            "error_patterns（易错模式数组）、current_goal（当前目标）、learning_style（学习风格）、"
            "resource_preference（资源偏好）、learning_rhythm（学习节律）、"
            "self_regulation（自我调节与任务执行描述）。\n"
            "没有依据的字段使用空字符串或空数组；不要编造百分比、置信度或知识掌握分数。\n"
            "mastery_map 固定输出空对象；量化掌握度只能由已评分练习或测评证据计算。\n"
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
            parsed = MemoryProfilePayload.model_validate(data)
            # Treat any unsolicited LLM score as untrusted text. Dialogue may
            # describe confidence, but it cannot write quantitative mastery.
            parsed.mastery_map = {}
            return parsed
        except ValidationError:
            weak_points = data.get("weak_points")
            if not isinstance(weak_points, list):
                weak_points = []
            error_patterns = data.get("error_patterns")
            if isinstance(error_patterns, str):
                error_patterns = [error_patterns]
            elif not isinstance(error_patterns, list):
                error_patterns = []
            return MemoryProfilePayload(
                weak_points=[str(item).strip() for item in weak_points if str(item).strip()],
                knowledge_foundation=str(data.get("knowledge_foundation") or "").strip(),
                error_patterns=[
                    str(item).strip()
                    for item in error_patterns
                    if str(item).strip()
                ],
                learning_style=str(data.get("learning_style") or "").strip(),
                current_goal=str(data.get("current_goal") or "").strip(),
                resource_preference=str(data.get("resource_preference") or "").strip(),
                learning_rhythm=str(data.get("learning_rhythm") or "").strip(),
                self_regulation=str(data.get("self_regulation") or "").strip(),
                mastery_map={},
            )

    def refresh_profile(self, user_id: UUID | str) -> dict[str, Any]:
        with Session(engine) as session:
            history = self.collect_recent_chat_history(session, user_id)
            if not history:
                return {"status": "skipped", "reason": "no_history"}
            previous_profile = self.get_profile_dict(session, user_id) or {}
            payload = self.infer_profile_from_history(history)
            # A missing extraction means "no new observation", not "erase the
            # longitudinal value". Explicit replacements remain versioned by
            # ``build_dialogue_profile_dimensions`` below.
            for field in (
                "knowledge_foundation",
                "current_goal",
                "learning_style",
                "resource_preference",
                "learning_rhythm",
                "self_regulation",
            ):
                if not str(getattr(payload, field) or "").strip():
                    setattr(payload, field, str(previous_profile.get(field) or "").strip())
            if not payload.error_patterns:
                payload.error_patterns = [
                    str(item).strip()
                    for item in (previous_profile.get("error_patterns") or [])
                    if str(item).strip()
                ]
            if not payload.weak_points:
                payload.weak_points = [
                    str(item).strip()
                    for item in (previous_profile.get("weak_points") or [])
                    if str(item).strip()
                ]
            # Natural-language history may describe a question, goal, or topic,
            # but it is not a scored mastery observation. Only the trusted
            # evidence ledger is allowed to populate mastery_map.
            from app.services.learning_report_service import learning_report_service

            evidence = learning_report_service.evidence_confidence(session, user_id)
            payload.mastery_map = {
                str(details.get("display_name") or point): self._clamp_mastery(estimate)
                for point, details in evidence.items()
                if (estimate := details.get("mastery_estimate")) is not None
            }
            if payload.mastery_map:
                payload.weak_points = [
                    topic
                    for topic, score in sorted(
                        payload.mastery_map.items(), key=lambda item: item[1]
                    )
                    if score < 0.6
                ][:6]
            history_ref = hashlib.sha256(history.encode("utf-8")).hexdigest()[:24]
            profile_dimensions = self.build_dialogue_profile_dimensions(
                payload,
                previous_dimensions=previous_profile.get("profile_dimensions") or {},
                source_ref=f"chat_digest:{history_ref}",
            )
            if payload.mastery_map:
                evidence_timestamp = max(
                    (
                        str(details.get("latest_observed_at") or "")
                        for details in evidence.values()
                    ),
                    default=datetime.now(timezone.utc).isoformat(),
                )
                profile_dimensions["knowledge_mastery"] = self._dimension_record(
                    key="knowledge_mastery",
                    value={
                        "mastery_map": payload.mastery_map,
                        "weak_points": payload.weak_points,
                    },
                    source_type="learning_evidence",
                    source_ref="evidence_ledger",
                    previous=(previous_profile.get("profile_dimensions") or {}).get(
                        "knowledge_mastery"
                    ),
                    updated_at=evidence_timestamp,
                )
            payload.mastery_update = {
                "formula": "trusted_learning_evidence_weighted_beta_v1",
                "source": "learning_evidence",
                "topic_count": len(payload.mastery_map),
            }
            payload.profile_dimensions = profile_dimensions
            payload.profile_schema_version = self.PROFILE_SCHEMA_VERSION
            self.upsert_profile(session, user_id=user_id, payload=payload)
            return {
                "status": "success",
                "user_id": str(user_id),
                "profile": payload.model_dump(),
            }


user_memory_profile_service = UserMemoryProfileService()
