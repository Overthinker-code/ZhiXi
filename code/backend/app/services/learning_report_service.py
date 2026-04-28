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
            from uuid import UUID
            from sqlalchemy import desc, or_
            try:
                uid = UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                uid = None
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
            from uuid import UUID
            from sqlalchemy import desc, or_
            try:
                uid = UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                uid = None
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
            from uuid import UUID
            from sqlalchemy import desc, or_
            try:
                uid = UUID(user_id) if isinstance(user_id, str) else user_id
            except ValueError:
                uid = None
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
            import json
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
            except Exception:
                pass
        profile = user_memory_profile_service.get_profile_dict(session, user_id) or {}
        history = self._recent_history(session, user_id)
        digest = self._history_digest(history)
        
        # 教育学参数联动1：注入课堂行为上下文
        behavior_context = self._get_recent_behavior_context(session, user_id)
        payload = self._infer_payload(profile=profile, history_digest=digest, behavior_context=behavior_context)
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
        
        # 教育学参数联动：附加课堂行为摘要
        classroom_behavior_summary = None
        if behavior_context:
            try:
                from uuid import UUID
                from sqlalchemy import desc
                try:
                    uid = UUID(user_id) if isinstance(user_id, str) else user_id
                except ValueError:
                    latest_record = None
                else:
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
                        "mind_wandering_rate": round(latest_record.mind_wandering_rate, 3),
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
            classroom_behavior_summary=classroom_behavior_summary,
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
