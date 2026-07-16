from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.models.learning_evidence import LearningEvidence
from app.models.resource_run import CourseKnowledgeNode
from app.schemas.learning_report import (
    DynamicProfileDimension,
    LearningReport,
    LearningReportSection,
    PortraitDimensionAssessment,
    PortraitAnalytics,
    PortraitAnalyticsCapability,
    PortraitAnalyticsCourse,
    PortraitAnalyticsResourcePreference,
    PortraitAnalyticsRhythm,
    PortraitAnalyticsSeries,
    ProcessStep,
    ReviewPlan,
    ReviewPlanDay,
    MistakeDigest,
    MistakeDigestItem,
)
from app.services.chat_model_factory import ChatModelFactory
from app.services.user_memory_profile_service import user_memory_profile_service
from app.services.learning_path_service import learning_path_service
from app.services.student_link_service import resolve_student_or_user_id

# 教育学参数联动导入
try:
    from app.models import BehaviorSummaryRecord
    BEHAVIOR_MODEL_AVAILABLE = True
except ImportError:
    BEHAVIOR_MODEL_AVAILABLE = False


class _LearningReportPayload(BaseModel):
    summary: str = ""
    risk_level: str = "medium"
    strengths: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    recommended_resources: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)


class _ReviewPlanPayload(BaseModel):
    summary: str = ""
    focus_topics: list[str] = Field(default_factory=list)
    daily_plan: list[dict[str, Any]] = Field(default_factory=list)
    checkpoints: list[str] = Field(default_factory=list)


class _MistakeDigestPayload(BaseModel):
    summary: str = ""
    mistakes: list[dict[str, Any]] = Field(default_factory=list)
    flashcards: list[str] = Field(default_factory=list)


# ==================== 教育学参数联动：课堂行为上下文 ====================

class _ClassroomBehaviorSummary(BaseModel):
    """课堂行为摘要，附加到学情诊断报告中"""
    recent_avg_lei: float = 0.0
    dominant_cognitive_state: str = ""
    mind_wandering_rate: float = 0.0
    bloom_distribution: dict[str, float] = Field(default_factory=dict)
    teacher_note: str = ""


class LearningReportService:
    MASTERY_SOURCE_TYPES = {"quiz", "exam", "assignment", "exercise_grading", "teacher_assessment"}
    MASTERY_EVENT_TYPES = {"graded", "submitted_and_graded", "teacher_scored", "assessment_completed"}
    KNOWLEDGE_POINT_ALIASES: dict[str, str] = {
        "acid": "数据库事务acid特性",
        "事务acid特性": "数据库事务acid特性",
        "数据库事务特性": "数据库事务acid特性",
        "数据库事务acid特性": "数据库事务acid特性",
    }
    STABLE_KNOWLEDGE_POINT_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,79}$")
    UNSCOPED_INTERACTION_KEY = "unscopedlearninginteraction"
    TRUSTED_GRAPH_SOURCES = {"course_plan", "curriculum"}

    @staticmethod
    def normalize_knowledge_point(value: str) -> str:
        normalized = unicodedata.normalize("NFKC", value).strip().lower()
        normalized = re.sub(r"[\s\-_—–/]+", "", normalized)
        normalized = re.sub(r"[，。；：、,.!?！？()（）\[\]【】]", "", normalized)
        if not normalized:
            raise ValueError("knowledge_point normalizes to empty")
        return LearningReportService.KNOWLEDGE_POINT_ALIASES.get(normalized, normalized)[:160]

    def resolve_knowledge_identity(
        self,
        session: Session,
        *,
        course_id: UUID | None,
        knowledge_point: str,
        knowledge_point_id: str | None,
        course_nodes: list[CourseKnowledgeNode] | None = None,
    ) -> dict[str, Any]:
        """Resolve a mastery-safe identity without promoting free-form queries.

        Course-scoped identities must match a curriculum concept node. Outside a
        course, only an explicit machine-style stable ID is accepted. Everything
        else remains a durable interaction/exposure record under a neutral key.
        """
        raw_id = (knowledge_point_id or "").strip()
        display_name = knowledge_point.strip()[:160]
        if course_id:
            nodes = course_nodes
            if nodes is None:
                nodes = session.exec(
                    select(CourseKnowledgeNode).where(
                        CourseKnowledgeNode.course_id == course_id,
                        CourseKnowledgeNode.map_type == "knowledge",
                        CourseKnowledgeNode.node_type == "concept",
                    )
                ).all()
            normalized_candidates = {
                self.normalize_knowledge_point(raw_id) if raw_id else "",
                self.normalize_knowledge_point(knowledge_point),
            }
            for node in nodes:
                source = str((node.attributes or {}).get("source") or "")
                if source not in self.TRUSTED_GRAPH_SOURCES:
                    continue
                node_labels = {
                    str(node.id),
                    node.normalized_key,
                    self.normalize_knowledge_point(node.label),
                }
                if (raw_id and raw_id in node_labels) or node_labels.intersection(
                    normalized_candidates
                ):
                    return {
                        "trusted": True,
                        "reason": "verified_course_graph_node",
                        "canonical": node.normalized_key,
                        "display_name": node.label,
                        "knowledge_point_id": str(node.id),
                    }
        elif raw_id and self.STABLE_KNOWLEDGE_POINT_ID.fullmatch(raw_id):
            return {
                "trusted": True,
                "reason": "explicit_stable_id",
                "canonical": self.normalize_knowledge_point(raw_id),
                "display_name": display_name or raw_id,
                "knowledge_point_id": raw_id,
            }
        return {
            "trusted": False,
            "reason": "untrusted_free_text",
            "canonical": self.UNSCOPED_INTERACTION_KEY,
            "display_name": display_name or "学习交互",
            "knowledge_point_id": None,
        }

    def record_evidence(
        self,
        session: Session,
        *,
        user_id: UUID,
        knowledge_point: str,
        knowledge_point_id: str | None = None,
        idempotency_key: str | None = None,
        source_type: str,
        source_id: str,
        event_type: str,
        course_id: UUID | None = None,
        run_id: str | None = None,
        observed_at: datetime | None = None,
        weight: float = 1.0,
        score: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> LearningEvidence:
        identity = self.resolve_knowledge_identity(
            session,
            course_id=course_id,
            knowledge_point=knowledge_point,
            knowledge_point_id=knowledge_point_id,
        )
        display_name = str(identity["display_name"])
        canonical = str(identity["canonical"])
        resolved_point_id = identity["knowledge_point_id"]
        normalized_score = None if score is None else max(0.0, min(1.0, float(score)))
        evidence_payload = dict(payload or {})
        evidence_payload["knowledge_identity"] = {
            "trusted": bool(identity["trusted"]),
            "reason": str(identity["reason"]),
        }
        if not identity["trusted"] and normalized_score is not None:
            evidence_payload["observed_score"] = normalized_score
            normalized_score = None
        identity_payload = {
            "course_id": str(course_id or ""),
            "knowledge_point": canonical,
            "knowledge_point_id": resolved_point_id or "",
            "source_type": source_type.strip().lower(),
            "source_id": source_id.strip(),
            "event_type": event_type.strip().lower(),
        }
        computed_key = idempotency_key or hashlib.sha256(
            json.dumps(identity_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        existing = session.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == user_id,
                LearningEvidence.idempotency_key == computed_key,
            )
        ).first()
        if existing:
            return existing
        evidence = LearningEvidence(
            user_id=user_id,
            course_id=course_id,
            run_id=run_id,
            knowledge_point=canonical,
            display_name=display_name,
            knowledge_point_id=resolved_point_id,
            idempotency_key=computed_key,
            source_type=source_type.strip().lower()[:48],
            source_id=source_id.strip()[:160],
            event_type=event_type.strip().lower()[:48],
            observed_at=observed_at or datetime.now(timezone.utc),
            weight=max(0.0, min(5.0, float(weight))),
            score=normalized_score,
            payload=evidence_payload,
        )
        session.add(evidence)
        session.flush([evidence])
        if (
            bool(identity["trusted"])
            and evidence.score is not None
            and evidence.source_type in self.MASTERY_SOURCE_TYPES
            and evidence.event_type in self.MASTERY_EVENT_TYPES
        ):
            # Keep the profile snapshot in the same transaction as its source
            # evidence. Exposure/resource events never cross this boundary.
            user_memory_profile_service.apply_learning_evidence_update(
                session,
                user_id=user_id,
                evidence_summary=self.evidence_confidence(session, user_id),
                evidence_id=evidence.id,
                evidence_payload=evidence.payload,
                observed_at=evidence.observed_at,
            )
        # Every durable interaction contributes to qualitative dimensions and
        # retrieval context. This path never changes mastery scores.
        user_memory_profile_service.apply_behavioral_evidence_update(
            session,
            user_id=user_id,
            evidence_id=evidence.id,
            observed_at=evidence.observed_at,
        )
        return evidence

    def evidence_confidence(
        self,
        session: Session,
        user_id: UUID | str,
        *,
        course_id: UUID | None = None,
        exact_course_scope: bool = False,
        now: datetime | None = None,
        observed_before: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        query = select(LearningEvidence).where(LearningEvidence.user_id == uid)
        if course_id:
            query = query.where(LearningEvidence.course_id == course_id)
        elif exact_course_scope:
            query = query.where(LearningEvidence.course_id.is_(None))
        if observed_before is not None:
            query = query.where(LearningEvidence.observed_at <= observed_before)
        records = session.exec(query.order_by(LearningEvidence.observed_at.desc())).all()
        trust_cache: dict[tuple[UUID | None, str | None, str], bool] = {}
        course_nodes_cache: dict[UUID, list[CourseKnowledgeNode]] = {}
        trusted_records: list[LearningEvidence] = []
        for row in records:
            cache_key = (row.course_id, row.knowledge_point_id, row.knowledge_point)
            trusted = trust_cache.get(cache_key)
            if trusted is None:
                course_nodes = None
                if row.course_id:
                    course_nodes = course_nodes_cache.get(row.course_id)
                    if course_nodes is None:
                        course_nodes = session.exec(
                            select(CourseKnowledgeNode).where(
                                CourseKnowledgeNode.course_id == row.course_id,
                                CourseKnowledgeNode.map_type == "knowledge",
                                CourseKnowledgeNode.node_type == "concept",
                            )
                        ).all()
                        course_nodes_cache[row.course_id] = course_nodes
                identity = self.resolve_knowledge_identity(
                    session,
                    course_id=row.course_id,
                    knowledge_point=row.display_name or row.knowledge_point,
                    knowledge_point_id=row.knowledge_point_id,
                    course_nodes=course_nodes,
                )
                trusted = bool(identity["trusted"])
                trust_cache[cache_key] = trusted
            if trusted:
                trusted_records.append(row)
        records = trusted_records
        grouped: dict[str, list[LearningEvidence]] = {}
        for row in records:
            grouped.setdefault(row.knowledge_point, []).append(row)
        reference = now or datetime.now(timezone.utc)
        output: dict[str, dict[str, Any]] = {}
        for point, items in grouped.items():
            mastery_items = [
                item for item in items
                if item.score is not None
                and item.source_type in self.MASTERY_SOURCE_TYPES
                and item.event_type in self.MASTERY_EVENT_TYPES
            ]
            exposure_items = [item for item in items if item not in mastery_items]
            independent_sources = len({(item.source_type, item.source_id) for item in mastery_items})
            source_type_counts = Counter(item.source_type for item in mastery_items)
            effective_weights: list[float] = []
            for item in mastery_items:
                observed = item.observed_at
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
                age_days = max(0.0, (reference - observed).total_seconds() / 86400)
                time_decay = math.exp(-age_days / 45.0)
                # Evidence emitted by the same source family shares methodology
                # and errors. Splitting its total influence by sqrt(n) prevents
                # one source family from dominating while retaining information.
                source_decorrelation = 1.0 / math.sqrt(source_type_counts[item.source_type])
                effective_weights.append(max(item.weight, 0.0) * time_decay * source_decorrelation)
            prior_alpha = 1.0
            prior_beta = 1.0
            alpha = prior_alpha + sum(
                weight * float(item.score)
                for item, weight in zip(mastery_items, effective_weights, strict=True)
            )
            beta = prior_beta + sum(
                weight * (1.0 - float(item.score))
                for item, weight in zip(mastery_items, effective_weights, strict=True)
            )
            posterior_mean = alpha / (alpha + beta)
            posterior_variance = (alpha * beta) / (
                ((alpha + beta) ** 2) * (alpha + beta + 1.0)
            )
            margin = 1.96 * math.sqrt(posterior_variance)
            credible_low = max(0.0, posterior_mean - margin)
            credible_high = min(1.0, posterior_mean + margin)
            interval_width = credible_high - credible_low
            confidence = round(max(0.0, 1.0 - interval_width), 4) if mastery_items else 0.0
            effective_sample_size = sum(effective_weights)
            mastery_estimate = None
            if mastery_items:
                mastery_estimate = round(posterior_mean, 4)
            output[point] = {
                "display_name": items[0].display_name,
                "confidence": confidence,
                "evidence_count": len(mastery_items),
                "exposure_evidence_count": len(exposure_items),
                "total_evidence_count": len(items),
                "independent_source_count": independent_sources,
                "latest_observed_at": items[0].observed_at.isoformat(),
                "mastery_estimate": mastery_estimate,
                "effective_sample_size": round(effective_sample_size, 4),
                "posterior": {
                    "prior": "Beta(1, 1)",
                    "alpha": round(alpha, 4),
                    "beta": round(beta, 4),
                    "variance": round(posterior_variance, 6),
                    "normal_approx_interval_95": [round(credible_low, 4), round(credible_high, 4)],
                    "interval_width": round(interval_width, 4),
                },
                "weighting": {
                    "version": "weighted_beta_v1",
                    "prior": {"alpha": prior_alpha, "beta": prior_beta},
                    "time_decay": "exp(-age_days/45)",
                    "source_decorrelation": "1/sqrt(evidence_count_in_source_type)",
                    "eligible_sources": sorted(self.MASTERY_SOURCE_TYPES),
                    "eligible_events": sorted(self.MASTERY_EVENT_TYPES),
                },
                "formula": "alpha=1+sum(w*s); beta=1+sum(w*(1-s)); w=base_weight*time_decay*source_decorrelation",
            }
        return output

    @staticmethod
    def _aware(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _mean(values: list[float | None]) -> float | None:
        available = [float(value) for value in values if value is not None]
        if not available:
            return None
        return round(sum(available) / len(available), 1)

    @staticmethod
    def _score_rows(
        rows: list[LearningEvidence],
        *,
        source_types: set[str] | None = None,
        task_types: set[str] | None = None,
    ) -> float | None:
        eligible: list[tuple[float, float]] = []
        for row in rows:
            if row.score is None:
                continue
            if source_types is not None and row.source_type not in source_types:
                continue
            payload = row.payload or {}
            if task_types is not None:
                task_type = str(
                    payload.get("task_type")
                    or payload.get("activity_type")
                    or payload.get("assessment_type")
                    or ""
                ).lower()
                if task_type not in task_types:
                    continue
            eligible.append((float(row.score), max(0.01, float(row.weight))))
        if not eligible:
            return None
        total_weight = sum(weight for _, weight in eligible)
        return round(100.0 * sum(score * weight for score, weight in eligible) / total_weight, 1)

    @staticmethod
    def _self_regulation_score(rows: list[LearningEvidence]) -> float | None:
        values: list[float] = []
        for row in rows:
            execution = (row.payload or {}).get("task_execution")
            if not isinstance(execution, dict):
                continue
            for key in ("completion_rate", "on_time_rate", "score"):
                raw = execution.get(key)
                if raw is None:
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue
                values.append(max(0.0, min(100.0, value * 100.0 if value <= 1 else value)))
                break
        return LearningReportService._mean(values)

    def _activity_times(
        self,
        session: Session,
        user_id: UUID,
        evidence_rows: list[LearningEvidence],
    ) -> list[datetime]:
        chat_times = session.exec(
            select(Chat.created_at)
            .join(ChatThread, Chat.thread_id == ChatThread.thread_id)
            .where(ChatThread.user_id == str(user_id))
        ).all()
        times = [self._aware(row.observed_at) for row in evidence_rows]
        times.extend(
            self._aware(created_at)
            for created_at in chat_times
            if created_at is not None
        )
        return sorted(times)

    @staticmethod
    def _engagement_score(activity_times: list[datetime], cutoff: datetime) -> float | None:
        window_start = cutoff - timedelta(days=30)
        active_days = {
            item.date()
            for item in activity_times
            if window_start <= item <= cutoff
        }
        if not active_days:
            return None
        # 以每周 3 个有效学习日作为满投入基准；只统计真实事件日期。
        return round(min(100.0, len(active_days) / 12.0 * 100.0), 1)

    def _knowledge_score_at(
        self,
        rows: list[LearningEvidence],
        cutoff: datetime,
    ) -> float | None:
        """Rebuild the weighted-Beta mastery snapshot without repeated DB reads.

        The endpoint computes fourteen snapshots (current, 30-day baseline and
        twelve weekly points). Re-querying and re-validating the same evidence
        for every point made response time grow with both history and graph
        size. Trust has already been established when evidence is persisted, so
        the analytics path can reuse that immutable marker and the same
        time-decay/source-decorrelation formula in memory.
        """
        eligible = [
            row
            for row in rows
            if self._aware(row.observed_at) <= cutoff
            and row.score is not None
            and row.source_type in self.MASTERY_SOURCE_TYPES
            and row.event_type in self.MASTERY_EVENT_TYPES
            and bool(((row.payload or {}).get("knowledge_identity") or {}).get("trusted"))
        ]
        grouped: dict[str, list[LearningEvidence]] = {}
        for row in eligible:
            grouped.setdefault(row.knowledge_point, []).append(row)
        scores: list[float] = []
        for items in grouped.values():
            source_type_counts = Counter(item.source_type for item in items)
            alpha = 1.0
            beta = 1.0
            for item in items:
                observed = self._aware(item.observed_at)
                age_days = max(0.0, (cutoff - observed).total_seconds() / 86400)
                weight = (
                    max(float(item.weight), 0.0)
                    * math.exp(-age_days / 45.0)
                    / math.sqrt(source_type_counts[item.source_type])
                )
                alpha += weight * float(item.score)
                beta += weight * (1.0 - float(item.score))
            scores.append(alpha / (alpha + beta) * 100.0)
        return self._mean(scores)

    def _capability_snapshot(
        self,
        evidence_rows: list[LearningEvidence],
        activity_times: list[datetime],
        cutoff: datetime,
    ) -> dict[str, float | None]:
        eligible = [
            row
            for row in evidence_rows
            if self._aware(row.observed_at) <= cutoff
            and row.score is not None
            and row.source_type in self.MASTERY_SOURCE_TYPES
            and row.event_type in self.MASTERY_EVENT_TYPES
            and bool(((row.payload or {}).get("knowledge_identity") or {}).get("trusted"))
        ]
        return {
            "knowledge_understanding": self._knowledge_score_at(evidence_rows, cutoff),
            "problem_solving": self._score_rows(
                eligible,
                source_types={"quiz", "exam", "exercise_grading"},
            ),
            "practice_transfer": self._score_rows(
                eligible,
                source_types={"assignment", "teacher_assessment"},
            ),
            "innovation_application": self._score_rows(
                eligible,
                task_types={"application", "case", "project", "practical", "innovation"},
            ),
            "learning_engagement": self._engagement_score(activity_times, cutoff),
            "self_regulation": self._self_regulation_score(eligible),
        }

    def _rhythm_analytics(
        self,
        activity_times: list[datetime],
        now: datetime,
    ) -> PortraitAnalyticsRhythm:
        monday = (now - timedelta(days=now.weekday())).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        week_starts = [monday - timedelta(weeks=offset) for offset in range(4, -1, -1)]
        matrix = [[0.0 for _ in range(7)] for _ in range(5)]
        for item in activity_times:
            for index, week_start in enumerate(week_starts):
                if week_start <= item < week_start + timedelta(days=7):
                    matrix[index][item.weekday()] += 1.0
                    break
        peak = max((value for row in matrix for value in row), default=0.0)
        normalized = [
            [round(value / peak * 100.0, 1) if peak else 0.0 for value in row]
            for row in matrix
        ]

        recent = [item for item in activity_times if now - timedelta(days=84) <= item <= now]
        sessions: list[tuple[datetime, datetime]] = []
        for item in recent:
            if not sessions or item - sessions[-1][1] > timedelta(minutes=45):
                sessions.append((item, item))
            else:
                sessions[-1] = (sessions[-1][0], item)
        hour_totals = [0.0 for _ in range(6)]
        hour_counts = [0 for _ in range(6)]
        for started, ended in sessions:
            duration = max(0.25, min(4.0, (ended - started).total_seconds() / 3600.0 + 0.25))
            bucket = min(5, started.hour // 4)
            hour_totals[bucket] += duration
            hour_counts[bucket] += 1
        focus = [
            round(total / count, 2) if count else 0.0
            for total, count in zip(hour_totals, hour_counts, strict=True)
        ]
        return PortraitAnalyticsRhythm(
            week_labels=[f"第{index}周" for index in range(8, 13)],
            day_labels=["一", "二", "三", "四", "五", "六", "日"],
            activity=normalized,
            hour_labels=["00", "04", "08", "12", "16", "20"],
            focus_hours=focus,
        )

    def build_portrait_analytics(
        self,
        session: Session,
        user_id: UUID | str,
        *,
        now: datetime | None = None,
    ) -> PortraitAnalytics:
        from app.models import Course, Resource

        uid = UUID(user_id) if isinstance(user_id, str) else user_id
        reference = self._aware(now or datetime.now(timezone.utc))
        evidence_rows = session.exec(
            select(LearningEvidence)
            .where(LearningEvidence.user_id == uid)
            .order_by(LearningEvidence.observed_at.asc())
        ).all()
        activity_times = self._activity_times(session, uid, evidence_rows)
        current = self._capability_snapshot(evidence_rows, activity_times, reference)
        previous_cutoff = reference - timedelta(days=30)
        previous = self._capability_snapshot(evidence_rows, activity_times, previous_cutoff)
        capability_labels = {
            "knowledge_understanding": "知识理解",
            "problem_solving": "问题解决",
            "practice_transfer": "实践迁移",
            "innovation_application": "创新应用",
            "learning_engagement": "学习投入",
            "self_regulation": "自我调节",
        }
        trusted_scored = [
            row
            for row in evidence_rows
            if row.score is not None
            and row.source_type in self.MASTERY_SOURCE_TYPES
            and row.event_type in self.MASTERY_EVENT_TYPES
            and bool(((row.payload or {}).get("knowledge_identity") or {}).get("trusted"))
        ]

        def task_type(row: LearningEvidence) -> str:
            payload = row.payload or {}
            return str(
                payload.get("task_type")
                or payload.get("activity_type")
                or payload.get("assessment_type")
                or ""
            ).lower()

        capability_evidence_counts = {
            "knowledge_understanding": len(trusted_scored),
            "problem_solving": sum(
                row.source_type in {"quiz", "exam", "exercise_grading"}
                for row in trusted_scored
            ),
            "practice_transfer": sum(
                row.source_type in {"assignment", "teacher_assessment"}
                for row in trusted_scored
            ),
            "innovation_application": sum(
                task_type(row)
                in {"application", "case", "project", "practical", "innovation"}
                for row in trusted_scored
            ),
            "learning_engagement": len(
                {
                    item.date()
                    for item in activity_times
                    if reference - timedelta(days=30) <= item <= reference
                }
            ),
            "self_regulation": sum(
                isinstance((row.payload or {}).get("task_execution"), dict)
                for row in trusted_scored
            ),
        }
        capabilities = [
            PortraitAnalyticsCapability(
                key=key,
                label=label,
                value=current.get(key),
                previous=previous.get(key),
                evidence_count=capability_evidence_counts[key],
            )
            for key, label in capability_labels.items()
        ]

        week_cutoffs = [
            reference - timedelta(weeks=11 - index)
            for index in range(12)
        ]
        snapshots = [
            self._capability_snapshot(evidence_rows, activity_times, cutoff)
            for cutoff in week_cutoffs
        ]
        series_keys = [
            "knowledge_understanding",
            "problem_solving",
            "practice_transfer",
            "self_regulation",
        ]
        trend_series = []
        for key in series_keys:
            values = [snapshot.get(key) for snapshot in snapshots]
            if sum(value is not None for value in values) < 2:
                continue
            trend_series.append(
                PortraitAnalyticsSeries(
                    key=key,
                    label=capability_labels[key],
                    values=values,
                )
            )

        current_values = [item.value for item in capabilities]
        previous_values = [item.previous for item in capabilities]
        overall = self._mean(current_values)
        previous_overall = self._mean(previous_values)
        growth = (
            round(overall - previous_overall, 1)
            if overall is not None and previous_overall is not None
            else None
        )
        confidence_rows = self.evidence_confidence(session, uid)
        confidence = self._mean(
            [
                float(item.get("confidence") or 0.0) * 100.0
                for item in confidence_rows.values()
                if item.get("mastery_estimate") is not None
            ]
        )

        profile = user_memory_profile_service.get_profile_dict(session, uid) or {}
        dimension_versions = [
            int(item.get("version") or 1)
            for item in (profile.get("profile_dimensions") or {}).values()
            if isinstance(item, dict)
        ]
        version = max(dimension_versions, default=1)

        resources = session.exec(
            select(Resource).where(Resource.uploader_id == uid)
        ).all()
        resource_counts: Counter[str] = Counter()
        resource_labels = {
            "document": "文档阅读",
            "video": "视频/动画",
            "quiz": "测验练习",
            "case": "实践案例",
        }
        for resource in resources:
            text = f"{resource.title} {resource.type} {resource.file_name}".lower()
            if re.search(r"练习|测验|题库|quiz|test", text):
                key = "quiz"
            elif re.search(r"案例|实操|项目|实验|case|lab", text):
                key = "case"
            elif re.search(r"视频|动画|video|mp4|webm", text):
                key = "video"
            else:
                key = "document"
            resource_counts[key] += 1
        resource_total = sum(resource_counts.values())
        resource_preferences = [
            PortraitAnalyticsResourcePreference(
                key=key,
                label=resource_labels[key],
                count=count,
                value=round(count / resource_total * 100.0, 1),
            )
            for key, count in resource_counts.most_common()
        ] if resource_total else []

        course_ids = sorted({row.course_id for row in trusted_scored if row.course_id}, key=str)
        courses_by_id = {
            course.id: course
            for course in session.exec(select(Course).where(Course.id.in_(course_ids))).all()
        } if course_ids else {}
        course_rows: list[PortraitAnalyticsCourse] = []
        for course_id in course_ids[:4]:
            course_confidence = self.evidence_confidence(session, uid, course_id=course_id)
            previous_course = self.evidence_confidence(
                session,
                uid,
                course_id=course_id,
                now=previous_cutoff,
                observed_before=previous_cutoff,
            )
            score = self._mean([
                float(item["mastery_estimate"]) * 100.0
                for item in course_confidence.values()
                if item.get("mastery_estimate") is not None
            ])
            old_score = self._mean([
                float(item["mastery_estimate"]) * 100.0
                for item in previous_course.values()
                if item.get("mastery_estimate") is not None
            ])
            weakest = min(
                (
                    item
                    for item in course_confidence.values()
                    if item.get("mastery_estimate") is not None
                ),
                key=lambda item: float(item["mastery_estimate"]),
                default=None,
            )
            course = courses_by_id.get(course_id)
            if course is None:
                continue
            course_rows.append(
                PortraitAnalyticsCourse(
                    id=course_id,
                    name=course.name,
                    score=score,
                    trend=(
                        round(score - old_score, 1)
                        if score is not None and old_score is not None
                        else None
                    ),
                    focus=str((weakest or {}).get("display_name") or "继续积累课程证据"),
                    evidence_count=sum(
                        int(item.get("evidence_count") or 0)
                        for item in course_confidence.values()
                    ),
                )
            )

        return PortraitAnalytics(
            profile_version=version,
            generated_at=reference.isoformat(),
            evidence_count=len(trusted_scored),
            confidence=confidence,
            overall_score=overall,
            growth_30d=growth,
            engagement=current.get("learning_engagement"),
            attention_count=sum(
                value is not None and value < 65.0 for value in current.values()
            ),
            trend_labels=[f"第{index}周" for index in range(1, 13)],
            trend_series=trend_series,
            capabilities=capabilities,
            rhythm=self._rhythm_analytics(activity_times, reference),
            resource_preferences=resource_preferences,
            courses=course_rows,
        )

    @staticmethod
    def build_portrait_dimensions(
        *,
        evidence_confidence: dict[str, dict[str, Any]],
        evidence_rows: list[LearningEvidence],
        classroom_behavior_summary: dict[str, Any] | None,
    ) -> list[PortraitDimensionAssessment]:
        """Build the six-dimension portrait from persisted observations only.

        The dimensions are always present in the contract, while ``value`` is
        intentionally nullable.  This makes the minimum-six-dimension model
        explicit without turning missing observations into fabricated scores.
        """

        def normalize_score(value: Any) -> float | None:
            try:
                number = float(value)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(number):
                return None
            if 0.0 <= number <= 1.0:
                number *= 100.0
            return round(max(0.0, min(100.0, number)), 1)

        def summarize(values: list[float], *, minimum: int = 1) -> tuple[float | None, int]:
            if len(values) < minimum:
                return None, len(values)
            return round(sum(values) / len(values), 1), len(values)

        def state_for(value: float | None) -> str:
            if value is None:
                return "insufficient"
            if value >= 80:
                return "strong"
            if value >= 65:
                return "steady"
            return "needs_attention"

        trusted_rows = [
            row
            for row in evidence_rows
            if bool(((row.payload or {}).get("knowledge_identity") or {}).get("trusted"))
        ]
        scored_rows = [
            row
            for row in trusted_rows
            if row.score is not None
            and row.event_type in LearningReportService.MASTERY_EVENT_TYPES
        ]

        mastery_values: list[float] = []
        for details in evidence_confidence.values():
            value = normalize_score(details.get("mastery_estimate"))
            if value is not None:
                mastery_values.append(value)
        knowledge_value, knowledge_count = summarize(mastery_values)

        problem_values = [
            value
            for row in scored_rows
            if row.source_type in {"quiz", "exam", "exercise_grading"}
            and (value := normalize_score(row.score)) is not None
        ]
        problem_value, problem_count = summarize(problem_values)

        transfer_values: list[float] = []
        for row in scored_rows:
            payload = row.payload or {}
            task_kind = str(
                payload.get("task_type")
                or payload.get("activity_type")
                or payload.get("assessment_type")
                or ""
            ).lower()
            is_transfer_task = row.source_type == "teacher_assessment" or (
                row.source_type == "assignment"
                and task_kind in {"application", "case", "project", "practical", "transfer"}
            )
            if is_transfer_task and (value := normalize_score(row.score)) is not None:
                transfer_values.append(value)
        transfer_value, transfer_count = summarize(transfer_values)

        behavior = classroom_behavior_summary or {}
        engagement_value = normalize_score(
            behavior.get("behavioral_engagement") or behavior.get("recent_avg_lei")
        )
        cognitive_value = normalize_score(
            behavior.get("cognitive_engagement") or behavior.get("avg_cognitive_depth")
        )
        attention_value = normalize_score(behavior.get("on_task_rate"))
        if attention_value is None:
            mind_wandering = normalize_score(behavior.get("mind_wandering_rate"))
            attention_value = None if mind_wandering is None else round(100.0 - mind_wandering, 1)
        behavior_sample_size = max(0, int(behavior.get("student_count") or 0))
        if behavior and behavior_sample_size == 0:
            behavior_sample_size = 1
        updated_at = max(
            (row.observed_at for row in trusted_rows),
            default=None,
        )
        updated_at_text = updated_at.isoformat() if updated_at else None

        rows = [
            ("knowledge_foundation", "知识基础", knowledge_value, knowledge_count, ["graded_evidence"]),
            ("problem_solving", "问题解决", problem_value, problem_count, ["quiz", "exam", "exercise_grading"]),
            ("transfer_application", "迁移应用", transfer_value, transfer_count, ["assignment", "teacher_assessment"]),
            ("learning_engagement", "学习投入", engagement_value, behavior_sample_size if engagement_value is not None else 0, ["classroom_behavior"]),
            ("cognitive_engagement", "认知投入", cognitive_value, behavior_sample_size if cognitive_value is not None else 0, ["classroom_behavior"]),
            ("attention_stability", "注意稳定", attention_value, behavior_sample_size if attention_value is not None else 0, ["classroom_behavior"]),
        ]
        return [
            PortraitDimensionAssessment(
                key=key,
                label=label,
                value=value,
                state=state_for(value),
                sample_size=sample_size,
                sources=sources if sample_size else [],
                method_version="portrait_evidence_v1",
                updated_at=updated_at_text,
            )
            for key, label, value, sample_size, sources in rows
        ]

    def _recent_history(self, session: Session, user_id: str, limit: int = 12) -> list[Chat]:
        return (
            session.query(Chat)
            .join(ChatThread, ChatThread.thread_id == Chat.thread_id)
            .filter(ChatThread.user_id == user_id)
            .order_by(Chat.created_at.desc())
            .limit(limit)
            .all()
        )

    def _history_digest(self, history: list[Chat]) -> str:
        if not history:
            return "（暂无近期学习对话）"
        lines: list[str] = []
        for row in reversed(history):
            if row.user_input:
                lines.append(f"学生：{row.user_input.strip()[:180]}")
            if row.response:
                lines.append(f"助手：{row.response.strip()[:220]}")
        return "\n".join(lines)

    def _normalized_topics(self, profile: dict[str, Any] | None, history: list[Chat]) -> list[str]:
        weak_points = (
            [str(item).strip() for item in (profile.get("weak_points") or []) if str(item).strip()]
            if profile
            else []
        )
        if weak_points:
            return weak_points[:4]
        collected: list[str] = []
        for row in history[:6]:
            source = f"{row.user_input}\n{row.response}"
            for token in ("数据库", "操作系统", "计算机网络", "算法", "并发控制", "索引", "事务"):
                if token in source and token not in collected:
                    collected.append(token)
        return collected[:4] or ["核心概念理解", "错题订正", "阶段复盘"]

    def _fallback_payload(self, profile: dict[str, Any] | None) -> _LearningReportPayload:
        weak_points = list(profile.get("weak_points") or []) if profile else []
        current_goal = str(profile.get("current_goal") or "").strip() if profile else ""
        actions = []
        if weak_points:
            actions.append(f"优先复习：{'、'.join(weak_points[:3])}")
        if current_goal:
            actions.append(f"围绕“{current_goal}”拆分本周学习任务")
        actions.extend(
            [
                "先看核心概念，再做 2-3 道由浅入深的练习题",
                "对近期高频错误点建立个人速记卡片",
            ]
        )
        return _LearningReportPayload(
            summary="近期学习提问较集中，建议围绕薄弱点做短周期复习与练习闭环。",
            risk_level="medium" if weak_points else "low",
            strengths=["具备主动提问习惯", "愿意围绕具体问题持续追问"],
            recommended_actions=actions[:4],
            recommended_resources=[f"{point} 相关课程资料" for point in weak_points[:3]],
            follow_up_questions=[
                "我本周最先复习哪个知识点最划算？",
                "能给我 3 道递进练习题吗？",
                "如何快速判断自己是否真正掌握了这个知识点？",
            ],
        )

    def _fallback_review_plan(
        self,
        profile: dict[str, Any] | None,
        history: list[Chat],
    ) -> _ReviewPlanPayload:
        topics = self._normalized_topics(profile, history)
        return _ReviewPlanPayload(
            summary="建议采用 3 天一个小闭环的方式，把薄弱点拆成概念梳理、错题订正和迁移练习三步推进。",
            focus_topics=topics,
            daily_plan=[
                {
                    "day_label": "Day 1",
                    "focus": topics[0] if topics else "核心概念",
                    "tasks": ["回看课堂笔记与资料", "整理 3 个易混概念", "完成 2 道基础题"],
                },
                {
                    "day_label": "Day 2",
                    "focus": topics[1] if len(topics) > 1 else "错题订正",
                    "tasks": ["复盘近期错误", "总结失分原因", "各做 1 道变式题"],
                },
                {
                    "day_label": "Day 3",
                    "focus": topics[2] if len(topics) > 2 else "迁移训练",
                    "tasks": ["限时练习 3 题", "口头讲解解题过程", "标记仍不熟练的点"],
                },
            ],
            checkpoints=[
                "能否不看答案复述核心概念",
                "能否说清最近 3 个错误的原因",
                "能否在限时条件下完成同类题",
            ],
        )

    def _fallback_mistake_digest(
        self,
        profile: dict[str, Any] | None,
        history: list[Chat],
    ) -> _MistakeDigestPayload:
        topics = self._normalized_topics(profile, history)
        mistakes = []
        for topic in topics[:3]:
            mistakes.append(
                {
                    "title": topic,
                    "symptom": f"在 {topic} 相关问题上容易出现概念混淆或步骤不完整。",
                    "evidence": "近期问答中多次围绕该主题追问、纠错或请求复述。",
                    "fix_strategy": "先整理定义与关键条件，再各做 2 道同类题完成巩固。",
                }
            )
        return _MistakeDigestPayload(
            summary="已根据近期问答与学习画像整理出最值得优先复盘的错点，建议先处理高频重复出现的概念性问题。",
            mistakes=mistakes,
            flashcards=[
                f"{topic}：一句话定义 + 一个典型例子 + 一个常见陷阱"
                for topic in topics[:3]
            ],
        )

    def _mastery_insights(self, profile: dict[str, Any]) -> list[str]:
        mastery_map = profile.get("mastery_map") or {}
        if not isinstance(mastery_map, dict) or not mastery_map:
            return []
        normalized = []
        for topic, score in mastery_map.items():
            try:
                normalized.append((str(topic), float(score)))
            except (TypeError, ValueError):
                continue
        if not normalized:
            return []
        low = sorted(normalized, key=lambda item: item[1])[:3]
        high = sorted(normalized, key=lambda item: item[1], reverse=True)[:2]
        insights = [
            f"{topic} 掌握度约 {round(score * 100)}%，建议优先补齐概念与例题闭环。"
            for topic, score in low
            if score < 0.65
        ]
        insights.extend(
            f"{topic} 掌握度约 {round(score * 100)}%，可作为迁移练习或讲解输出的优势点。"
            for topic, score in high
            if score >= 0.72
        )
        return insights[:4]

    def _get_recent_behavior_context(self, session: Session, user_id: str) -> str:
        """获取学生最近3节课的课堂行为数据（教育学参数联动1）"""
        if not BEHAVIOR_MODEL_AVAILABLE:
            return ""
        try:
            from sqlalchemy import desc, or_
            uid = resolve_student_or_user_id(session, user_id)
            if uid is None:
                return ""
            # 优先查询该学生的个人记录；若无，则查询课堂整体记录（student_id=NULL）
            query = (
                session.query(BehaviorSummaryRecord)
                .filter(
                    or_(
                        BehaviorSummaryRecord.student_id == uid,
                        BehaviorSummaryRecord.student_id.is_(None),
                    )
                )
                .order_by(desc(BehaviorSummaryRecord.session_date))
                .limit(3)
            )
            records = query.all()
            if not records:
                return ""
            
            lines = ["【学生课堂表现数据（最近3节课）】"]
            for i, r in enumerate(records, 1):
                lines.append(f"第{i}节课 ({r.session_date.strftime('%m-%d')}):")
                lines.append(f"  - 学习投入指数(LEI): {r.avg_lei:.2f}")
                lines.append(f"  - 认知深度: {r.avg_cognitive_depth:.2f}")
                lines.append(f"  - 走神率: {r.mind_wandering_rate:.1%}")
                lines.append(f"  - 目标行为率: {r.on_task_rate:.1%}")
                if r.bloom_distribution:
                    import json
                    try:
                        bd = json.loads(r.bloom_distribution)
                        bd_str = ", ".join(f"{k}:{float(v):.0%}" for k, v in bd.items())
                        lines.append(f"  - 布鲁姆分布: {bd_str}")
                    except Exception:
                        pass
            
            # 生成教师备注
            avg_lei = sum(r.avg_lei for r in records) / len(records)
            avg_mw = sum(r.mind_wandering_rate for r in records) / len(records)
            if avg_lei < 0.4:
                note = "该生课堂投入度极低，诊断时应优先考虑注意力管理问题而非知识漏洞。"
            elif avg_lei < 0.6:
                note = "该生课堂投入度偏低，建议诊断中兼顾知识掌握与学习习惯。"
            elif avg_mw > 0.3:
                note = "该生课堂走神率较高，但投入度尚可，可能存在特定知识点听不懂导致的注意力漂移。"
            else:
                note = "该生课堂表现良好，诊断可聚焦于知识深度与拓展。"
            lines.append(f"\n[课堂行为综合判断] {note}")
            
            return "\n".join(lines)
        except Exception:
            return ""

    def _infer_payload(
        self,
        *,
        profile: dict[str, Any] | None,
        history_digest: str,
        behavior_context: str = "",
    ) -> _LearningReportPayload:
        current_goal = str(profile.get("current_goal") or "").strip() if profile else ""
        weak_points = (profile.get("weak_points") or []) if profile else []
        learning_style = str(profile.get("learning_style") or "").strip() if profile else ""
        behavior_section = f"\n{behavior_context}\n" if behavior_context else ""
        
        prompt = (
            "你是一名学情诊断助手。请根据学生长期画像、近期问答以及课堂行为数据，"
            "输出严格 JSON，字段包括：summary, risk_level, strengths, "
            "recommended_actions, recommended_resources, follow_up_questions。\n"
            "risk_level 只能是 low / medium / high。\n"
            "每个数组给 2-4 条，尽量简洁可执行。\n\n"
            "【重要】如果提供了课堂行为数据，请将其作为诊断的重要依据：\n"
            "- 课堂LEI<0.4且走神率高 → 风险等级应上调，建议优先解决注意力问题\n"
            "- 课堂LEI>0.7且认知深度高 → 风险等级应下调，可建议拓展性学习\n"
            "- 布鲁姆分布停留在remembering/understanding → 建议增加高阶思维训练\n\n"
            f"【当前目标】{current_goal or '暂无明确目标'}\n"
            f"【薄弱点】{'、'.join(weak_points) if weak_points else '暂无明确薄弱点'}\n"
            f"【学习偏好】{learning_style or '暂无明显偏好'}\n"
            f"【近期问答】\n{history_digest}"
            f"{behavior_section}"
        )
        try:
            llm = ChatModelFactory.create(temperature=0.2, max_tokens=900)
            structured = llm.with_structured_output(_LearningReportPayload)
            payload = structured.invoke([HumanMessage(content=prompt)])
            if isinstance(payload, _LearningReportPayload):
                return payload
            if isinstance(payload, dict):
                return _LearningReportPayload.model_validate(payload)
        except Exception:
            pass
        return self._fallback_payload(profile)

    def _get_behavior_for_review_plan(self, session: Session, user_id: str) -> str:
        """获取用于复习计划生成的课堂行为数据（教育学参数联动2）"""
        if not BEHAVIOR_MODEL_AVAILABLE:
            return ""
        try:
            from sqlalchemy import desc, or_
            uid = resolve_student_or_user_id(session, user_id)
            if uid is None:
                return ""
            # 优先查询该学生的个人记录；若无，则查询课堂整体记录
            query = (
                session.query(BehaviorSummaryRecord)
                .filter(
                    or_(
                        BehaviorSummaryRecord.student_id == uid,
                        BehaviorSummaryRecord.student_id.is_(None),
                    )
                )
                .order_by(desc(BehaviorSummaryRecord.session_date))
                .limit(3)
            )
            records = query.all()
            if not records:
                return ""
            
            lines = ["【学生课堂认知特征】"]
            import json
            avg_bloom: dict[str, float] = {}
            avg_depth = 0.0
            avg_mw = 0.0
            for r in records:
                avg_depth += r.avg_cognitive_depth
                avg_mw += r.mind_wandering_rate
                if r.bloom_distribution:
                    try:
                        bd = json.loads(r.bloom_distribution)
                        for k, v in bd.items():
                            avg_bloom[k] = avg_bloom.get(k, 0.0) + float(v)
                    except Exception:
                        pass
            
            n = len(records)
            avg_depth /= n
            avg_mw /= n
            for k in avg_bloom:
                avg_bloom[k] /= n
            
            bloom_str = ", ".join(f"{k}:{float(v):.0%}" for k, v in sorted(avg_bloom.items(), key=lambda x: -x[1]))
            lines.append(f"- 布鲁姆认知层次分布: {bloom_str}")
            lines.append(f"- 认知深度得分: {avg_depth:.2f}")
            lines.append(f"- 课堂走神率: {avg_mw:.1%}")
            
            # 生成规划约束
            constraints = []
            if avg_depth < 0.55:
                constraints.append("该生认知层次以低阶思维为主，复习计划中必须包含应用/分析类任务，禁止只做记忆性背诵。")
            if avg_depth > 0.80:
                constraints.append("该生认知深度较高，复习计划应加入挑战性题目和拓展阅读。")
            if avg_mw > 0.3:
                constraints.append("该生走神率较高，每日任务应拆分为25分钟以内的短模块（番茄工作法），并在每个模块后设置即时反馈。")
            if not constraints:
                constraints.append("该生课堂表现正常，按标准难度制定复习计划。")
            
            lines.append("\n【复习计划约束】")
            for c in constraints:
                lines.append(f"- {c}")
            
            return "\n".join(lines)
        except Exception:
            return ""

    def _infer_review_plan(
        self,
        *,
        profile: dict[str, Any] | None,
        history: list[Chat],
        history_digest: str,
        behavior_context: str = "",
    ) -> _ReviewPlanPayload:
        topics = self._normalized_topics(profile, history)
        behavior_section = f"\n{behavior_context}\n" if behavior_context else ""
        
        prompt = (
            "你是一名学习规划助手。请根据学生画像、近期问答以及课堂认知特征，输出严格 JSON。"
            "字段包括：summary, focus_topics, daily_plan, checkpoints。\n"
            "其中 daily_plan 为数组，每项包含 day_label, focus, tasks。"
            "请输出 3 天复习计划，每天 2-4 条任务，简洁可执行。\n\n"
            "【重要】如果有课堂认知特征数据，请严格遵循其约束条件调整任务类型和难度。\n"
            f"【薄弱点】{'、'.join(topics)}\n"
            f"【近期问答】\n{history_digest}"
            f"{behavior_section}"
        )
        try:
            llm = ChatModelFactory.create(temperature=0.2, max_tokens=900)
            structured = llm.with_structured_output(_ReviewPlanPayload)
            payload = structured.invoke([HumanMessage(content=prompt)])
            if isinstance(payload, _ReviewPlanPayload):
                return payload
            if isinstance(payload, dict):
                return _ReviewPlanPayload.model_validate(payload)
        except Exception:
            pass
        return self._fallback_review_plan(profile, history)

    def _get_attention_context_for_mistakes(self, session: Session, user_id: str, topics: list[str]) -> str:
        """获取错题注意力归因数据（教育学参数联动7）"""
        if not BEHAVIOR_MODEL_AVAILABLE or not topics:
            return ""
        try:
            from sqlalchemy import desc, or_
            uid = resolve_student_or_user_id(session, user_id)
            if uid is None:
                return ""
            # 优先查询该学生的个人记录；若无，则查询课堂整体记录
            query = (
                session.query(BehaviorSummaryRecord)
                .filter(
                    or_(
                        BehaviorSummaryRecord.student_id == uid,
                        BehaviorSummaryRecord.student_id.is_(None),
                    )
                )
                .order_by(desc(BehaviorSummaryRecord.session_date))
                .limit(5)
            )
            records = query.all()
            if not records:
                return ""
            
            lines = ["【错题-课堂注意力归因数据】"]
            avg_mw = sum(r.mind_wandering_rate for r in records) / len(records)
            avg_lei = sum(r.avg_lei for r in records) / len(records)
            
            lines.append(f"- 该生近期平均走神率: {avg_mw:.1%}")
            lines.append(f"- 该生近期平均学习投入指数: {avg_lei:.2f}")
            
            if avg_mw > 0.3 and avg_lei < 0.5:
                lines.append("- [归因判断] 该生课堂注意力问题严重，错题可能主要由于上课未听讲导致，建议优先重新听课而非盲目刷题。")
            elif avg_mw > 0.2:
                lines.append("- [归因判断] 该生存在一定注意力问题，错题可能兼有知识漏洞和听课不专注两种原因。")
            else:
                lines.append("- [归因判断] 该生课堂注意力正常，错题主要反映知识理解问题，建议针对性练习。")
            
            lines.append("\n【错题诊断要求】")
            lines.append("- 若归因判断为'上课未听讲'，请在symptom中明确指出'课堂注意力不集中导致概念遗漏'")
            lines.append("- 若归因判断为'知识理解问题'，请深入分析概念误解的具体表现")
            lines.append("- fix_strategy必须对应归因结论：注意力问题→重新听课；知识问题→针对性练习")
            
            return "\n".join(lines)
        except Exception:
            return ""

    def _infer_mistake_digest(
        self,
        *,
        profile: dict[str, Any] | None,
        history: list[Chat],
        history_digest: str,
        behavior_context: str = "",
    ) -> _MistakeDigestPayload:
        topics = self._normalized_topics(profile, history)
        behavior_section = f"\n{behavior_context}\n" if behavior_context else ""
        
        prompt = (
            "你是一名错题整理助手。请根据学生画像、近期问答以及课堂注意力归因数据，输出严格 JSON。"
            "字段包括：summary, mistakes, flashcards。"
            "mistakes 为数组，每项包含 title, symptom, evidence, fix_strategy。"
            "请优先整理最值得优先复盘的 3 个错点。\n\n"
            "【重要】如果归因数据指出'课堂注意力不集中'，则诊断结论必须区分'真不会'和'没听'，"
            "fix_strategy不能一味地建议'刷更多题'，对于注意力问题应建议'重新听课/回顾笔记'。\n"
            f"【候选薄弱点】{'、'.join(topics)}\n"
            f"【近期问答】\n{history_digest}"
            f"{behavior_section}"
        )
        try:
            llm = ChatModelFactory.create(temperature=0.2, max_tokens=900)
            structured = llm.with_structured_output(_MistakeDigestPayload)
            payload = structured.invoke([HumanMessage(content=prompt)])
            if isinstance(payload, _MistakeDigestPayload):
                return payload
            if isinstance(payload, dict):
                return _MistakeDigestPayload.model_validate(payload)
        except Exception:
            pass
        return self._fallback_mistake_digest(profile, history)

    def build_report(self, session: Session, user_id: str, *, refresh_profile: bool = False) -> LearningReport:
        if refresh_profile:
            try:
                user_memory_profile_service.refresh_profile(user_id)
                # The profile refresh commits in its own short-lived session.
                # Expire this request session so it observes that committed row.
                session.expire_all()
            except Exception:
                pass
        profile = user_memory_profile_service.get_profile_dict(session, user_id) or {}
        history = self._recent_history(session, user_id)
        digest = self._history_digest(history)
        
        # 教育学参数联动1：注入课堂行为上下文
        behavior_context = self._get_recent_behavior_context(session, user_id)
        # A normal GET is a deterministic read of persisted profile/evidence.
        # Remote diagnosis is opt-in through ``refresh=true`` only; otherwise a
        # page visit would pay model latency and make an ostensibly read-only
        # endpoint nondeterministic.
        payload = (
            self._infer_payload(
                profile=profile,
                history_digest=digest,
                behavior_context=behavior_context,
            )
            if refresh_profile
            else self._fallback_payload(profile)
        )
        weak_points = [str(item).strip() for item in profile.get("weak_points") or [] if str(item).strip()]
        evidence_confidence = self.evidence_confidence(session, user_id)
        mastery_map = {
            str(details.get("display_name") or point): round(float(estimate), 4)
            for point, details in evidence_confidence.items()
            if (estimate := details.get("mastery_estimate")) is not None
        }
        mastery_update = profile.get("mastery_update") or {}
        sections = [
            LearningReportSection(title="近期学习概览", content=payload.summary or "暂无总结"),
            LearningReportSection(
                title="建议复习动作",
                content="\n".join(f"- {item}" for item in payload.recommended_actions) or "暂无建议",
            ),
        ]
        if mastery_map:
            sections.append(
                LearningReportSection(
                    title="知识掌握度更新",
                    content="\n".join(
                        f"- {topic}: {round(score * 100)}%"
                        for topic, score in sorted(mastery_map.items(), key=lambda item: item[1])
                    ),
                )
            )
        
        # 教育学参数联动：附加课堂行为摘要
        classroom_behavior_summary = None
        if behavior_context:
            try:
                from sqlalchemy import desc
                uid = resolve_student_or_user_id(session, user_id)
                latest_record = None
                if uid is not None:
                    from sqlalchemy import or_
                    latest_record = (
                        session.query(BehaviorSummaryRecord)
                        .filter(
                            or_(
                                BehaviorSummaryRecord.student_id == uid,
                                BehaviorSummaryRecord.student_id.is_(None),
                            )
                        )
                        .order_by(desc(BehaviorSummaryRecord.session_date))
                        .first()
                    )
                if latest_record:
                    import json
                    bd = {}
                    if latest_record.bloom_distribution:
                        try:
                            bd = json.loads(latest_record.bloom_distribution)
                        except Exception:
                            pass
                    # 解析个体画像快照中的三维投入指标
                    snapshot = {}
                    if latest_record.student_profiles_snapshot:
                        try:
                            snapshot = json.loads(latest_record.student_profiles_snapshot)
                        except Exception:
                            pass
                    classroom_behavior_summary = {
                        "recent_avg_lei": round(latest_record.avg_lei, 3),
                        "avg_cognitive_depth": round(latest_record.avg_cognitive_depth, 3),
                        "mind_wandering_rate": round(latest_record.mind_wandering_rate, 3),
                        "contagion_index": round(latest_record.contagion_index, 3),
                        "on_task_rate": round(latest_record.on_task_rate, 3),
                        "dominant_cognitive_state": "",
                        "bloom_distribution": bd,
                        "teacher_note": "课堂表现已纳入诊断参考",
                        "behavioral_engagement": snapshot.get("class_behavioral_engagement", 0),
                        "cognitive_engagement": snapshot.get("class_cognitive_engagement", 0),
                        "emotional_engagement": snapshot.get("class_emotional_engagement", 0),
                        "attention_cycle_phase": snapshot.get("attention_cycle_phase"),
                        "class_attention_trend": snapshot.get("class_attention_trend"),
                        "student_count": snapshot.get("student_count", 0),
                    }
            except Exception:
                pass

        try:
            portrait_evidence_rows = session.exec(
                select(LearningEvidence)
                .where(LearningEvidence.user_id == UUID(user_id))
                .order_by(LearningEvidence.observed_at.desc())
                .limit(200)
            ).all()
        except (TypeError, ValueError):
            portrait_evidence_rows = []
        portrait_dimensions = self.build_portrait_dimensions(
            evidence_confidence=evidence_confidence,
            evidence_rows=list(portrait_evidence_rows),
            classroom_behavior_summary=classroom_behavior_summary,
        )
        stored_dynamic_dimensions = profile.get("profile_dimensions") or {}
        dynamic_profile_dimensions: list[DynamicProfileDimension] = []
        for key, label in user_memory_profile_service.PROFILE_DIMENSIONS.items():
            raw = stored_dynamic_dimensions.get(key) or {
                "key": key,
                "label": label,
                "value": None,
                "source_type": "insufficient",
                "version": 1,
                "method_version": user_memory_profile_service.PROFILE_SCHEMA_VERSION,
            }
            try:
                dynamic_profile_dimensions.append(DynamicProfileDimension.model_validate(raw))
            except Exception:
                dynamic_profile_dimensions.append(
                    DynamicProfileDimension(key=key, label=label)
                )
        
        process_steps = [
            ProcessStep(
                key="profile",
                label="读取学习画像",
                message=f"已加载 {len(weak_points)} 个薄弱点" if weak_points else "画像待通过对话建立",
                status="done",
            ),
            ProcessStep(
                key="behavior",
                label="汇总课堂投入",
                message=(
                    "已纳入近期课堂行为数据"
                    if classroom_behavior_summary
                    else "暂无课堂行为记录"
                ),
                status="done" if classroom_behavior_summary else "idle",
            ),
            ProcessStep(
                key="infer",
                label="生成诊断结论",
                message=payload.summary[:80] if payload.summary else "诊断完成",
                status="done",
            ),
        ]

        return LearningReport(
            learner_id=user_id,
            generated_at=datetime.utcnow().isoformat(),
            summary=payload.summary,
            current_goal=str(profile.get("current_goal") or "").strip(),
            learning_style=str(profile.get("learning_style") or "").strip(),
            risk_level=payload.risk_level,
            weak_points=weak_points,
            mastery_map=mastery_map,
            mastery_insights=self._mastery_insights({**profile, "mastery_map": mastery_map}),
            mastery_formula=str(mastery_update.get("formula") or ""),
            strengths=payload.strengths,
            recommended_actions=payload.recommended_actions,
            recommended_resources=payload.recommended_resources,
            follow_up_questions=payload.follow_up_questions,
            sections=sections,
            classroom_behavior_summary=classroom_behavior_summary,
            process_steps=process_steps,
            evidence_confidence=evidence_confidence,
            portrait_dimensions=portrait_dimensions,
            profile_schema_version=str(
                profile.get("profile_schema_version")
                or user_memory_profile_service.PROFILE_SCHEMA_VERSION
            ),
            dynamic_profile_dimensions=dynamic_profile_dimensions,
        )

    def build_report_and_sync_path(
        self, session: Session, user_id: str, *, refresh_profile: bool = False
    ) -> LearningReport:
        report = self.build_report(session, user_id, refresh_profile=refresh_profile)
        try:
            learning_path_service.upsert_from_report(session, user_id, report)
        except Exception:
            pass
        return report

    def build_review_plan(
        self, session: Session, user_id: str, *, refresh_profile: bool = False
    ) -> ReviewPlan:
        if refresh_profile:
            try:
                user_memory_profile_service.refresh_profile(user_id)
            except Exception:
                pass
        profile = user_memory_profile_service.get_profile_dict(session, user_id) or {}
        history = self._recent_history(session, user_id)
        digest = self._history_digest(history)
        
        # 教育学参数联动2：注入课堂认知特征
        behavior_context = self._get_behavior_for_review_plan(session, user_id)
        payload = self._infer_review_plan(
            profile=profile,
            history=history,
            history_digest=digest,
            behavior_context=behavior_context,
        )
        plan_days: list[ReviewPlanDay] = []
        for index, item in enumerate(payload.daily_plan[:3], start=1):
            if not isinstance(item, dict):
                continue
            plan_days.append(
                ReviewPlanDay(
                    day_label=str(item.get("day_label") or f"Day {index}"),
                    focus=str(item.get("focus") or "复习推进"),
                    tasks=[
                        str(task).strip()
                        for task in (item.get("tasks") or [])
                        if str(task).strip()
                    ][:4],
                )
            )
        if not plan_days:
            fallback = self._fallback_review_plan(profile, history)
            plan_days = [
                ReviewPlanDay(
                    day_label=str(item.get("day_label") or f"Day {idx + 1}"),
                    focus=str(item.get("focus") or "复习推进"),
                    tasks=[
                        str(task).strip()
                        for task in (item.get("tasks") or [])
                        if str(task).strip()
                    ][:4],
                )
                for idx, item in enumerate(fallback.daily_plan[:3])
            ]
            payload = fallback
        return ReviewPlan(
            learner_id=user_id,
            generated_at=datetime.utcnow().isoformat(),
            summary=payload.summary,
            focus_topics=[str(item).strip() for item in payload.focus_topics if str(item).strip()][:4],
            daily_plan=plan_days,
            checkpoints=[
                str(item).strip()
                for item in payload.checkpoints
                if str(item).strip()
            ][:4],
        )

    def build_mistake_digest(
        self, session: Session, user_id: str, *, refresh_profile: bool = False
    ) -> MistakeDigest:
        if refresh_profile:
            try:
                user_memory_profile_service.refresh_profile(user_id)
            except Exception:
                pass
        profile = user_memory_profile_service.get_profile_dict(session, user_id) or {}
        history = self._recent_history(session, user_id)
        digest = self._history_digest(history)
        topics = self._normalized_topics(profile, history)
        
        # 教育学参数联动7：注入注意力归因数据
        behavior_context = self._get_attention_context_for_mistakes(session, user_id, topics)
        payload = self._infer_mistake_digest(
            profile=profile,
            history=history,
            history_digest=digest,
            behavior_context=behavior_context,
        )
        items: list[MistakeDigestItem] = []
        for raw in payload.mistakes[:4]:
            if not isinstance(raw, dict):
                continue
            items.append(
                MistakeDigestItem(
                    title=str(raw.get("title") or "待复盘错点"),
                    symptom=str(raw.get("symptom") or ""),
                    evidence=str(raw.get("evidence") or ""),
                    fix_strategy=str(raw.get("fix_strategy") or ""),
                )
            )
        if not items:
            payload = self._fallback_mistake_digest(profile, history)
            items = [
                MistakeDigestItem(
                    title=str(raw.get("title") or "待复盘错点"),
                    symptom=str(raw.get("symptom") or ""),
                    evidence=str(raw.get("evidence") or ""),
                    fix_strategy=str(raw.get("fix_strategy") or ""),
                )
                for raw in payload.mistakes[:4]
                if isinstance(raw, dict)
            ]
        return MistakeDigest(
            learner_id=user_id,
            generated_at=datetime.utcnow().isoformat(),
            summary=payload.summary,
            mistakes=items,
            flashcards=[
                str(item).strip()
                for item in payload.flashcards
                if str(item).strip()
            ][:5],
        )


learning_report_service = LearningReportService()
