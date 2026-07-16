from uuid import UUID, uuid4

import pytest

from app.models import Course, CourseKnowledgeNode
from scripts.backfill_resource_course_scope import (
    CurriculumIndex,
    ScopeDeclarations,
    backfill,
    declared_scope_conflict,
    quarantine_transition,
    should_repair_subject,
)


DATABASE_COURSE_ID = UUID("c1111111-1111-4111-9111-111111111101")
ECONOMICS_COURSE_ID = UUID("c1111111-1111-4111-9111-111111111104")


def _course(course_id: UUID, name: str) -> Course:
    return Course(
        id=course_id,
        ud_id=uuid4(),
        name=name,
        identifier=f"test-{course_id}",
    )


def _node(course_id: UUID, label: str, *, source: str = "course_plan") -> CourseKnowledgeNode:
    return CourseKnowledgeNode(
        id=uuid4(),
        course_id=course_id,
        normalized_key=f"concept:{label}",
        label=label,
        node_type="concept",
        map_type="knowledge",
        attributes={"source": source},
    )


def _index(*nodes: CourseKnowledgeNode) -> CurriculumIndex:
    return CurriculumIndex(
        courses=[
            _course(DATABASE_COURSE_ID, "数据库系统"),
            _course(ECONOMICS_COURSE_ID, "宏观经济学"),
        ],
        nodes=nodes,
    )


def test_unique_exact_curriculum_match_accepts_spacing_normalization() -> None:
    node = _node(DATABASE_COURSE_ID, "范式与 BCNF")
    resolution = _index(node).resolve(["范式与BCNF"])

    assert resolution.status == "unique"
    assert resolution.match is not None
    assert resolution.match.node_id == node.id
    assert resolution.match.course_id == DATABASE_COURSE_ID


def test_substring_and_generated_nodes_are_never_positive_evidence() -> None:
    curriculum = _node(DATABASE_COURSE_ID, "可串行化")
    generated = _node(ECONOMICS_COURSE_ID, "可串行化", source="resource_run")
    index = _index(curriculum, generated)

    assert index.resolve(["串行化"]).status == "unresolved"
    resolution = index.resolve(["可串行化"])
    assert resolution.status == "unique"
    assert resolution.match is not None
    assert resolution.match.course_id == DATABASE_COURSE_ID


def test_duplicate_curriculum_label_across_courses_remains_ambiguous() -> None:
    resolution = _index(
        _node(DATABASE_COURSE_ID, "共享主题"),
        _node(ECONOMICS_COURSE_ID, "共享主题"),
    ).resolve(["共享主题"])

    assert resolution.status == "ambiguous"
    assert resolution.match is None
    assert len(resolution.candidate_node_ids) == 2


def test_declared_completed_domain_conflict_blocks_relabelling() -> None:
    index = _index(_node(DATABASE_COURSE_ID, "可串行化"))

    conflicts = declared_scope_conflict(
        index=index,
        target_course_id=DATABASE_COURSE_ID,
        declarations=ScopeDeclarations(
            package_subject="宏观经济学",
            requested_subject="宏观经济学",
            model_domain="宏观经济学课程",
        ),
    )

    assert conflicts == {
        "package_subject": "宏观经济学",
        "requested_subject": "宏观经济学",
        "model_domain": "宏观经济学课程",
    }


def test_generic_subject_is_repairable_but_valid_specific_subject_is_preserved() -> None:
    index = _index(_node(DATABASE_COURSE_ID, "范式与 BCNF"))

    assert should_repair_subject(
        index=index,
        subject="未分类",
        target_course_id=DATABASE_COURSE_ID,
    )
    assert should_repair_subject(
        index=index,
        subject="宏观经济学",
        target_course_id=DATABASE_COURSE_ID,
    )
    assert not should_repair_subject(
        index=index,
        subject="数据库",
        target_course_id=DATABASE_COURSE_ID,
    )


def test_default_mode_never_plans_quarantine() -> None:
    assert quarantine_transition(
        enabled=False,
        config_exists=False,
        current_hidden=None,
    ) is None


def test_explicit_quarantine_records_reversible_before_and_after() -> None:
    transition = quarantine_transition(
        enabled=True,
        config_exists=True,
        current_hidden=False,
    )

    assert transition == (
        {"exists": True, "is_hidden": False},
        {"exists": True, "is_hidden": True},
    )


def test_quarantine_is_idempotent_for_already_hidden_resource() -> None:
    assert quarantine_transition(
        enabled=True,
        config_exists=True,
        current_hidden=True,
    ) is None


def test_quarantine_requires_apply_before_any_database_access() -> None:
    with pytest.raises(ValueError, match="quarantine_conflicts_requires_apply"):
        backfill(None, apply=False, quarantine_conflicts=True)  # type: ignore[arg-type]
