from __future__ import annotations

from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.models.chat import Chat
from app.models.chat_thread import ChatThread
from app.schemas.learning_report import (
    LearningReport,
    LearningReportSection,
    ReviewPlan,
    ReviewPlanDay,
    MistakeDigest,
    MistakeDigestItem,
)
from app.services.chat_model_factory import ChatModelFactory
from app.services.user_memory_profile_service import user_memory_profile_service


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


class LearningReportService:
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

    def _infer_payload(
        self,
        *,
        profile: dict[str, Any] | None,
        history_digest: str,
    ) -> _LearningReportPayload:
        current_goal = str(profile.get("current_goal") or "").strip() if profile else ""
        weak_points = profile.get("weak_points") or [] if profile else []
        learning_style = str(profile.get("learning_style") or "").strip() if profile else ""
        prompt = (
            "你是一名学情诊断助手。请根据学生长期画像与近期问答，"
            "输出严格 JSON，字段包括：summary, risk_level, strengths, "
            "recommended_actions, recommended_resources, follow_up_questions。\n"
            "risk_level 只能是 low / medium / high。\n"
            "每个数组给 2-4 条，尽量简洁可执行。\n\n"
            f"【当前目标】{current_goal or '暂无明确目标'}\n"
            f"【薄弱点】{'、'.join(weak_points) if weak_points else '暂无明确薄弱点'}\n"
            f"【学习偏好】{learning_style or '暂无明显偏好'}\n"
            f"【近期问答】\n{history_digest}"
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

    def _infer_review_plan(
        self,
        *,
        profile: dict[str, Any] | None,
        history: list[Chat],
        history_digest: str,
    ) -> _ReviewPlanPayload:
        topics = self._normalized_topics(profile, history)
        prompt = (
            "你是一名学习规划助手。请根据学生画像与近期问答，输出严格 JSON。"
            "字段包括：summary, focus_topics, daily_plan, checkpoints。\n"
            "其中 daily_plan 为数组，每项包含 day_label, focus, tasks。"
            "请输出 3 天复习计划，每天 2-4 条任务，简洁可执行。\n\n"
            f"【薄弱点】{'、'.join(topics)}\n"
            f"【近期问答】\n{history_digest}"
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

    def _infer_mistake_digest(
        self,
        *,
        profile: dict[str, Any] | None,
        history: list[Chat],
        history_digest: str,
    ) -> _MistakeDigestPayload:
        topics = self._normalized_topics(profile, history)
        prompt = (
            "你是一名错题整理助手。请根据学生画像和近期问答，输出严格 JSON。"
            "字段包括：summary, mistakes, flashcards。"
            "mistakes 为数组，每项包含 title, symptom, evidence, fix_strategy。"
            "请优先整理最值得优先复盘的 3 个错点。\n\n"
            f"【候选薄弱点】{'、'.join(topics)}\n"
            f"【近期问答】\n{history_digest}"
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
            except Exception:
                pass
        profile = user_memory_profile_service.get_profile_dict(session, user_id) or {}
        history = self._recent_history(session, user_id)
        digest = self._history_digest(history)
        payload = self._infer_payload(profile=profile, history_digest=digest)
        weak_points = [str(item).strip() for item in profile.get("weak_points") or [] if str(item).strip()]
        mastery_map = {
            str(topic): round(float(score), 4)
            for topic, score in (profile.get("mastery_map") or {}).items()
            if str(topic).strip()
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
        return LearningReport(
            learner_id=user_id,
            generated_at=datetime.utcnow().isoformat(),
            summary=payload.summary,
            current_goal=str(profile.get("current_goal") or "").strip(),
            learning_style=str(profile.get("learning_style") or "").strip(),
            risk_level=payload.risk_level,
            weak_points=weak_points,
            mastery_map=mastery_map,
            mastery_insights=self._mastery_insights(profile),
            mastery_formula=str(mastery_update.get("formula") or ""),
            strengths=payload.strengths,
            recommended_actions=payload.recommended_actions,
            recommended_resources=payload.recommended_resources,
            follow_up_questions=payload.follow_up_questions,
            sections=sections,
        )

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
        payload = self._infer_review_plan(
            profile=profile,
            history=history,
            history_digest=digest,
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
        payload = self._infer_mistake_digest(
            profile=profile,
            history=history,
            history_digest=digest,
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
