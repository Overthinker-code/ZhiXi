from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from sqlmodel import Session, select

from app.models import (
    Course,
    ExternalResource,
    PersonalizedResourceRecommendation,
    PracticeRecord,
    Resource,
    UserMemoryProfile,
    UserResourceConfig,
)
from app.schemas.resource_generation import ResourceGenerationRequest
from app.schemas.resource_recommendation import (
    RecommendationActionResponse,
    RecommendationItem,
    ResourceRecommendationResponse,
)
from app.services.generated_knowledge_graph_service import knowledge_graph_service
from app.services.quiz_service import quiz_service
from app.services.resource_package_service import resource_package_service
from app.services.resource_subject_service import resolve_resource_subject


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
        learning_report_service.record_evidence(
            session,
            user_id=user_id,
            course_id=course_id,
            knowledge_point=item.knowledge_point or item.title,
            source_type="resource_interaction",
            source_id=f"{item.id}:{event_type}:{item.updated_time.isoformat()}",
            event_type=event_type,
            weight=0.2,
            score=None,
            payload={
                "recommendation_id": str(item.id),
                "resource_id": str(item.resource_id) if item.resource_id else None,
                "resource_type": item.type,
                "subject": item.subject,
                "origin": item.origin,
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
        if not active:
            active = self._create_profile_candidates(
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
                allow_discovery=refresh or not bool(session.exec(select(ExternalResource.id)).first()),
            )
            active = session.exec(
                select(PersonalizedResourceRecommendation).where(
                    PersonalizedResourceRecommendation.user_id == user_id,
                    PersonalizedResourceRecommendation.status == "active",
                )
            ).all()

        items = [self._public(item) for item in active]
        items.sort(key=lambda item: (item.favorite, item.score), reverse=True)
        return ResourceRecommendationResponse(
            generated_at=datetime.now(timezone.utc),
            profile_signals=self._unique(signals)[:8],
            agent_trace=["student_profile_agent", "resource_agent", "multimodal_planner"],
            items=items[:limit],
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
        return self._public(item)

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
            item.reason = f"根据你的“{item.knowledge_point}”画像信号重新检索的网络资源。"
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
                recommendation=self._public(item),
                message="已重新检索网络推荐",
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
            recommendation=self._public(item),
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
            resource = Resource(
                title=item.title,
                type="external",
                subject=item.subject,
                content_type="text/uri-list",
                url=item.url,
                knowledge_point=item.knowledge_point,
                difficulty=item.difficulty,
                source=item.source,
                uploader_id=user_id,
                course_id=course_id,
                content={"recommendation_id": str(item.id), "external": True},
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
            recommendation=self._public(item),
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
        rows: list[PersonalizedResourceRecommendation] = []
        for index, (resource_type, label, preview) in enumerate(MODALITY_SPECS):
            topic = topics[index % len(topics)]
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
                source="student-profile-agent",
                reason=f"根据你的个人画像，为“{topic}”规划的{label}，内容会在生成时动态创建。",
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

    def _create_external_candidates(
        self,
        session: Session,
        *,
        user_id: UUID,
        topics: list[str],
        allow_discovery: bool,
    ) -> None:
        externals = list(session.exec(select(ExternalResource)).all())
        if allow_discovery and topics:
            externals.extend(self._discover_external(session, topic=topics[0]))
        seen_urls: set[str] = set()
        for external in externals:
            if external.url in seen_urls:
                continue
            seen_urls.add(external.url)
            score, reason, evidence = self._score(
                title=external.title,
                knowledge_point=external.knowledge_point,
                resource_type=external.type,
                weak_points=topics,
                goals=[],
                learning_style="",
            )
            if score < 0.5 and topics:
                continue
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
                    url=external.url,
                    reason=external.recommend_reason or reason,
                    evidence=evidence + ["来源：公开网络"],
                    content_spec={"preview": "打开原网站查看完整内容", "network": True},
                    external_resource_id=external.id,
                )
            )
        session.commit()

    def _discover_external(self, session: Session, *, topic: str) -> list[ExternalResource]:
        try:
            from langchain_community.tools import DuckDuckGoSearchResults

            search = DuckDuckGoSearchResults(output_format="list", num_results=4)
            results = search.invoke(f"{topic} 教学 视频 课程 练习")
            if not isinstance(results, list):
                return []
        except Exception:
            return []
        created: list[ExternalResource] = []
        existing_urls = set(session.exec(select(ExternalResource.url)).all())
        for result in results:
            if not isinstance(result, dict):
                continue
            url = str(result.get("link") or result.get("url") or "")
            title = str(result.get("title") or "").strip()
            if not title or not url.startswith(("http://", "https://")) or url in existing_urls:
                continue
            host = urlparse(url).netloc.removeprefix("www.")[:80]
            resource_type = "video" if any(name in host for name in ("bilibili", "youtube")) else "document"
            external = ExternalResource(
                title=title[:255],
                source=host or "公开网络",
                url=url,
                type=resource_type,
                subject=resolve_resource_subject(None, topic, title),
                knowledge_point=topic[:160],
                difficulty="standard",
                recommend_reason=f"网络检索结果与薄弱知识点“{topic}”相关。",
            )
            session.add(external)
            created.append(external)
            existing_urls.add(url)
        if created:
            session.commit()
            for item in created:
                session.refresh(item)
        return created

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
        matched = next(
            (row for row in candidates if item.knowledge_point in row.knowledge_point or row.knowledge_point in item.knowledge_point),
            None,
        )
        if matched:
            return matched
        discovered = self._discover_external(session, topic=item.knowledge_point)
        return discovered[0] if discovered else None

    def _owned(
        self, session: Session, *, user_id: UUID, recommendation_id: UUID
    ) -> PersonalizedResourceRecommendation:
        item = session.get(PersonalizedResourceRecommendation, recommendation_id)
        if not item or item.user_id != user_id or item.status == "dismissed":
            raise LookupError("未找到指定推荐")
        return item

    def _public(self, item: PersonalizedResourceRecommendation) -> RecommendationItem:
        score, _, _ = self._score(
            title=item.title,
            knowledge_point=item.knowledge_point,
            resource_type=item.type,
            weak_points=[item.knowledge_point],
            goals=[],
            learning_style=str((item.content_spec or {}).get("learning_style") or ""),
        )
        resource_payload = None
        if item.resource_id:
            resource_payload = {"id": str(item.resource_id), "type": item.type}
        return RecommendationItem(
            id=str(item.id),
            origin=item.origin,  # type: ignore[arg-type]
            title=item.title,
            type=item.type,
            subject=item.subject,
            knowledge_point=item.knowledge_point,
            difficulty=item.difficulty,
            source=item.source,
            url=item.url,
            reason=item.reason,
            score=score,
            evidence=item.evidence,
            preview=str((item.content_spec or {}).get("preview") or ""),
            favorite=item.favorite,
            status=item.status,
            generation=item.generation,
            resource=resource_payload,
        )

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

    def _score(
        self,
        *,
        title: str,
        knowledge_point: str,
        resource_type: str,
        weak_points: list[str],
        goals: list[str],
        learning_style: str,
    ) -> tuple[float, str, list[str]]:
        searchable = f"{title} {knowledge_point}".lower()
        score = 0.25
        evidence: list[str] = []
        matched_weak = next(
            (point for point in weak_points if point.lower() in searchable or searchable in point.lower()), ""
        )
        if matched_weak:
            score += 0.55
            evidence.append(f"匹配薄弱知识点：{matched_weak}")
        matched_goal = next(
            (goal for goal in goals if any(token in searchable for token in self._tokens(goal))), ""
        )
        if matched_goal:
            score += 0.15
            evidence.append(f"匹配学习目标：{matched_goal}")
        if learning_style and self._style_matches(learning_style.lower(), resource_type):
            score += 0.12
            evidence.append(f"符合学习偏好：{learning_style}")
        reason = (
            f"你的“{matched_weak}”掌握度较弱，推荐针对性巩固。"
            if matched_weak
            else f"这份资料与当前学习目标“{matched_goal}”相关。"
            if matched_goal
            else "根据当前个人画像生成的多模态学习建议。"
        )
        return round(min(score, 0.99), 4), reason, evidence

    @staticmethod
    def _style_matches(style: str, resource_type: str) -> bool:
        if any(token in style for token in ("视觉", "图", "动画", "视频")):
            return resource_type in {"knowledge_graph", "image", "video"}
        if any(token in style for token in ("练习", "实践", "做题")):
            return resource_type in {"question", "code"}
        if any(token in style for token in ("阅读", "文字", "讲义")):
            return resource_type == "document"
        return False

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return [token.lower() for token in str(text).replace("，", " ").split() if len(token) >= 2]

    @staticmethod
    def _accuracy(score: float, correct: int, total: int) -> float:
        if total > 0:
            return max(0.0, min(1.0, correct / total))
        return max(0.0, min(1.0, score / 100 if score > 1 else score))

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))


resource_recommendation_service = ResourceRecommendationService()
