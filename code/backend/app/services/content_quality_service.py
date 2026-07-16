from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AcronymDefinition:
    """A registry entry for concepts whose named parts must be complete."""

    acronym: str
    aliases: tuple[str, ...]
    components: tuple[tuple[str, tuple[str, ...]], ...]

    @property
    def canonical_summary(self) -> str:
        return "、".join(f"{name}（{aliases[0]}）" for name, aliases in self.components)


@dataclass(frozen=True)
class ContentReviewResult:
    passed: bool
    reasons: tuple[str, ...]
    checks: dict[str, Any]


ACRONYM_REGISTRY: tuple[AcronymDefinition, ...] = (
    AcronymDefinition(
        acronym="ACID",
        aliases=("ACID", "事务特性"),
        components=(
            ("原子性", ("Atomicity", "原子性")),
            ("一致性", ("Consistency", "一致性")),
            ("隔离性", ("Isolation", "隔离性")),
            ("持久性", ("Durability", "持久性")),
        ),
    ),
    AcronymDefinition(
        acronym="CRUD",
        aliases=("CRUD",),
        components=(
            ("创建", ("Create", "创建", "新增")),
            ("读取", ("Read", "读取", "查询")),
            ("更新", ("Update", "更新", "修改")),
            ("删除", ("Delete", "删除")),
        ),
    ),
    AcronymDefinition(
        acronym="CAP",
        aliases=("CAP", "CAP 定理", "CAP理论"),
        components=(
            ("一致性", ("Consistency", "一致性")),
            ("可用性", ("Availability", "可用性")),
            ("分区容错性", ("Partition tolerance", "分区容错")),
        ),
    ),
)


# Course metadata alone proves that a course exists, but cannot support a factual
# claim. Only references that point to content, a stable node, or an observed
# learning event may enable course-grounded wording.
VERIFIABLE_EVIDENCE_TYPES = frozenset(
    {
        "course_resource",
        "uploaded_document",
        "course_document",
        "knowledge_chunk",
        "resource",
        "document",
    }
)


UNGROUNDED_COURSE_TERMS: tuple[str, ...] = (
    "课程讲义",
    "课堂讲义",
    "当前章节讲义",
    "课堂笔记",
    "课程图谱",
    "知识图谱节点",
    "知识图谱",
    "课程证据",
    "课堂证据",
    "课程内资料",
    "课堂案例",
)


UNGROUNDED_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("当前章节讲义", "主题学习材料"),
    ("课程讲义", "学习材料"),
    ("课堂讲义", "学习材料"),
    ("课堂笔记", "学习笔记"),
    ("课程图谱", "概念关系图"),
    ("知识图谱节点", "概念节点"),
    ("知识图谱", "概念关系图"),
    ("课程证据", "内容核验项"),
    ("课堂证据", "内容核验项"),
    ("课程内资料", "可核验学习资料"),
    ("课堂案例", "学习案例"),
)

ACRONYM_REQUIRED_KINDS = frozenset(
    {"lecture_markdown", "practice_markdown", "case_project", "video_script"}
)


class ContentQualityService:
    """Deterministic, extensible quality and evidence gates for resources."""

    @staticmethod
    def verifiable_evidence(citations: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
        verified: list[dict[str, Any]] = []
        for citation in citations or []:
            evidence_type = str(citation.get("type") or "").strip().lower()
            identifier = str(citation.get("source_id") or citation.get("id") or "").strip()
            if evidence_type in VERIFIABLE_EVIDENCE_TYPES and identifier:
                verified.append(citation)
        return verified

    @classmethod
    def has_verifiable_evidence(cls, citations: Iterable[dict[str, Any]] | None) -> bool:
        return bool(cls.verifiable_evidence(citations))

    @staticmethod
    def active_acronyms(topic: str, content: str) -> tuple[AcronymDefinition, ...]:
        search_text = f"{topic}\n{content}".lower()
        return tuple(
            definition
            for definition in ACRONYM_REGISTRY
            if any(alias.lower() in search_text for alias in definition.aliases)
        )

    @classmethod
    def review(
        cls,
        *,
        kind: str,
        content: str,
        topic: str,
        has_course_evidence: bool,
    ) -> ContentReviewResult:
        reasons: list[str] = []
        checks: dict[str, Any] = {}
        stripped = content.strip()
        if not stripped:
            return ContentReviewResult(False, ("empty_content",), {"non_empty": False})

        structure_rules: dict[str, tuple[tuple[str, bool], ...]] = {
            "lecture_markdown": (
                ("minimum_length", len(content) >= 400),
                ("section_structure", content.count("#") >= 2),
            ),
            "practice_markdown": (
                ("minimum_length", len(content) >= 450),
                ("question_structure", any(token in content for token in ("题", "练习", "任务"))),
                ("answer_or_rubric", any(token in content for token in ("答案", "评分", "量规"))),
            ),
            "mind_map": (
                ("valid_mermaid", any(token in content.lower() for token in ("mindmap", "graph", "flowchart"))),
            ),
            "reading_list": (
                ("minimum_length", len(content) >= 220),
                ("source_guidance", any(token in content for token in ("来源", "参考", "核验", "资料"))),
            ),
            "case_project": (
                ("minimum_length", len(content) >= 350),
                ("acceptance_criteria", any(token in content for token in ("验收", "量规", "交付"))),
            ),
            "video_script": (
                ("minimum_length", len(content) >= 300),
                ("interaction_design", any(token in content for token in ("互动", "停顿", "镜头"))),
            ),
            "quality_checklist": (
                ("minimum_length", len(content) >= 320),
                ("review_dimensions", any(token in content for token in ("引用", "事实", "安全", "质量", "核验"))),
            ),
        }
        structure = structure_rules.get(kind, ())
        checks["required_structure"] = {name: passed for name, passed in structure}
        reasons.extend(f"missing_required_field:{name}" for name, passed in structure if not passed)

        topic_bound = not topic or topic in content
        checks["topic_bound"] = topic_bound
        if not topic_bound:
            reasons.append("topic_not_grounded")

        acronym_checks: dict[str, Any] = {}
        definitions = cls.active_acronyms(topic, content) if kind in ACRONYM_REQUIRED_KINDS else ()
        for definition in definitions:
            missing = [
                name
                for name, aliases in definition.components
                if not any(alias.lower() in content.lower() for alias in aliases)
            ]
            acronym_checks[definition.acronym] = {"complete": not missing, "missing": missing}
            if missing:
                reasons.append(
                    f"incomplete_acronym:{definition.acronym}:{','.join(missing)}"
                )
        checks["acronym_completeness"] = acronym_checks

        ungrounded_terms = (
            []
            if has_course_evidence
            else [term for term in UNGROUNDED_COURSE_TERMS if term in content]
        )
        checks["evidence_gate"] = {
            "grounded": has_course_evidence,
            "unsupported_terms": ungrounded_terms,
        }
        if ungrounded_terms:
            reasons.append("unsupported_course_evidence_claim")

        return ContentReviewResult(not reasons, tuple(reasons), checks)

    @classmethod
    def repair_acronym_completeness(
        cls,
        content: str,
        topic: str,
        *,
        kind: str,
    ) -> tuple[str, list[str]]:
        additions: list[str] = []
        definitions = cls.active_acronyms(topic, content) if kind in ACRONYM_REQUIRED_KINDS else ()
        for definition in definitions:
            missing = [
                name
                for name, aliases in definition.components
                if not any(alias.lower() in content.lower() for alias in aliases)
            ]
            if missing:
                additions.append(f"- **{definition.acronym}**：{definition.canonical_summary}。")
        if not additions:
            return content, []
        section = "\n\n## 关键缩写完整性校验\n" + "\n".join(additions)
        return content.rstrip() + section + "\n", ["completed_acronym_components"]

    @staticmethod
    def neutralize_ungrounded_course_claims(content: str, *, kind: str) -> tuple[str, list[str]]:
        updated = content
        replacements: list[str] = []
        for source, target in UNGROUNDED_REPLACEMENTS:
            if source in updated:
                updated = updated.replace(source, target)
                replacements.append(f"{source}->{target}")
        if not replacements:
            return content, []
        disclosure = "未绑定可核验课程资料；以下内容基于通用学科知识生成，使用前应结合正式课程资料复核。"
        if kind == "mind_map":
            lines = updated.rstrip().splitlines()
            if lines:
                lines.extend(["  生成范围", f"    {disclosure}"])
                updated = "\n".join(lines) + "\n"
        elif disclosure not in updated:
            lines = updated.splitlines()
            insert_at = 1 if lines and lines[0].lstrip().startswith("#") else 0
            lines.insert(insert_at, f"\n> 生成范围：{disclosure}\n")
            updated = "\n".join(lines)
        return updated, replacements


content_quality_service = ContentQualityService()
