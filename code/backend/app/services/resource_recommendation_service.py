from __future__ import annotations

import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlmodel import Session, select

from app.core.config import settings
from app.models import (
    Course,
    ExternalResource,
    LearningEvidence,
    PersonalizedResourceRecommendation,
    PracticeRecord,
    Resource,
    UserMemoryProfile,
    UserResourceConfig,
)
from app.schemas.resource_generation import ResourceGenerationRequest
from app.schemas.knowledge_graph import KnowledgeGraphPayload
from app.schemas.resource_recommendation import (
    RecommendationActionResponse,
    RecommendationContentPreview,
    RecommendationItem,
    RecommendationPreviewResource,
    RecommendationPreviewResponse,
    ResourceRecommendationResponse,
)
from app.services.generated_knowledge_graph_service import knowledge_graph_service
from app.services.external_resource_discovery_service import (
    TOPIC_QUERY_ALIASES,
    external_resource_discovery_service,
)
from app.services.quiz_service import quiz_service
from app.services.resource_package_service import resource_package_service
from app.services.resource_subject_service import resolve_resource_subject
from app.services.recommendation_feedback_service import (
    dimension_signed_weights,
    feedback_idempotency_key,
    signed_weight,
)
from app.services.recommendation_ranking_service import (
    Candidate,
    RecommendationContext,
    RankedCandidate,
    lexical_similarity,
    mmr_order,
    rank_candidates,
)


MODALITY_SPECS: tuple[tuple[str, str, str], ...] = (
    ("document", "个性化讲解", "概念梳理、例子、常见误区与复习清单"),
    ("question", "专项练习", "分层单选题、答案解析与画像反馈"),
    ("knowledge_graph", "知识图谱", "核心概念、关系与薄弱节点可视化"),
    ("video", "视频讲解", "动画分镜、口播脚本与演示步骤"),
    ("code", "代码案例", "可运行案例、实验步骤与观察问题"),
    ("image", "图解卡片", "流程图、对比图与关键结论卡片"),
)

# A recommendation is a short follow-up activity, not a full exam. Six
# questions keep the two-stage generation/review request inside an interactive
# latency budget while still covering concept, mechanism and application.
RECOMMENDED_QUIZ_QUESTION_COUNT = 6


class ResourceRecommendationService:
    @classmethod
    def _record_resource_signal(
        cls,
        session: Session,
        *,
        user_id: UUID,
        item: PersonalizedResourceRecommendation,
        event_type: str,
    ) -> None:
        from app.services.learning_report_service import learning_report_service

        course_id = cls._resolve_course_id(
            session,
            subject=item.subject,
            topic=item.knowledge_point,
            resource_id=item.resource_id,
        )
        observed_at = datetime.now(timezone.utc)
        learning_report_service.record_evidence(
            session,
            user_id=user_id,
            course_id=course_id,
            knowledge_point=item.knowledge_point or item.title,
            source_type="resource_interaction",
            source_id=f"{item.id}:{event_type}",
            event_type=event_type,
            weight=0.2,
            score=None,
            observed_at=observed_at,
            idempotency_key=feedback_idempotency_key(str(item.id), event_type, observed_at),
            payload={
                "recommendation_id": str(item.id),
                "resource_id": str(item.resource_id) if item.resource_id else None,
                "resource_type": item.type,
                "subject": item.subject,
                "origin": item.origin,
                "topic": item.knowledge_point,
                "signed_preference_weight": signed_weight(event_type),
                "dimension_preference_weights": dimension_signed_weights(event_type),
                "course_id": str(course_id) if course_id else None,
            },
        )

    @classmethod
    def _resolve_course_id(
        cls,
        session: Session,
        *,
        subject: str | None,
        topic: str | None,
        resource_id: UUID | None = None,
    ) -> UUID | None:
        """Resolve a recommendation to one real course without guessing.

        An already materialized resource is authoritative. Otherwise, an exact
        normalized course-name match wins; a substring match is accepted only
        when it identifies exactly one course. Ambiguous or weak matches remain
        unscoped so evidence is never attributed to the wrong course.
        """
        if resource_id:
            resource = session.get(Resource, resource_id)
            if resource and resource.course_id:
                return resource.course_id

        signals = cls._unique(
            [
                cls._normalize_course_text(subject),
                cls._normalize_course_text(topic),
            ]
        )
        signals = [
            value
            for value in signals
            if len(value) >= 3
            and value not in {"未分类", "通用学习", "个性化学习", "当前学习目标"}
        ]
        if not signals:
            return None

        courses = list(session.exec(select(Course)).all())
        normalized_courses = [
            (course, cls._normalize_course_text(course.name)) for course in courses
        ]
        exact = {
            course.id
            for course, course_name in normalized_courses
            if course_name and course_name in signals
        }
        if len(exact) == 1:
            return next(iter(exact))
        if len(exact) > 1:
            return None

        contained = {
            course.id
            for course, course_name in normalized_courses
            if course_name
            and any(signal in course_name or course_name in signal for signal in signals)
        }
        return next(iter(contained)) if len(contained) == 1 else None

    @staticmethod
    def _normalize_course_text(value: object) -> str:
        normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
        return "".join(character for character in normalized if character.isalnum())

    def recommend(
        self,
        session: Session,
        *,
        user_id: UUID,
        limit: int = 8,
        refresh: bool = False,
    ) -> ResourceRecommendationResponse:
        profile, weak_points, goals, learning_style, signals = self._profile_context(
            session, user_id=user_id
        )
        if refresh:
            current = session.exec(
                select(PersonalizedResourceRecommendation).where(
                    PersonalizedResourceRecommendation.user_id == user_id,
                    PersonalizedResourceRecommendation.status == "active",
                )
            ).all()
            for item in current:
                # A favorite is an explicit "keep this" decision. Changing the
                # surrounding batch must not silently throw it away.
                if item.favorite:
                    continue
                item.status = "dismissed"
                item.updated_time = datetime.now(timezone.utc)
                session.add(item)
            session.commit()

        active = session.exec(
            select(PersonalizedResourceRecommendation).where(
                PersonalizedResourceRecommendation.user_id == user_id,
                PersonalizedResourceRecommendation.status == "active",
            )
        ).all()
        if len(active) < limit:
            self._create_profile_candidates(
                session,
                user_id=user_id,
                weak_points=weak_points,
                goals=goals,
                learning_style=learning_style,
            )
            self._create_external_candidates(
                session,
                user_id=user_id,
                topics=weak_points or goals or ["当前学习目标"],
                # Normal page loads rank the durable catalog only. Network
                # discovery is an explicit refresh action, never a cold-start
                # request that blocks a student's first visit.
                allow_discovery=refresh,
            )
            active = session.exec(
                select(PersonalizedResourceRecommendation).where(
                    PersonalizedResourceRecommendation.user_id == user_id,
                    PersonalizedResourceRecommendation.status == "active",
                )
            ).all()

        items = self._rank_public_items(session, user_id=user_id, items=active, limit=limit)
        return ResourceRecommendationResponse(
            generated_at=datetime.now(timezone.utc),
            profile_signals=self._unique(signals)[:8],
            agent_trace=["学习画像分析", "资料匹配", "学习形式规划"],
            items=items[:limit],
        )

    def preview(
        self, session: Session, *, user_id: UUID, recommendation_id: UUID
    ) -> RecommendationPreviewResponse:
        """Prepare an owner-only recommendation preview.

        A non-materialized generated recommendation gets an immediate local
        outline.  This deliberately does *not* call a model, quiz generator or
        package generator: full content is created only after the student adds
        it to the library.  External recommendations remain metadata-only.
        """
        item = self._owned(session, user_id=user_id, recommendation_id=recommendation_id)
        self._record_resource_signal(
            session, user_id=user_id, item=item, event_type="recommendation_previewed"
        )
        session.commit()
        if item.origin == "external":
            return RecommendationPreviewResponse(
                recommendation=self._public_current(session, user_id=user_id, item=item),
                message=(
                    "可在新窗口阅读原文。"
                    if self._safe_external_url(item.url)
                    else "来源暂不可用，请换一条推荐或稍后重试。"
                ),
            )

        resource = self._owned_materialized_resource(session, item=item, user_id=user_id)
        if resource is None:
            return RecommendationPreviewResponse(
                recommendation=self._public_current(session, user_id=user_id, item=item),
                content_preview=self._instant_content_preview(item),
                message="先查看围绕该主题安排的学习重点、示例和自测方向。",
            )

        return RecommendationPreviewResponse(
            recommendation=self._public_current(session, user_id=user_id, item=item),
            resource=self._preview_resource(resource),
            message=(
                "练习已准备好，可开始作答。"
                if item.type == "question"
                else "这份个性化资料可直接预览和学习。"
            ),
        )

    @staticmethod
    def _instant_content_preview(
        item: PersonalizedResourceRecommendation,
    ) -> RecommendationContentPreview:
        """Build a truthful type-specific outline solely from recommendation metadata."""
        subject = item.subject or "通用学习"
        topic = item.knowledge_point or item.title or "当前学习目标"
        difficulty = item.difficulty or "standard"
        reason = item.reason or f"围绕{topic}安排一次针对性学习"
        common = {"type": item.type, "subject": subject, "topic": topic, "difficulty": difficulty, "reason": reason}
        if item.type == "question":
            sections = [
                {"kind": "sample_question", "title": "练习样题", "prompt": f"在{subject}中，{topic}最需要先澄清的核心概念是什么？", "options": ["定义与适用条件", "无关的术语罗列", "跳过前提直接套结论", "只记住结论名称"]},
                {"kind": "plan", "title": "学习内容包含", "points": ["基础概念辨析", "机制或步骤判断", "情境应用与解析"]},
            ]
        elif item.type in {"knowledge_graph", "image"}:
            sections = [
                {"kind": "graph", "title": "图谱骨架", "nodes": [topic, "关键概念", "应用场景"], "edges": [{"source": topic, "target": "关键概念", "label": "拆解"}, {"source": "关键概念", "target": "应用场景", "label": "迁移"}]},
                {"kind": "plan", "title": "学习内容包含", "points": ["前置与后续知识", "易混淆关系", "待复习节点"]},
            ]
        elif item.type == "video":
            sections = [
                {"kind": "storyboard", "title": "视频分镜", "points": [f"00:00 提出 {topic} 的学习问题", "00:45 分解核心概念与条件", "02:00 用小例子演示应用", "03:30 总结易错点与复习动作"]},
                {"kind": "plan", "title": "学习内容包含", "points": ["口播脚本", "演示步骤", "课后自测提示"]},
            ]
        elif item.type == "code":
            sections = [
                {"kind": "code_task", "title": "代码任务", "task": f"为 {topic} 写一个最小可运行示例，并记录输入、关键步骤和输出。", "points": ["明确接口或数据结构", "实现可观察的核心过程", "用一组边界样例验证"]},
                {"kind": "plan", "title": "学习内容包含", "points": ["项目骨架", "实验步骤", "结果观察问题"]},
            ]
        else:
            sections = [
                {"kind": "outline", "title": "讲解提纲", "points": [f"{topic} 的定义与适用范围", "关键机制或步骤", "一个可检查的小例子", "常见误区与复习清单"]},
                {"kind": "plan", "title": "学习内容包含", "points": ["完整讲解内容", "针对难度的例题", "可保存的复习清单"]},
            ]
        return RecommendationContentPreview(
            **common,
            sections=sections,
            note="内容围绕推荐的学科、主题和难度组织，便于先判断学习重点与练习方向。",
        )

    def dismiss(self, session: Session, *, user_id: UUID, recommendation_id: UUID) -> None:
        item = self._owned(session, user_id=user_id, recommendation_id=recommendation_id)
        item.status = "dismissed"
        item.updated_time = datetime.now(timezone.utc)
        session.add(item)
        self._record_resource_signal(
            session, user_id=user_id, item=item, event_type="recommendation_dismissed"
        )
        session.commit()

    def favorite(
        self,
        session: Session,
        *,
        user_id: UUID,
        recommendation_id: UUID,
        favorite: bool,
    ) -> RecommendationItem:
        item = self._owned(session, user_id=user_id, recommendation_id=recommendation_id)
        item.favorite = favorite
        item.updated_time = datetime.now(timezone.utc)
        session.add(item)
        self._record_resource_signal(
            session,
            user_id=user_id,
            item=item,
            event_type="resource_favorited" if favorite else "resource_unfavorited",
        )
        session.commit()
        session.refresh(item)
        return self._public_current(session, user_id=user_id, item=item)

    def record_explicit_feedback(
        self, session: Session, *, user_id: UUID, recommendation_id: UUID, action: str
    ) -> RecommendationItem:
        """Record the one client-only action after owner and URL validation."""
        if action != "source_opened":
            raise ValueError("不支持的推荐反馈动作")
        item = self._owned(session, user_id=user_id, recommendation_id=recommendation_id)
        if item.origin != "external" or not self._safe_external_url(item.url):
            raise ValueError("该推荐没有可安全打开的外部来源")
        self._record_resource_signal(session, user_id=user_id, item=item, event_type=action)
        session.commit()
        return self._public_current(session, user_id=user_id, item=item)

    def regenerate(
        self, session: Session, *, user_id: UUID, recommendation_id: UUID
    ) -> RecommendationActionResponse:
        item = self._owned(session, user_id=user_id, recommendation_id=recommendation_id)
        if item.origin == "external":
            replacement = self._next_external(session, item=item, user_id=user_id)
            if replacement:
                item.title = replacement.title
                item.url = replacement.url
                item.source = replacement.source
                item.type = replacement.type
                item.subject = replacement.subject
                item.external_resource_id = replacement.id
            item.generation += 1
            item.reason = f"根据你的“{item.knowledge_point}”学习信号更新的公开来源资料。"
            item.updated_time = datetime.now(timezone.utc)
            session.add(item)
            self._record_resource_signal(
                session,
                user_id=user_id,
                item=item,
                event_type="external_resource_regenerated",
            )
            session.commit()
            session.refresh(item)
            return RecommendationActionResponse(
                recommendation=self._public_current(session, user_id=user_id, item=item),
                message="已更新公开来源推荐",
            )

        resource_id = self._materialize_generated(session, item=item, user_id=user_id, hidden=True)
        item.resource_id = resource_id
        item.generation += 1
        item.content_spec = {
            **(item.content_spec or {}),
            "variant": item.generation,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        item.reason = f"已根据最新个人画像重新生成第 {item.generation} 版，可预览后加入资料库。"
        item.updated_time = datetime.now(timezone.utc)
        session.add(item)
        self._record_resource_signal(
            session,
            user_id=user_id,
            item=item,
            event_type="generated_resource_regenerated",
        )
        session.commit()
        session.refresh(item)
        return RecommendationActionResponse(
            recommendation=self._public_current(session, user_id=user_id, item=item),
            resource_id=resource_id,
            message="已按最新个人画像重新生成",
        )

    def add_to_library(
        self, session: Session, *, user_id: UUID, recommendation_id: UUID
    ) -> RecommendationActionResponse:
        item = self._owned(session, user_id=user_id, recommendation_id=recommendation_id)
        course_id = self._resolve_course_id(
            session,
            subject=item.subject,
            topic=item.knowledge_point,
            resource_id=item.resource_id,
        )
        if item.origin == "external":
            safe_url = self._safe_external_url(item.url)
            if not safe_url:
                raise ValueError("外部来源暂不可用，无法加入资料库")
            external = (
                session.get(ExternalResource, item.external_resource_id)
                if item.external_resource_id
                else None
            )
            resource = Resource(
                title=item.title,
                type="external",
                subject=item.subject,
                content_type="text/uri-list",
                url=safe_url,
                knowledge_point=item.knowledge_point,
                difficulty=item.difficulty,
                source=item.source,
                uploader_id=user_id,
                course_id=course_id,
                content={
                    "recommendation_id": str(item.id),
                    "external": True,
                    "source_metadata": self._external_source_metadata(external),
                },
            )
            session.add(resource)
            session.flush([resource])
            resource_id = resource.id
        else:
            resource_id = item.resource_id or self._materialize_generated(
                session, item=item, user_id=user_id, hidden=False
            )
            existing_resource = session.get(Resource, resource_id)
            if existing_resource and existing_resource.course_id is None and course_id:
                existing_resource.course_id = course_id
                session.add(existing_resource)
        config = session.exec(
            select(UserResourceConfig).where(
                UserResourceConfig.user_id == user_id,
                UserResourceConfig.resource_id == resource_id,
            )
        ).first()
        if config:
            config.is_hidden = False
            config.updated_time = datetime.now(timezone.utc)
            session.add(config)
        item.resource_id = resource_id
        item.status = "added"
        item.updated_time = datetime.now(timezone.utc)
        session.add(item)
        self._record_resource_signal(
            session, user_id=user_id, item=item, event_type="resource_added_to_library"
        )
        session.commit()
        session.refresh(item)
        return RecommendationActionResponse(
            recommendation=self._public_current(session, user_id=user_id, item=item),
            resource_id=resource_id,
            message="已加入我的资料库",
        )

    def _create_profile_candidates(
        self,
        session: Session,
        *,
        user_id: UUID,
        weak_points: list[str],
        goals: list[str],
        learning_style: str,
    ) -> list[PersonalizedResourceRecommendation]:
        topics = self._unique(weak_points + goals) or ["当前学习目标"]
        blocked_pairs = self._blocked_profile_pairs(session, user_id=user_id)
        history_count = len(session.exec(
            select(PersonalizedResourceRecommendation.id).where(
                PersonalizedResourceRecommendation.user_id == user_id,
                PersonalizedResourceRecommendation.origin == "generated",
            )
        ).all())
        rotation = (history_count // max(1, len(MODALITY_SPECS))) % len(topics)
        rows: list[PersonalizedResourceRecommendation] = []
        for index, (resource_type, label, preview) in enumerate(MODALITY_SPECS):
            topic = ""
            for offset in range(len(topics)):
                proposed = topics[(index + rotation + offset) % len(topics)]
                fingerprint = (resource_type, self._normalize_course_text(proposed))
                if fingerprint not in blocked_pairs:
                    topic = proposed
                    blocked_pairs.add(fingerprint)
                    break
            if not topic:
                # Every topic for this modality is explicitly unavailable or
                # already kept as a favorite; do not immediately repeat it.
                continue
            evidence = [f"匹配画像知识点：{topic}", f"多模态类型：{label}"]
            if learning_style:
                evidence.append(f"学习偏好：{learning_style}")
            row = PersonalizedResourceRecommendation(
                user_id=user_id,
                origin="generated",
                title=f"{topic} · {label}",
                type=resource_type,
                subject=resolve_resource_subject(None, topic, *goals),
                knowledge_point=topic,
                difficulty="foundation" if index in {0, 3, 5} else "standard",
                source="智屿个性化生成",
                reason=f"根据你的个人画像，为“{topic}”安排{label}，围绕概念辨析、示例和自测展开。",
                evidence=evidence,
                content_spec={
                    "preview": preview,
                    "learning_style": learning_style,
                    "profile_topic": topic,
                    "modality": resource_type,
                },
            )
            session.add(row)
            rows.append(row)
        session.commit()
        for row in rows:
            session.refresh(row)
        return rows

    def _blocked_profile_pairs(
        self, session: Session, *, user_id: UUID
    ) -> set[tuple[str, str]]:
        """Pairs kept as favorites or explicitly dismissed in the last 30 days."""
        blocked: set[tuple[str, str]] = set()
        kept = session.exec(
            select(PersonalizedResourceRecommendation).where(
                PersonalizedResourceRecommendation.user_id == user_id,
                PersonalizedResourceRecommendation.status == "active",
                PersonalizedResourceRecommendation.favorite.is_(True),
            )
        ).all()
        for item in kept:
            blocked.add((item.type, self._normalize_course_text(item.knowledge_point)))

        dismissed = session.exec(
            select(LearningEvidence).where(
                LearningEvidence.user_id == user_id,
                LearningEvidence.event_type == "recommendation_dismissed",
                LearningEvidence.observed_at >= datetime.now(timezone.utc) - timedelta(days=30),
            )
        ).all()
        for event in dismissed:
            payload = event.payload if isinstance(event.payload, dict) else {}
            resource_type = str(payload.get("resource_type") or "").strip()
            topic = self._normalize_course_text(payload.get("topic"))
            if resource_type and topic:
                blocked.add((resource_type, topic))
        return blocked

    def _create_external_candidates(
        self,
        session: Session,
        *,
        user_id: UUID,
        topics: list[str],
        allow_discovery: bool,
    ) -> None:
        externals = list(session.exec(select(ExternalResource)).all())
        # A deliberate refresh may fill only missing or stale topic coverage.
        # Default page loads stay entirely DB-backed.
        if allow_discovery:
            fresh_after = datetime.now(timezone.utc) - timedelta(
                hours=settings.EXTERNAL_DISCOVERY_STALE_HOURS
            )
            for topic in self._unique(topics)[: max(1, min(3, settings.EXTERNAL_DISCOVERY_MAX_TOPICS))]:
                matching = [
                    row for row in externals
                    if lexical_similarity(topic, f"{row.knowledge_point} {row.title}") >= 0.16
                ]
                # A single fresh paper must not suppress the book/video
                # catalogs for the whole topic.  Refresh only skips network
                # discovery when all fixed catalogs already have recent rows.
                fresh_providers = {
                    row.provider
                    for row in matching
                    if row.discovered_at and row.discovered_at >= fresh_after
                }
                if {"open_library", "openalex", "internet_archive"} <= fresh_providers:
                    continue
                discovered = self._discover_external(session, topic=topic)
                externals.extend(discovered)
        seen_urls: set[str] = set()
        external_rows: list[tuple[ExternalResource, str]] = []
        for external in externals:
            # Shared legacy/manual records have no reviewed catalog provenance.
            # They remain useful to the student who saved them, but must not
            # appear in another student's automatic recommendation batch.
            if external.provider == "manual" and external.created_by != user_id:
                continue
            safe_url = self._safe_external_url(external.url)
            if not safe_url or safe_url in seen_urls:
                continue
            seen_urls.add(safe_url)
            external_rows.append((external, safe_url))
        # Use the full profile context here rather than a new minimal context.
        # Besides recent practice and feedback, this carries the reviewed
        # Chinese-to-catalog aliases needed to judge an English catalog title
        # against the original (Chinese) learning signal.  Without it, a
        # successful Open Library/OpenAlex lookup could be dropped by the
        # relevance gate before the student ever sees it.
        context = self._recommendation_context(session, user_id=user_id)
        if not context.query_topics:
            aliases = {
                topic: TOPIC_QUERY_ALIASES[self._normalize_course_text(topic)]
                for topic in topics
                if self._normalize_course_text(topic) in TOPIC_QUERY_ALIASES
            }
            context = RecommendationContext(
                weak_points=topics,
                external_topic_aliases=aliases,
            )
        candidates = [
            Candidate(
                title=external.title, subject=external.subject, source=external.source,
                knowledge_point=external.knowledge_point, modality=external.type,
                difficulty=external.difficulty, origin="external",
                trusted_catalog_context=self._trusted_catalog_context(external),
            )
            for external, _ in external_rows
        ]
        ranked = rank_candidates(candidates, context)
        eligible = [index for index, detail in enumerate(ranked) if detail.external_relevant]
        ordered = mmr_order(
            [candidates[index] for index in eligible],
            [ranked[index] for index in eligible],
            limit=min(6, len(eligible)),
        )
        for relative_index in ordered:
            index = eligible[relative_index]
            external, safe_url = external_rows[index]
            detail = ranked[index]
            session.add(
                PersonalizedResourceRecommendation(
                    user_id=user_id,
                    origin="external",
                    title=external.title,
                    type=external.type,
                    subject=external.subject,
                    knowledge_point=external.knowledge_point,
                    difficulty=external.difficulty,
                    source=external.source,
                    url=safe_url,
                    reason=self._external_reason(detail.reason, external),
                    evidence=detail.evidence + [f"公开来源：{external.source}"],
                    content_spec={"preview": "打开公开来源查看完整内容", "external": True},
                    external_resource_id=external.id,
                )
            )
        session.commit()

    def _discover_external(self, session: Session, *, topic: str) -> list[ExternalResource]:
        """Persist bounded metadata from the three fixed public catalogs."""
        topic = self._clean_query_topic(topic)
        if not topic:
            return []
        return external_resource_discovery_service.persist(
            session,
            topic=topic,
            candidates=external_resource_discovery_service.discover(topic=topic),
        )

    @staticmethod
    def _clean_query_topic(value: object) -> str:
        text = " ".join(str(value or "").split())[:80]
        # A query must contain a genuine word/Chinese character rather than a
        # concatenated URL/prompt fragment.
        if len(text) < 2 or not any(character.isalnum() for character in text):
            return ""
        return text

    @staticmethod
    def _clean_external_title(value: object) -> str:
        title = " ".join(str(value or "").split())[:180]
        if len(title) < 2 or title.count("http") > 0:
            return ""
        return title

    def _materialize_generated(
        self,
        session: Session,
        *,
        item: PersonalizedResourceRecommendation,
        user_id: UUID,
        hidden: bool,
    ) -> UUID:
        topic = item.knowledge_point or "当前学习目标"
        subject = resolve_resource_subject(item.subject, topic, item.title)
        course_id = self._resolve_course_id(
            session,
            subject=subject,
            topic=topic,
            resource_id=item.resource_id,
        )
        if item.type == "question":
            output = quiz_service.generate(
                session,
                owner_id=user_id,
                course=subject,
                knowledge_point=topic,
                count=RECOMMENDED_QUIZ_QUESTION_COUNT,
                difficulty=item.difficulty,
                course_id=course_id,
            )
            resource_id = output.resource_id
        elif item.type == "knowledge_graph":
            output = knowledge_graph_service.generate(
                session,
                owner_id=user_id,
                course=subject,
                knowledge_point=topic,
                course_id=course_id,
            )
            resource_id = UUID(str(output.resource_id))
        else:
            kind_map = {
                "document": "lecture_markdown",
                "video": "video_script",
                "code": "case_project",
                "image": "mind_map",
            }
            kind = kind_map.get(item.type, "lecture_markdown")
            output = resource_package_service.generate(
                session,
                ResourceGenerationRequest(
                    course_id=course_id,
                    node_label=topic,
                    subject=subject,
                    topic=topic,
                    learning_goal=item.reason,
                    difficulty=item.difficulty,
                    target_minutes=30,
                    resource_types=[kind],
                    source="profile-recommendation",
                ),
                owner_id=user_id,
            )
            if not output.persisted_resource_ids:
                raise RuntimeError("个性化资源生成后未能入库")
            resource_id = output.persisted_resource_ids[0]
        config = session.exec(
            select(UserResourceConfig).where(
                UserResourceConfig.user_id == user_id,
                UserResourceConfig.resource_id == resource_id,
            )
        ).first() or UserResourceConfig(user_id=user_id, resource_id=resource_id)
        config.is_hidden = hidden
        config.updated_time = datetime.now(timezone.utc)
        session.add(config)
        session.commit()
        return resource_id

    def _next_external(
        self,
        session: Session,
        *,
        item: PersonalizedResourceRecommendation,
        user_id: UUID,
    ) -> ExternalResource | None:
        used = set(session.exec(
            select(PersonalizedResourceRecommendation.external_resource_id).where(
                PersonalizedResourceRecommendation.user_id == user_id,
                PersonalizedResourceRecommendation.external_resource_id.is_not(None),
            )
        ).all())
        candidates = session.exec(
            select(ExternalResource).where(ExternalResource.id.not_in(used))
        ).all()
        context = self._recommendation_context(session, user_id=user_id)
        candidate_rows = [
            row
            for row in candidates
            if self._safe_external_url(row.url)
            and (row.provider != "manual" or row.created_by == user_id)
        ]
        candidate_models = [
            Candidate(
                row.title, row.subject, row.source, row.knowledge_point,
                row.type, row.difficulty, "external",
                self._trusted_catalog_context(row),
            )
            for row in candidate_rows
        ]
        ranked = rank_candidates(candidate_models, context)
        eligible = [
            (row, detail)
            for row, detail in zip(candidate_rows, ranked, strict=True)
            if detail.external_relevant
        ]
        matched = max(eligible, key=lambda pair: pair[1].score)[0] if eligible else None
        if matched:
            return matched
        discovered = self._discover_external(session, topic=item.knowledge_point)
        safe_discovered = [row for row in discovered if self._safe_external_url(row.url)]
        discovered_models = [
            Candidate(
                row.title, row.subject, row.source, row.knowledge_point,
                row.type, row.difficulty, "external",
                self._trusted_catalog_context(row),
            )
            for row in safe_discovered
        ]
        discovered_ranked = rank_candidates(discovered_models, context)
        discovered_eligible = [
            (row, detail)
            for row, detail in zip(safe_discovered, discovered_ranked, strict=True)
            if detail.external_relevant
        ]
        return max(discovered_eligible, key=lambda pair: pair[1].score)[0] if discovered_eligible else None

    def _owned(
        self, session: Session, *, user_id: UUID, recommendation_id: UUID
    ) -> PersonalizedResourceRecommendation:
        item = session.get(PersonalizedResourceRecommendation, recommendation_id)
        if not item or item.user_id != user_id or item.status == "dismissed":
            raise LookupError("未找到指定推荐")
        return item

    def _candidate(
        self, session: Session, item: PersonalizedResourceRecommendation
    ) -> Candidate:
        external = (
            session.get(ExternalResource, item.external_resource_id)
            if item.origin == "external" and item.external_resource_id
            else None
        )
        return Candidate(
            title=item.title, subject=item.subject, source=item.source,
            knowledge_point=item.knowledge_point, modality=item.type,
            difficulty=item.difficulty, origin=item.origin,
            trusted_catalog_context=(
                self._trusted_catalog_context(external) if external else ""
            ),
        )

    def _rank_public_items(
        self, session: Session, *, user_id: UUID,
        items: list[PersonalizedResourceRecommendation], limit: int,
    ) -> list[RecommendationItem]:
        context = self._recommendation_context(session, user_id=user_id)
        candidates = [self._candidate(session, item) for item in items]
        ranked = rank_candidates(candidates, context)
        eligible = [
            index for index, (item, detail) in enumerate(zip(items, ranked, strict=True))
            if item.origin != "external" or detail.external_relevant
        ]
        # Favorites receive only a bounded relevance prior before MMR; do not
        # sort afterward or that would erase diversity and bypass the gate.
        mmr_ranked = [
            RankedCandidate(
                score=round(min(0.99, ranked[index].score + (0.05 if items[index].favorite else 0.0)), 4),
                evidence=ranked[index].evidence,
                reason=ranked[index].reason,
                external_relevant=ranked[index].external_relevant,
            )
            for index in eligible
        ]
        ordered_relative = mmr_order(
            [candidates[index] for index in eligible],
            mmr_ranked,
            limit=len(eligible),
        )
        ordered = [eligible[index] for index in ordered_relative]
        selected = ordered[:limit]
        # A six-card student batch deliberately combines catalog discovery
        # with first-party personalized study materials.  Keep public sources
        # to at most half the batch (and include up to three when available),
        # so a strong catalog response cannot crowd out practice, explanation
        # and other learning actions generated for this learner.
        desired_external = min(
            limit // 2,
            sum(items[index].origin == "external" for index in ordered),
        )
        current_external = sum(items[index].origin == "external" for index in selected)
        changed_composition = False
        if current_external > desired_external:
            generated_replacements = [
                index for index in ordered[limit:]
                if items[index].origin != "external"
            ]
            for replacement in generated_replacements:
                removable = next(
                    (
                        position for position in range(len(selected) - 1, -1, -1)
                        if items[selected[position]].origin == "external"
                        and not items[selected[position]].favorite
                    ),
                    None,
                )
                if removable is None:
                    break
                selected[removable] = replacement
                current_external -= 1
                changed_composition = True
                if current_external <= desired_external:
                    break
        if current_external < desired_external:
            replacements = [
                index for index in ordered[limit:]
                if items[index].origin == "external"
            ]
            for replacement in replacements:
                removable = next(
                    (
                        position for position in range(len(selected) - 1, -1, -1)
                        if items[selected[position]].origin != "external"
                        and not items[selected[position]].favorite
                    ),
                    None,
                )
                if removable is None:
                    break
                selected[removable] = replacement
                current_external += 1
                changed_composition = True
                if current_external >= desired_external:
                    break
        # When the catalog offers several relevant formats, avoid spending all
        # public slots on near-duplicate papers or videos.  This replacement
        # runs only after relevance gating and only removes an unfavorited
        # duplicate, so it cannot override an explicit learner choice.
        available_external_kinds = {
            items[index].type
            for index in ordered
            if items[index].origin == "external"
        }
        target_kind_count = min(desired_external, len(available_external_kinds))
        selected_external_kinds = {
            items[index].type
            for index in selected
            if items[index].origin == "external"
        }
        if len(selected_external_kinds) < target_kind_count:
            for replacement in ordered:
                if (
                    items[replacement].origin != "external"
                    or items[replacement].type in selected_external_kinds
                    or replacement in selected
                ):
                    continue
                removable = next(
                    (
                        position
                        for position in range(len(selected) - 1, -1, -1)
                        if items[selected[position]].origin == "external"
                        and not items[selected[position]].favorite
                        and sum(
                            1
                            for selected_index in selected
                            if items[selected_index].origin == "external"
                            and items[selected_index].type == items[selected[position]].type
                        ) > 1
                    ),
                    None,
                )
                if removable is None:
                    break
                selected[removable] = replacement
                selected_external_kinds = {
                    items[index].type
                    for index in selected
                    if items[index].origin == "external"
                }
                changed_composition = True
                if len(selected_external_kinds) >= target_kind_count:
                    break
        if changed_composition:
            # Restore MMR ordering after the constrained composition step;
            # relevance stays the primary score and the external gate above
            # ensures only topic-matching catalog items enter this branch.
            selected_relative = mmr_order(
                [candidates[index] for index in selected],
                [ranked[index] for index in selected],
                limit=len(selected),
            )
            selected = [selected[index] for index in selected_relative]
        return [self._public(session, items[index], ranked[index]) for index in selected]

    def _public_current(
        self, session: Session, *, user_id: UUID, item: PersonalizedResourceRecommendation
    ) -> RecommendationItem:
        active = list(session.exec(select(PersonalizedResourceRecommendation).where(
            PersonalizedResourceRecommendation.user_id == user_id,
            PersonalizedResourceRecommendation.status != "dismissed",
        )).all())
        if item.id not in {row.id for row in active}:
            active.append(item)
        public_items = self._rank_public_items(session, user_id=user_id, items=active, limit=len(active))
        return next((row for row in public_items if row.id == str(item.id)), self._public(session, item, None))

    def _public(
        self, session: Session, item: PersonalizedResourceRecommendation, detail: Any | None
    ) -> RecommendationItem:
        resource_payload = None
        if item.resource_id:
            resource_payload = {"id": str(item.resource_id), "type": item.type}
        safe_url = self._safe_external_url(item.url) if item.origin == "external" else None
        source_domain = self._external_domain(safe_url) if safe_url else None
        source = (
            "智屿个性化生成"
            if item.origin == "generated"
            else self._external_source_name(item.source, source_domain)
            if safe_url
            else "来源暂不可用"
        )
        external = (
            session.get(ExternalResource, item.external_resource_id)
            if item.origin == "external" and item.external_resource_id
            else None
        )
        return RecommendationItem(
            id=str(item.id),
            origin=item.origin,  # type: ignore[arg-type]
            title=item.title,
            type=item.type,
            subject=item.subject,
            knowledge_point=item.knowledge_point,
            difficulty=item.difficulty,
            source=source,
            source_domain=source_domain,
            url=safe_url,
            reason=detail.reason if detail else item.reason,
            evidence=detail.evidence if detail else item.evidence,
            preview=str((item.content_spec or {}).get("preview") or ""),
            favorite=item.favorite,
            status=item.status,
            generation=item.generation,
            resource=resource_payload,
            source_metadata=self._external_source_metadata(external),
        )

    @staticmethod
    def _external_source_metadata(external: ExternalResource | None) -> dict[str, Any]:
        if not external:
            return {}
        safe_cover = ResourceRecommendationService._safe_external_url(external.cover_url)
        catalog: dict[str, Any] = {}
        if isinstance(external.source_metadata, dict):
            for key, value in list(external.source_metadata.items())[:8]:
                clean_key = str(key)[:80]
                if not clean_key:
                    continue
                if clean_key.endswith(("url", "_url")):
                    catalog[clean_key] = ResourceRecommendationService._safe_external_url(
                        str(value or "")
                    )
                elif isinstance(value, (bool, int, float)) or value is None:
                    catalog[clean_key] = value
                elif isinstance(value, list):
                    catalog[clean_key] = [str(item)[:200] for item in value[:8]]
                else:
                    catalog[clean_key] = " ".join(str(value or "").split())[:300]
        return {
            "provider": str(external.provider or "manual")[:40],
            "provider_name": str(external.source or "开放学习来源")[:80],
            "kind": str(external.provider_kind or external.type)[:32],
            "summary": str(external.summary or "")[:1200],
            "authors": [str(value)[:160] for value in (external.authors or [])[:8]],
            "year": external.published_year,
            "language": str(external.language or "")[:32] or None,
            "license_status": str(external.license_status or "")[:160] or None,
            "cover_url": safe_cover,
            "canonical_url": ResourceRecommendationService._safe_external_url(external.url),
            "discovered_at": external.discovered_at.isoformat() if external.discovered_at else None,
            "verified_at": external.verified_at.isoformat() if external.verified_at else None,
            "catalog": catalog,
        }

    @staticmethod
    def _trusted_catalog_context(external: ExternalResource) -> str:
        """Return only server-generated context from the fixed source set."""
        if external.provider not in {"open_library", "openalex", "internet_archive"}:
            return ""
        metadata = external.source_metadata if isinstance(external.source_metadata, dict) else {}
        parts = [external.knowledge_point]
        for name in ("query_alias", "video_query_alias"):
            value = metadata.get(name)
            if isinstance(value, str):
                parts.append(value)
        return " ".join(" ".join(str(value or "").split())[:160] for value in parts if value)[:480]

    @staticmethod
    def _external_reason(base_reason: str, external: ExternalResource) -> str:
        topic = external.knowledge_point or "当前学习主题"
        format_label = {"book": "图书", "paper": "开放获取论文", "video": "视频讲座"}.get(
            external.provider_kind or external.type, "公开资料"
        )
        signal = str(base_reason or "").rstrip("。")
        if signal and "当前可用学习信息" not in signal:
            return f"{signal}；“{external.title}”是一份{format_label}，可用于围绕“{topic}”继续学习。"
        return f"你的学习画像关联“{topic}”；“{external.title}”是一份{format_label}，可补充该主题的阅读或观看。"

    @staticmethod
    def _safe_external_url(value: str | None) -> str | None:
        try:
            parsed = urlparse(str(value or "").strip())
        except (TypeError, ValueError):
            return None
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            return None
        return parsed.geturl()

    @staticmethod
    def _external_domain(url: str) -> str:
        return (urlparse(url).hostname or "").removeprefix("www.")[:255]

    @staticmethod
    def _external_source_name(source: str | None, domain: str) -> str:
        candidate = str(source or "").strip()
        return candidate[:80] if candidate else domain

    @staticmethod
    def _preview_resource(resource: Resource) -> RecommendationPreviewResource:
        return RecommendationPreviewResource(
            id=resource.id,
            title=resource.title,
            type=resource.type,
            file_name=resource.file_name,
            file_size=resource.file_size,
            content_type=resource.content_type,
            knowledge_point=resource.knowledge_point,
            difficulty=resource.difficulty,
            content=(
                ResourceRecommendationService._safe_knowledge_graph_content(resource.content)
                if resource.type == "knowledge_graph"
                else None
            ),
        )

    @staticmethod
    def _safe_knowledge_graph_content(
        content: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if not isinstance(content, dict):
            return None
        try:
            payload = KnowledgeGraphPayload.model_validate(
                {"nodes": content.get("nodes"), "edges": content.get("edges")}
            )
        except (TypeError, ValueError):
            return None
        return payload.model_dump()

    @staticmethod
    def _owned_materialized_resource(
        session: Session,
        *,
        item: PersonalizedResourceRecommendation,
        user_id: UUID,
    ) -> Resource | None:
        if not item.resource_id:
            return None
        resource = session.get(Resource, item.resource_id)
        if resource and resource.uploader_id == user_id:
            return resource
        return None

    def _profile_context(
        self, session: Session, *, user_id: UUID
    ) -> tuple[dict[str, Any], list[str], list[str], str, list[str]]:
        profile_row = session.exec(
            select(UserMemoryProfile).where(UserMemoryProfile.user_id == user_id)
        ).first()
        profile = (profile_row.memory_profile or {}) if profile_row else {}
        weak_points, goals, learning_style, signals = self._profile_signals(profile)
        practices = session.exec(
            select(PracticeRecord)
            .where(PracticeRecord.user_id == user_id)
            .order_by(PracticeRecord.practiced_at.desc())
            .limit(20)
        ).all()
        for practice in practices:
            accuracy = self._accuracy(practice.score, practice.correct_count, practice.total_questions)
            if accuracy < 0.7 and practice.topic not in weak_points:
                weak_points.append(practice.topic)
                signals.append(f"练习薄弱点：{practice.topic}（正确率 {accuracy:.0%}）")
        return profile, weak_points, goals, learning_style, signals

    def _recommendation_context(
        self, session: Session, *, user_id: UUID
    ) -> RecommendationContext:
        profile, weak_points, goals, learning_style, _ = self._profile_context(session, user_id=user_id)
        feedback = profile.get("recommendation_feedback") if isinstance(profile, dict) else {}
        feedback = feedback if isinstance(feedback, dict) else {}

        def affinities(name: str) -> dict[str, float]:
            values = feedback.get(name)
            if not isinstance(values, dict):
                return {}
            result: dict[str, float] = {}
            for key, details in values.items():
                if isinstance(details, dict):
                    try:
                        result[str(key)] = float(details.get("affinity", 0))
                    except (TypeError, ValueError):
                        pass
            return result

        practices = session.exec(
            select(PracticeRecord)
            .where(PracticeRecord.user_id == user_id)
            .order_by(PracticeRecord.practiced_at.desc())
            .limit(20)
        ).all()
        # Query is newest-first. Keep exactly the latest observation per topic
        # so a long history cannot overwrite current practice performance.
        practice_gaps: dict[str, float] = {}
        seen_practice_topics: set[str] = set()
        for row in practices:
            if not row.topic or row.topic in seen_practice_topics:
                continue
            seen_practice_topics.add(row.topic)
            accuracy = self._accuracy(row.score, row.correct_count, row.total_questions)
            if accuracy < 0.7:
                practice_gaps[row.topic] = 1 - accuracy
        mastery = profile.get("mastery_map") or profile.get("knowledge_state") or {}
        mastery_gaps = {
            str(topic).strip(): max(0.0, 0.7 - float(value))
            for topic, value in mastery.items()
            if str(topic).strip() and isinstance(value, (int, float)) and float(value) < 0.7
        } if isinstance(mastery, dict) else {}
        kb_context = profile.get("knowledge_base_context") if isinstance(profile, dict) else {}
        kb_topics = [str(value).strip() for value in (kb_context or {}).get("topic_signals", []) if str(value).strip()]
        interests = [str(value).strip() for value in (profile.get("interest_topics") or []) if str(value).strip()]
        preferred = affinities("modalities")
        aliases = {
            topic: TOPIC_QUERY_ALIASES[self._normalize_course_text(topic)]
            for topic in [*weak_points, *practice_gaps, *mastery_gaps, *goals, *interests, *kb_topics]
            if self._normalize_course_text(topic) in TOPIC_QUERY_ALIASES
        }
        return RecommendationContext(
            weak_points=weak_points,
            practice_gaps=practice_gaps,
            mastery_gaps=mastery_gaps,
            goals=goals[:1],
            interests=interests,
            kb_topics=kb_topics,
            learning_style=learning_style,
            preferred_modalities=preferred,
            topic_affinity=affinities("topics"),
            subject_affinity=affinities("subjects"),
            seen_topics=list(affinities("topics")),
            difficulty="foundation" if practice_gaps or weak_points else "standard",
            external_topic_aliases=aliases,
        )

    def _profile_signals(
        self, profile: dict[str, Any]
    ) -> tuple[list[str], list[str], str, list[str]]:
        weak_points = [str(item).strip() for item in (profile.get("weak_points") or []) if str(item).strip()]
        interest_topics = [
            str(item).strip()
            for item in (profile.get("interest_topics") or [])
            if str(item).strip()
        ]
        kb_context = profile.get("knowledge_base_context") or {}
        kb_topics = [
            str(item).strip()
            for item in (kb_context.get("topic_signals") or [])
            if str(item).strip()
        ]
        mastery = profile.get("mastery_map") or profile.get("knowledge_state") or {}
        if isinstance(mastery, dict):
            for topic, value in sorted(
                mastery.items(), key=lambda item: float(item[1]) if isinstance(item[1], (int, float)) else 1.0
            ):
                if isinstance(value, (int, float)) and float(value) < 0.7:
                    topic_text = str(topic).strip()
                    if topic_text and topic_text not in weak_points:
                        weak_points.append(topic_text)
        goal = str(profile.get("current_goal") or profile.get("learning_goal") or "").strip()
        goals = [goal] if goal else []
        goals.extend(
            item for item in [*interest_topics, *kb_topics] if item not in goals
        )
        style = str(profile.get("learning_style") or profile.get("cognitive_style") or "").strip()
        signals = [f"薄弱知识点：{item}" for item in weak_points[:5]]
        if goal:
            signals.append(f"当前目标：{goal}")
        if style:
            signals.append(f"学习偏好：{style}")
        signals.extend(f"近期学习主题：{item}" for item in interest_topics[:3])
        signals.extend(f"知识库关联：{item}" for item in kb_topics[:3])
        return weak_points, goals, style, signals

    @staticmethod
    def _accuracy(score: float, correct: int, total: int) -> float:
        if total > 0:
            return max(0.0, min(1.0, correct / total))
        return max(0.0, min(1.0, score / 100 if score > 1 else score))

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))


resource_recommendation_service = ResourceRecommendationService()
