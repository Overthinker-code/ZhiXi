from __future__ import annotations

import math
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import or_, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlmodel import Session, select

from app.models import (
    Course,
    CourseKnowledgeEdge,
    CourseKnowledgeNode,
    CourseKnowledgeNodeAction,
    CoursePlan,
    LearningEvidence,
    Resource,
    ResourceKnowledgeLink,
    Student,
    StudentTC,
    TC,
    User,
)


# Only the curriculum/resource graph is materialized today.  Keeping unsupported
# product concepts in this set used to make the API return an empty graph with a
# convincing title, which is indistinguishable from a real but empty result.
MAP_TYPES = {"knowledge"}
RELATIONS = {"父子关系", "前后置关系", "关联关系", "资料支撑", "任务驱动"}
NODE_ACTION_TYPES = {"evidence_read", "review_queued", "resource_requested"}


def _normalized(value: str) -> str:
    value = re.sub(r"\s+", " ", (value or "").strip().lower())
    value = re.sub(r"[^\w\u4e00-\u9fff -]+", "", value)
    return value[:160] or "unnamed"


def _stable_id(course_id: UUID, map_type: str, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"zhixi:graph:{course_id}:{map_type}:{key}")


def _node_owner_id(node: CourseKnowledgeNode) -> UUID | None:
    raw_value = (node.attributes or {}).get("owner_id")
    if not raw_value:
        return None
    try:
        return UUID(str(raw_value))
    except (TypeError, ValueError, AttributeError):
        return None


def _node_is_visible(
    node: CourseKnowledgeNode,
    *,
    user: User,
    visible_resource_ids: set[UUID],
) -> bool:
    """Apply the same node privacy rule to maps, neighbors and actions."""
    if user.is_superuser:
        return True
    attributes = node.attributes or {}
    if attributes.get("source") == "resource_run":
        # Ownerless legacy generated concepts are hidden until repaired.  This
        # is deliberately fail-closed because their labels may contain private
        # user input.
        return _node_owner_id(node) == user.id
    if node.node_type == "resource":
        return _node_resource_id(node) in visible_resource_ids
    return True


def can_access_course(session: Session, *, user: User, course_id: UUID) -> bool:
    """Require a real enrollment or an explicit superuser grant."""
    if user.is_superuser:
        return session.get(Course, course_id) is not None
    enrolled = session.exec(
        select(StudentTC.id)
        .join(Student, Student.id == StudentTC.student_id)
        .join(TC, TC.id == StudentTC.tc_id)
        .where(Student.user_id == user.id, TC.course_id == course_id)
        .limit(1)
    ).first()
    return enrolled is not None


def get_node_actions(
    session: Session,
    *,
    user: User,
    course_id: UUID,
    map_type: str = "knowledge",
    node_id: UUID | None = None,
) -> dict[str, Any]:
    """Return persisted workflow state without treating it as mastery evidence."""
    if map_type not in MAP_TYPES:
        raise ValueError("invalid_map_type")
    if not can_access_course(session, user=user, course_id=course_id):
        raise PermissionError("course_access_denied")
    if node_id is not None:
        node = session.get(CourseKnowledgeNode, node_id)
        visible_resources = _visible_resource_ids(
            session, user=user, course_id=course_id
        )
        if (
            node is None
            or node.course_id != course_id
            or node.map_type != map_type
            or not _node_is_visible(
                node, user=user, visible_resource_ids=visible_resources
            )
        ):
            raise LookupError("node_not_found")
    query = (
        select(CourseKnowledgeNodeAction)
        .join(CourseKnowledgeNode, CourseKnowledgeNode.id == CourseKnowledgeNodeAction.node_id)
        .where(
            CourseKnowledgeNodeAction.user_id == user.id,
            CourseKnowledgeNodeAction.course_id == course_id,
            CourseKnowledgeNode.map_type == map_type,
        )
    )
    if node_id is not None:
        query = query.where(CourseKnowledgeNodeAction.node_id == node_id)
    rows = session.exec(query).all()
    visible_resources = _visible_resource_ids(
        session, user=user, course_id=course_id
    )
    states: dict[str, dict[str, Any]] = {}
    for row in rows:
        node = session.get(CourseKnowledgeNode, row.node_id)
        if node is None or not _node_is_visible(
            node, user=user, visible_resource_ids=visible_resources
        ):
            continue
        state = states.setdefault(
            str(row.node_id),
            {
                "evidenceRead": False,
                "reviewQueued": False,
                "resourceRequested": False,
                "updatedAt": None,
            },
        )
        field = {
            "evidence_read": "evidenceRead",
            "review_queued": "reviewQueued",
            "resource_requested": "resourceRequested",
        }.get(row.action_type)
        if field is None:
            continue
        state[field] = row.active
        updated_at = row.updated_at.isoformat()
        if not state["updatedAt"] or updated_at > state["updatedAt"]:
            state["updatedAt"] = updated_at
    return {
        "courseId": str(course_id),
        "mapType": map_type,
        "states": states,
    }


def set_node_action(
    session: Session,
    *,
    user: User,
    course_id: UUID,
    node_id: UUID,
    action_type: str,
    active: bool,
    map_type: str = "knowledge",
) -> dict[str, Any]:
    """Idempotently set an explicit graph workflow action."""
    if action_type not in NODE_ACTION_TYPES:
        raise ValueError("invalid_action_type")
    if map_type not in MAP_TYPES:
        raise ValueError("invalid_map_type")
    if not can_access_course(session, user=user, course_id=course_id):
        raise PermissionError("course_access_denied")
    node = session.get(CourseKnowledgeNode, node_id)
    visible_resources = _visible_resource_ids(
        session, user=user, course_id=course_id
    )
    if (
        node is None
        or node.course_id != course_id
        or node.map_type != map_type
        or not _node_is_visible(
            node, user=user, visible_resource_ids=visible_resources
        )
    ):
        raise LookupError("node_not_found")
    now = datetime.now(timezone.utc)
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        table = CourseKnowledgeNodeAction.__table__
        statement = postgresql_insert(table).values(
            id=uuid4(),
            user_id=user.id,
            course_id=course_id,
            node_id=node_id,
            action_type=action_type,
            active=active,
            created_at=now,
            updated_at=now,
        )
        # Concurrent retries are one database operation.  An identical retry is
        # a true no-op, including its timestamp; a changed value is updated.
        statement = statement.on_conflict_do_update(
            constraint="uq_course_knowledge_node_action_user_node_type",
            set_={"active": active, "updated_at": now},
            where=table.c.active != active,
        )
        session.exec(statement)
    else:
        row = session.exec(
            select(CourseKnowledgeNodeAction).where(
                CourseKnowledgeNodeAction.user_id == user.id,
                CourseKnowledgeNodeAction.node_id == node_id,
                CourseKnowledgeNodeAction.action_type == action_type,
            )
        ).first()
        if row is None:
            row = CourseKnowledgeNodeAction(
                user_id=user.id,
                course_id=course_id,
                node_id=node_id,
                action_type=action_type,
                active=active,
                created_at=now,
                updated_at=now,
            )
        elif row.active != active:
            row.active = active
            row.updated_at = now
        session.add(row)
    session.flush()
    action_row = session.exec(
        select(CourseKnowledgeNodeAction).where(
            CourseKnowledgeNodeAction.user_id == user.id,
            CourseKnowledgeNodeAction.node_id == node_id,
            CourseKnowledgeNodeAction.action_type == action_type,
        )
    ).one()
    evidence_version = action_row.updated_at
    if evidence_version.tzinfo is None:
        evidence_version = evidence_version.replace(tzinfo=timezone.utc)

    from app.services.learning_report_service import learning_report_service

    learning_report_service.record_evidence(
        session,
        user_id=user.id,
        course_id=course_id,
        knowledge_point=node.label,
        knowledge_point_id=str(node.id),
        source_type="knowledge_graph",
        # Identical retries share the persisted action version and therefore
        # the evidence idempotency key. A real state change updates the version
        # and creates a new behavioral observation.
        source_id=f"{node_id}:{action_type}:{evidence_version.isoformat()}",
        event_type=f"{action_type}_{'enabled' if active else 'disabled'}",
        weight=0.2,
        score=None,
        payload={
            "node_id": str(node_id),
            "action_type": action_type,
            "active": active,
            "resource_type": "knowledge_graph",
        },
    )
    session.commit()
    return get_node_actions(
        session,
        user=user,
        course_id=course_id,
        map_type=map_type,
        node_id=node_id,
    )


def _upsert_node(
    session: Session,
    *,
    course_id: UUID,
    map_type: str,
    key: str,
    label: str,
    node_type: str,
    detail: str,
    x: float,
    y: float,
    weight: float,
    attributes: dict[str, Any] | None = None,
) -> CourseKnowledgeNode:
    key = _normalized(key)
    node = session.exec(
        select(CourseKnowledgeNode).where(
            CourseKnowledgeNode.course_id == course_id,
            CourseKnowledgeNode.map_type == map_type,
            CourseKnowledgeNode.normalized_key == key,
        )
    ).first()
    if node is None:
        node = CourseKnowledgeNode(
            id=_stable_id(course_id, map_type, key),
            course_id=course_id,
            map_type=map_type,
            normalized_key=key,
            label=label.strip()[:180],
            node_type=node_type,
            detail=detail,
            position_x=x,
            position_y=y,
            weight=weight,
            attributes=attributes or {},
        )
        session.add(node)
        session.flush([node])
    return node


def _upsert_edge(
    session: Session,
    *,
    course_id: UUID,
    map_type: str,
    source: CourseKnowledgeNode,
    target: CourseKnowledgeNode,
    relation: str,
    strength: float = 1.0,
    source_type: str = "curriculum",
    run_id: str | None = None,
) -> CourseKnowledgeEdge:
    relation = relation if relation in RELATIONS else "关联关系"
    edge = session.exec(
        select(CourseKnowledgeEdge).where(
            CourseKnowledgeEdge.course_id == course_id,
            CourseKnowledgeEdge.map_type == map_type,
            CourseKnowledgeEdge.source_node_id == source.id,
            CourseKnowledgeEdge.target_node_id == target.id,
            CourseKnowledgeEdge.relation_type == relation,
        )
    ).first()
    if edge is None:
        edge = CourseKnowledgeEdge(
            id=uuid5(
                NAMESPACE_URL,
                f"zhixi:graph-edge:{course_id}:{map_type}:{source.id}:{target.id}:{relation}",
            ),
            course_id=course_id,
            map_type=map_type,
            source_node_id=source.id,
            target_node_id=target.id,
            relation_type=relation,
            strength=max(0.0, min(float(strength), 1.0)),
            source_type=source_type,
            run_id=run_id,
        )
        session.add(edge)
        session.flush([edge])
    return edge


def _private_generated_point(
    session: Session,
    *,
    course_id: UUID,
    owner_id: UUID,
    knowledge_point: str,
) -> CourseKnowledgeNode:
    """Create an owner-scoped generated topic, never a public curriculum node."""
    return _upsert_node(
        session,
        course_id=course_id,
        map_type="knowledge",
        key=(
            f"generated-concept:{owner_id}:"
            f"{_normalized(knowledge_point)}"
        ),
        label=knowledge_point,
        node_type="concept",
        detail="由个人资源生成运行关联的学习主题。",
        x=760,
        y=420,
        weight=2,
        attributes={"source": "resource_run", "owner_id": str(owner_id)},
    )


def _resource_link_needs_owner_repair(
    session: Session,
    *,
    link: ResourceKnowledgeLink,
) -> bool:
    resource = session.get(Resource, link.resource_id)
    if resource is None:
        return False
    if link.knowledge_node_id is None:
        return True
    node = session.get(CourseKnowledgeNode, link.knowledge_node_id)
    if node is None:
        return True
    return (
        (node.attributes or {}).get("source") == "resource_run"
        and _node_owner_id(node) != resource.uploader_id
    )


def ensure_course_graph(session: Session, *, course_id: UUID) -> None:
    """Idempotently materialize curriculum plans and legacy resource links."""
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        # Deterministic IDs prevent duplicate identities, while this transaction
        # lock prevents two first requests from racing between SELECT and INSERT.
        lock_key = course_id.int & ((1 << 63) - 1)
        session.exec(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            params={"lock_key": lock_key},
        )
    course = session.get(Course, course_id)
    if course is None:
        raise LookupError("course_not_found")
    existing_root = session.exec(
        select(CourseKnowledgeNode.id).where(
            CourseKnowledgeNode.course_id == course_id,
            CourseKnowledgeNode.map_type == "knowledge",
            CourseKnowledgeNode.normalized_key == "course-root",
        ).limit(1)
    ).first()
    course_resource_links = session.exec(
        select(ResourceKnowledgeLink).where(
            ResourceKnowledgeLink.course_id == course_id
        )
    ).all()
    pending_private_link = any(
        _resource_link_needs_owner_repair(session, link=link)
        for link in course_resource_links
    )
    if existing_root and not pending_private_link:
        return
    root = _upsert_node(
        session,
        course_id=course_id,
        map_type="knowledge",
        key="course-root",
        label=course.name,
        node_type="chapter",
        detail=course.description or f"{course.name}课程知识结构",
        x=470,
        y=230,
        weight=4,
        attributes={"source": "course"},
    )
    plans = session.exec(
        select(CoursePlan)
        .join(TC, TC.id == CoursePlan.tc_id)
        .where(TC.course_id == course_id)
        .order_by(CoursePlan.week)
    ).all()
    grouped: dict[str, list[CoursePlan]] = defaultdict(list)
    for plan in plans:
        grouped[plan.goal.strip()].append(plan)
    chapters: list[CourseKnowledgeNode] = []
    for chapter_index, (chapter_label, chapter_plans) in enumerate(grouped.items()):
        angle = -math.pi / 2 + (math.pi * 2 * chapter_index / max(len(grouped), 1))
        chapter_key = f"chapter:{_normalized(chapter_label)}"
        chapter = _upsert_node(
            session,
            course_id=course_id,
            map_type="knowledge",
            key=chapter_key,
            label=chapter_label,
            node_type="chapter",
            detail=f"覆盖 {'、'.join(item.key_point for item in chapter_plans)}。",
            x=470 + math.cos(angle) * 190,
            y=230 + math.sin(angle) * 135,
            weight=3,
            attributes={"source": "course_plan", "weeks": [item.week for item in chapter_plans]},
        )
        chapters.append(chapter)
        _upsert_edge(
            session, course_id=course_id, map_type="knowledge",
            source=root, target=chapter, relation="父子关系", strength=1,
        )
        previous: CourseKnowledgeNode | None = None
        for point_index, plan in enumerate(chapter_plans):
            concept = _upsert_node(
                session,
                course_id=course_id,
                map_type="knowledge",
                key=f"concept:{_normalized(chapter_label)}:{_normalized(plan.key_point)}",
                label=plan.key_point,
                node_type="concept",
                detail=f"{chapter_label}第 {plan.week} 周核心知识点。",
                x=chapter.position_x + 110 + (point_index % 2) * 55,
                y=chapter.position_y + (point_index - 1) * 58,
                weight=2 if point_index == 0 else 1,
                attributes={"source": "course_plan", "week": plan.week},
            )
            _upsert_edge(
                session, course_id=course_id, map_type="knowledge",
                source=chapter, target=concept, relation="父子关系", strength=0.95,
            )
            if previous is not None:
                _upsert_edge(
                    session, course_id=course_id, map_type="knowledge",
                    source=previous, target=concept, relation="前后置关系", strength=0.8,
                )
            previous = concept
    for left, right in zip(chapters, chapters[1:]):
        _upsert_edge(
            session, course_id=course_id, map_type="knowledge",
            source=left, target=right, relation="前后置关系", strength=0.7,
        )

    # Repair pre-owner links into private generated topics.  Public curriculum
    # nodes are left untouched if a future workflow links resources to them.
    for link in course_resource_links:
        if not _resource_link_needs_owner_repair(session, link=link):
            continue
        resource = session.get(Resource, link.resource_id)
        if resource is None:
            continue
        point = _private_generated_point(
            session,
            course_id=course_id,
            owner_id=resource.uploader_id,
            knowledge_point=link.knowledge_point,
        )
        resource_node = _resource_node(session, resource=resource)
        _upsert_edge(
            session, course_id=course_id, map_type="knowledge",
            source=point, target=resource_node, relation="资料支撑",
            strength=1, source_type="resource_run", run_id=link.run_id,
        )
        link.knowledge_node_id = point.id
        session.add(link)
    session.commit()


def _resource_node(session: Session, *, resource: Resource) -> CourseKnowledgeNode:
    return _upsert_node(
        session,
        course_id=resource.course_id,
        map_type="knowledge",
        key=f"resource:{resource.id}",
        label=resource.title,
        node_type="resource",
        detail=f"{resource.type} · {resource.file_name}",
        x=850,
        y=500,
        weight=1,
        attributes={"source": "resource", "resource_id": str(resource.id), "resource_type": resource.type},
    )


def link_generated_resources(
    session: Session,
    *,
    run_id: str,
    package_id: str,
    course_id: UUID,
    knowledge_point: str,
    resources: list[Resource],
) -> tuple[CourseKnowledgeNode, int]:
    owner_ids = {resource.uploader_id for resource in resources}
    if not resources or len(owner_ids) != 1:
        raise ValueError("generated_resources_require_one_owner")
    if any(resource.course_id != course_id for resource in resources):
        raise ValueError("generated_resource_course_mismatch")
    owner_id = next(iter(owner_ids))
    point = _private_generated_point(
        session,
        course_id=course_id,
        owner_id=owner_id,
        knowledge_point=knowledge_point,
    )
    linked = 0
    for resource in resources:
        resource_node = _resource_node(session, resource=resource)
        _upsert_edge(
            session,
            course_id=course_id,
            map_type="knowledge",
            source=point,
            target=resource_node,
            relation="资料支撑",
            strength=1,
            source_type="resource_run",
            run_id=run_id,
        )
        existing = session.exec(
            select(ResourceKnowledgeLink).where(
                ResourceKnowledgeLink.run_id == run_id,
                ResourceKnowledgeLink.resource_id == resource.id,
                ResourceKnowledgeLink.knowledge_node_id == point.id,
            )
        ).first()
        if existing is None:
            session.add(ResourceKnowledgeLink(
                run_id=run_id,
                package_id=package_id,
                resource_id=resource.id,
                course_id=course_id,
                knowledge_node_id=point.id,
                knowledge_point=knowledge_point,
                relation_type="supports",
            ))
            linked += 1
    session.flush()
    return point, linked


def _visible_resource_ids(session: Session, *, user: User, course_id: UUID) -> set[UUID]:
    query = select(Resource.id).where(Resource.course_id == course_id)
    if not user.is_superuser:
        query = query.where(or_(Resource.package_id.is_(None), Resource.uploader_id == user.id))
    return set(session.exec(query).all())


def _node_resource_id(node: CourseKnowledgeNode) -> UUID | None:
    """Parse legacy JSON attributes without letting corrupt IDs break a graph."""
    raw_value = (node.attributes or {}).get("resource_id")
    if not raw_value:
        return None
    try:
        return UUID(str(raw_value))
    except (TypeError, ValueError, AttributeError):
        return None


def _summarize_evidence(rows: list[LearningEvidence]) -> tuple[int | None, list[str]]:
    rows = sorted(rows, key=lambda row: row.observed_at, reverse=True)[:8]
    scored = [(row.score, max(row.weight, 0.0)) for row in rows if row.score is not None]
    denominator = sum(weight for _score, weight in scored)
    mastery = None
    if scored and denominator > 0:
        mastery = round(100 * sum(float(score) * weight for score, weight in scored) / denominator)
        mastery = max(0, min(mastery, 100))
    evidence = [
        f"{row.source_type} · {row.event_type}" + (f" · {round(float(row.score) * 100)}%" if row.score is not None else "")
        for row in rows[:4]
    ]
    return mastery, evidence


def _course_evidence_index(
    session: Session,
    *,
    user: User,
    course_id: UUID,
    nodes: list[CourseKnowledgeNode],
) -> dict[UUID, tuple[int | None, list[str]]]:
    """Load course evidence once; graph rendering must not issue one query per node."""
    rows = session.exec(
        select(LearningEvidence).where(
            LearningEvidence.user_id == user.id,
            LearningEvidence.course_id == course_id,
        ).order_by(LearningEvidence.observed_at.desc()).limit(500)
    ).all()
    by_id = {str(node.id): node.id for node in nodes}
    by_key: dict[str, set[UUID]] = defaultdict(set)
    by_label: dict[str, set[UUID]] = defaultdict(set)
    for node in nodes:
        by_key[node.normalized_key].add(node.id)
        by_label[node.label].add(node.id)
    buckets: dict[UUID, list[LearningEvidence]] = defaultdict(list)
    for row in rows:
        matched: set[UUID] = set()
        if row.knowledge_point_id and row.knowledge_point_id in by_id:
            matched.add(by_id[row.knowledge_point_id])
        matched.update(by_key.get(row.knowledge_point, set()))
        matched.update(by_label.get(row.display_name, set()))
        for node_id in matched:
            buckets[node_id].append(row)
    return {node.id: _summarize_evidence(buckets.get(node.id, [])) for node in nodes}


def _node_public(
    *,
    node: CourseKnowledgeNode,
    evidence_result: tuple[int | None, list[str]],
) -> dict[str, Any]:
    mastery, evidence = evidence_result
    attrs = dict(node.attributes or {})
    return {
        "id": str(node.id),
        "label": node.label,
        "type": node.node_type,
        "x": node.position_x,
        "y": node.position_y,
        "weight": node.weight,
        "detail": node.detail,
        "mastery": mastery,
        "evidence": evidence,
        "outcomes": list(attrs.get("outcomes") or []),
        "misconceptions": list(attrs.get("misconceptions") or []),
        "activities": list(attrs.get("activities") or []),
        "resources": list(attrs.get("resources") or []),
        "checks": list(attrs.get("checks") or []),
        "recommendedAction": attrs.get("recommended_action"),
    }


def get_course_map(
    session: Session, *, user: User, course_id: UUID, map_type: str = "knowledge"
) -> dict[str, Any]:
    if map_type not in MAP_TYPES:
        raise ValueError("invalid_map_type")
    if not can_access_course(session, user=user, course_id=course_id):
        raise PermissionError("course_access_denied")
    ensure_course_graph(session, course_id=course_id)
    course = session.get(Course, course_id)
    nodes = session.exec(select(CourseKnowledgeNode).where(
        CourseKnowledgeNode.course_id == course_id,
        CourseKnowledgeNode.map_type == map_type,
    )).all()
    visible_resources = _visible_resource_ids(session, user=user, course_id=course_id)
    visible_nodes = [
        node for node in nodes
        if _node_is_visible(
            node, user=user, visible_resource_ids=visible_resources
        )
    ]
    visible_ids = {node.id for node in visible_nodes}
    edges = session.exec(select(CourseKnowledgeEdge).where(
        CourseKnowledgeEdge.course_id == course_id,
        CourseKnowledgeEdge.map_type == map_type,
    )).all()
    public_edges = [edge for edge in edges if edge.source_node_id in visible_ids and edge.target_node_id in visible_ids]
    evidence_index = _course_evidence_index(
        session, user=user, course_id=course_id, nodes=visible_nodes
    )
    graph_map = {
        "type": map_type,
        "title": f"{course.name}知识图谱",
        "description": "基于课程计划、真实资源关系与学习证据生成；未评测节点不展示掌握度。",
        "nodes": [
            _node_public(node=node, evidence_result=evidence_index[node.id])
            for node in visible_nodes
        ],
        "links": [{
            "source": str(edge.source_node_id),
            "target": str(edge.target_node_id),
            "relation": edge.relation_type,
            "strength": edge.strength,
        } for edge in public_edges],
        "focusTags": [node.label for node in visible_nodes if node.node_type == "concept"][:4],
    }
    return {
        "courseId": str(course_id),
        "summary": {
            "nodeCount": len(visible_nodes),
            "linkCount": len(public_edges),
            "resourceCount": sum(node.node_type == "resource" for node in visible_nodes),
            "evidenceBackedNodeCount": sum(bool(evidence_index[node.id][1]) for node in visible_nodes),
        },
        "maps": [graph_map],
    }


def get_neighbors(
    session: Session,
    *,
    user: User,
    course_id: UUID,
    node_id: UUID,
    depth: int = 1,
    map_type: str = "knowledge",
) -> dict[str, Any]:
    if map_type not in MAP_TYPES:
        raise ValueError("invalid_map_type")
    if not can_access_course(session, user=user, course_id=course_id):
        raise PermissionError("course_access_denied")
    ensure_course_graph(session, course_id=course_id)
    center = session.get(CourseKnowledgeNode, node_id)
    if center is None or center.course_id != course_id or center.map_type != map_type:
        raise LookupError("node_not_found")
    visible_resources = _visible_resource_ids(session, user=user, course_id=course_id)
    all_nodes = session.exec(select(CourseKnowledgeNode).where(
        CourseKnowledgeNode.course_id == course_id,
        CourseKnowledgeNode.map_type == map_type,
    )).all()
    node_by_id = {
        node.id: node for node in all_nodes
        if _node_is_visible(
            node, user=user, visible_resource_ids=visible_resources
        )
    }
    if node_id not in node_by_id:
        raise LookupError("node_not_found")
    edges = session.exec(select(CourseKnowledgeEdge).where(
        CourseKnowledgeEdge.course_id == course_id,
        CourseKnowledgeEdge.map_type == map_type,
    )).all()
    edges = [edge for edge in edges if edge.source_node_id in node_by_id and edge.target_node_id in node_by_id]
    adjacency: dict[UUID, set[UUID]] = defaultdict(set)
    for edge in edges:
        adjacency[edge.source_node_id].add(edge.target_node_id)
        adjacency[edge.target_node_id].add(edge.source_node_id)
    selected = {node_id}
    queue: deque[tuple[UUID, int]] = deque([(node_id, 0)])
    while queue:
        current, distance = queue.popleft()
        if distance >= depth:
            continue
        for neighbor in adjacency[current]:
            if neighbor not in selected:
                selected.add(neighbor)
                queue.append((neighbor, distance + 1))
    selected_edges = [edge for edge in edges if edge.source_node_id in selected and edge.target_node_id in selected]
    selected_nodes = [node_by_id[item] for item in selected]
    evidence_index = _course_evidence_index(
        session, user=user, course_id=course_id, nodes=selected_nodes
    )
    return {
        "courseId": str(course_id),
        "centerNodeId": str(node_id),
        "depth": depth,
        "nodes": [
            _node_public(node=node, evidence_result=evidence_index[node.id])
            for node in selected_nodes
        ],
        "links": [{
            "source": str(edge.source_node_id),
            "target": str(edge.target_node_id),
            "relation": edge.relation_type,
            "strength": edge.strength,
        } for edge in selected_edges],
    }
