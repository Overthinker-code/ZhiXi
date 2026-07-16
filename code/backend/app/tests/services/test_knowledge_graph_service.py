from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete, select

from app.api import deps
from app.core.db import engine
from app.main import app
from app.models import (
    Course,
    CourseKnowledgeEdge,
    CourseKnowledgeNode,
    CourseKnowledgeNodeAction,
    GeneratedResourcePackage,
    Resource,
    ResourceGenerationRun,
    ResourceKnowledgeLink,
    LearningEvidence,
    Student,
    StudentTC,
    User,
)
from app.services.knowledge_graph_service import (
    can_access_course,
    get_course_map,
    get_neighbors,
    get_node_actions,
    link_generated_resources,
    set_node_action,
)


COURSE_ID = UUID("c1111111-1111-4111-9111-111111111101")


def _student(db: Session) -> User:
    user = db.exec(select(User).where(User.email == "student@example.com")).first()
    assert user is not None
    return user


def test_course_graph_api_contract(
    client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    response = client.get(
        f"/api/v1/knowledge-graph/courses/{COURSE_ID}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["courseId"] == str(COURSE_ID)
    assert set(payload["summary"]) == {
        "nodeCount", "linkCount", "resourceCount", "evidenceBackedNodeCount"
    }
    graph = payload["maps"][0]
    root = next(node for node in graph["nodes"] if node["weight"] == 4)
    neighbors = client.get(
        f"/api/v1/knowledge-graph/courses/{COURSE_ID}/nodes/{root['id']}/neighbors",
        params={"depth": 1},
        headers=superuser_token_headers,
    )
    assert neighbors.status_code == 200
    assert neighbors.json()["centerNodeId"] == root["id"]
    action = client.put(
        f"/api/v1/knowledge-graph/courses/{COURSE_ID}/nodes/{root['id']}/actions/review_queued",
        params={"map_type": "knowledge"},
        json={"active": True},
        headers=superuser_token_headers,
    )
    assert action.status_code == 200
    assert action.json()["states"][root["id"]]["reviewQueued"] is True
    restored = client.get(
        f"/api/v1/knowledge-graph/courses/{COURSE_ID}/actions",
        params={"map_type": "knowledge", "node_id": root["id"]},
        headers=superuser_token_headers,
    )
    assert restored.status_code == 200
    assert restored.json()["states"][root["id"]]["reviewQueued"] is True

    unsupported = client.get(
        f"/api/v1/knowledge-graph/courses/{COURSE_ID}",
        params={"map_type": "ability"},
        headers=superuser_token_headers,
    )
    assert unsupported.status_code == 422


def test_course_graph_is_persisted_and_neighbor_query_is_course_scoped(db: Session) -> None:
    user = _student(db)
    assert can_access_course(db, user=user, course_id=COURSE_ID)

    payload = get_course_map(db, user=user, course_id=COURSE_ID)
    graph = payload["maps"][0]
    assert payload["courseId"] == str(COURSE_ID)
    assert payload["summary"]["nodeCount"] >= 5
    assert graph["nodes"]
    assert graph["links"]
    assert all(node["mastery"] is None or 0 <= node["mastery"] <= 100 for node in graph["nodes"])

    root = next(node for node in graph["nodes"] if node["weight"] == 4)
    neighborhood = get_neighbors(
        db,
        user=user,
        course_id=COURSE_ID,
        node_id=UUID(root["id"]),
        depth=1,
    )
    assert neighborhood["centerNodeId"] == root["id"]
    assert len(neighborhood["nodes"]) > 1
    returned_ids = {UUID(node["id"]) for node in neighborhood["nodes"]}
    persisted = db.exec(
        select(CourseKnowledgeNode).where(CourseKnowledgeNode.id.in_(returned_ids))
    ).all()
    assert len(persisted) == len(returned_ids)
    assert {node.course_id for node in persisted} == {COURSE_ID}


def test_course_graph_rejects_authenticated_but_unenrolled_user(db: Session) -> None:
    outsider = User(
        email=f"graph-outsider-{uuid4().hex}@example.com",
        username="graph-outsider",
        hashed_password="not-used-in-service-test",
    )
    db.add(outsider)
    db.flush([outsider])
    unrelated_upload = Resource(
        title="未选课用户的上传",
        type="document",
        file_name="outsider.md",
        file_path="tests/outsider.md",
        file_size=1,
        content_type="text/markdown",
        course_id=COURSE_ID,
        uploader_id=outsider.id,
    )
    db.add(unrelated_upload)
    db.commit()
    try:
        assert not can_access_course(db, user=outsider, course_id=COURSE_ID)
        try:
            get_course_map(db, user=outsider, course_id=COURSE_ID)
        except PermissionError:
            pass
        else:
            raise AssertionError("unenrolled users must not read a course graph")
    finally:
        db.delete(unrelated_upload)
        db.commit()
        db.delete(outsider)
        db.commit()


def test_course_graph_api_hides_course_from_unenrolled_user(
    client: TestClient,
    db: Session,
) -> None:
    outsider = User(
        email=f"graph-api-outsider-{uuid4().hex}@example.com",
        username="graph-api-outsider",
        hashed_password="not-used-in-service-test",
    )
    db.add(outsider)
    db.commit()
    app.dependency_overrides[deps.get_current_user] = lambda: outsider
    try:
        graph = client.get(f"/api/v1/knowledge-graph/courses/{COURSE_ID}")
        actions = client.get(f"/api/v1/knowledge-graph/courses/{COURSE_ID}/actions")
        assert graph.status_code == 404
        assert actions.status_code == 404
        assert graph.json()["detail"] == actions.json()["detail"]
    finally:
        app.dependency_overrides.pop(deps.get_current_user, None)
        db.delete(outsider)
        db.commit()


def test_resource_run_writes_node_edge_and_link_idempotently(db: Session) -> None:
    user = _student(db)
    run_id = f"rr_graph_{uuid4().hex[:12]}"
    package_id = f"rg_graph_{uuid4().hex[:12]}"
    package = GeneratedResourcePackage(
        id=package_id,
        user_id=user.id,
        course_id=COURSE_ID,
        subject="数据库系统",
        topic="事务与并发控制",
    )
    run = ResourceGenerationRun(
        id=run_id,
        user_id=user.id,
        course_id=COURSE_ID,
        package_id=package_id,
        status="completed",
        requested={},
        shared_state={},
    )
    resource = Resource(
        title="事务练习",
        type="practice_markdown",
        file_name="practice.md",
        file_path=f"generated_resources/{package_id}/practice.md",
        file_size=12,
        content_type="text/markdown",
        course_id=COURSE_ID,
        package_id=package_id,
        uploader_id=user.id,
    )
    db.add(package)
    db.flush([package])
    db.add(run)
    db.flush([run])
    db.add(resource)
    db.commit()
    try:
        node, first_count = link_generated_resources(
            db,
            run_id=run_id,
            package_id=package_id,
            course_id=COURSE_ID,
            knowledge_point="事务与并发控制",
            resources=[resource],
        )
        db.commit()
        _, second_count = link_generated_resources(
            db,
            run_id=run_id,
            package_id=package_id,
            course_id=COURSE_ID,
            knowledge_point="事务与并发控制",
            resources=[resource],
        )
        db.commit()
        assert first_count == 1
        assert second_count == 0
        edge = db.exec(select(CourseKnowledgeEdge).where(
            CourseKnowledgeEdge.run_id == run_id,
            CourseKnowledgeEdge.source_node_id == node.id,
        )).first()
        assert edge is not None
        assert edge.course_id == COURSE_ID
        assert edge.relation_type == "资料支撑"
    finally:
        db.rollback()
        for link in db.exec(select(ResourceKnowledgeLink).where(ResourceKnowledgeLink.run_id == run_id)).all():
            db.delete(link)
        for edge in db.exec(select(CourseKnowledgeEdge).where(CourseKnowledgeEdge.run_id == run_id)).all():
            db.delete(edge)
        db.commit()
        db.delete(resource)
        db.commit()
        db.delete(run)
        db.delete(package)
        db.commit()


def test_generated_graph_topics_are_private_between_students_in_same_course(
    db: Session,
) -> None:
    owner = _student(db)
    owner_student = db.exec(
        select(Student).where(Student.user_id == owner.id)
    ).first()
    assert owner_student is not None
    owner_enrollment = db.exec(
        select(StudentTC).where(StudentTC.student_id == owner_student.id)
    ).first()
    assert owner_enrollment is not None
    admin = db.exec(select(User).where(User.is_superuser == True)).first()  # noqa: E712
    assert admin is not None

    peer = User(
        email=f"graph-peer-{uuid4().hex}@example.com",
        username="graph-peer",
        hashed_password="not-used-in-service-test",
    )
    db.add(peer)
    db.flush([peer])
    peer_student = Student(
        name="同课隐私测试学生",
        identifier=f"graph-peer-{uuid4().hex[:12]}",
        ud_id=owner_student.ud_id,
        user_id=peer.id,
    )
    db.add(peer_student)
    db.flush([peer_student])
    peer_enrollment = StudentTC(
        student_id=peer_student.id,
        tc_id=owner_enrollment.tc_id,
    )
    db.add(peer_enrollment)

    topic = f"A的私有学习主题-{uuid4().hex}"
    run_id = f"rr_graph_private_{uuid4().hex[:10]}"
    package_id = f"rg_graph_private_{uuid4().hex[:10]}"
    package = GeneratedResourcePackage(
        id=package_id,
        user_id=owner.id,
        course_id=COURSE_ID,
        subject="数据库系统",
        topic=topic,
    )
    run = ResourceGenerationRun(
        id=run_id,
        user_id=owner.id,
        course_id=COURSE_ID,
        package_id=package_id,
        status="completed",
        requested={},
        shared_state={},
    )
    resource = Resource(
        title=f"{topic}私有讲义",
        type="lecture_markdown",
        file_name="private.md",
        file_path=f"generated_resources/{package_id}/private.md",
        file_size=12,
        content_type="text/markdown",
        course_id=COURSE_ID,
        package_id=package_id,
        uploader_id=owner.id,
    )
    db.add(package)
    db.flush([package])
    db.add(run)
    db.flush([run])
    db.add(resource)
    db.commit()

    point: CourseKnowledgeNode | None = None
    resource_node: CourseKnowledgeNode | None = None
    try:
        point, _ = link_generated_resources(
            db,
            run_id=run_id,
            package_id=package_id,
            course_id=COURSE_ID,
            knowledge_point=topic,
            resources=[resource],
        )
        db.commit()
        resource_node = db.exec(select(CourseKnowledgeNode).where(
            CourseKnowledgeNode.course_id == COURSE_ID,
            CourseKnowledgeNode.node_type == "resource",
            CourseKnowledgeNode.label == resource.title,
        )).first()
        assert resource_node is not None

        owner_payload = get_course_map(db, user=owner, course_id=COURSE_ID)
        owner_graph = owner_payload["maps"][0]
        assert any(node["id"] == str(point.id) and node["label"] == topic for node in owner_graph["nodes"])
        assert any(
            link["source"] == str(point.id) and link["target"] == str(resource_node.id)
            for link in owner_graph["links"]
        )

        peer_payload = get_course_map(db, user=peer, course_id=COURSE_ID)
        peer_graph = peer_payload["maps"][0]
        peer_serialized = str(peer_graph)
        assert topic not in peer_serialized
        assert str(point.id) not in peer_serialized
        assert str(resource_node.id) not in peer_serialized
        assert all(
            str(point.id) not in (link["source"], link["target"])
            for link in peer_graph["links"]
        )

        peer_root = next(node for node in peer_graph["nodes"] if node["weight"] == 4)
        peer_neighbors = get_neighbors(
            db,
            user=peer,
            course_id=COURSE_ID,
            node_id=UUID(peer_root["id"]),
            depth=2,
        )
        assert topic not in str(peer_neighbors)
        with pytest.raises(LookupError):
            get_neighbors(
                db,
                user=peer,
                course_id=COURSE_ID,
                node_id=point.id,
            )
        with pytest.raises(LookupError):
            get_node_actions(
                db,
                user=peer,
                course_id=COURSE_ID,
                node_id=point.id,
            )
        with pytest.raises(LookupError):
            set_node_action(
                db,
                user=peer,
                course_id=COURSE_ID,
                node_id=point.id,
                action_type="review_queued",
                active=True,
            )

        admin_graph = get_course_map(db, user=admin, course_id=COURSE_ID)["maps"][0]
        assert any(node["id"] == str(point.id) and node["label"] == topic for node in admin_graph["nodes"])
        assert any(
            link["source"] == str(point.id) and link["target"] == str(resource_node.id)
            for link in admin_graph["links"]
        )
        admin_neighbors = get_neighbors(
            db,
            user=admin,
            course_id=COURSE_ID,
            node_id=point.id,
        )
        assert topic in str(admin_neighbors)
        assert str(resource_node.id) in str(admin_neighbors)
    finally:
        db.rollback()
        db.exec(delete(ResourceKnowledgeLink).where(ResourceKnowledgeLink.run_id == run_id))
        db.exec(delete(CourseKnowledgeNodeAction).where(
            CourseKnowledgeNodeAction.node_id == (point.id if point else uuid4())
        ))
        db.exec(delete(CourseKnowledgeEdge).where(CourseKnowledgeEdge.run_id == run_id))
        db.commit()
        if resource_node is not None:
            db.delete(resource_node)
        if point is not None:
            db.delete(point)
        db.commit()
        db.delete(resource)
        db.commit()
        db.delete(run)
        db.delete(package)
        db.commit()
        db.exec(delete(StudentTC).where(StudentTC.id == peer_enrollment.id))
        db.exec(delete(Student).where(Student.id == peer_student.id))
        db.commit()
        db.exec(delete(User).where(User.id == peer.id))
        db.commit()


def test_node_actions_are_persisted_idempotently_without_mastery_evidence(db: Session) -> None:
    user = _student(db)
    graph = get_course_map(db, user=user, course_id=COURSE_ID)["maps"][0]
    node_id = UUID(next(node["id"] for node in graph["nodes"] if node["type"] == "concept"))
    evidence_before = len(db.exec(select(LearningEvidence).where(
        LearningEvidence.user_id == user.id,
        LearningEvidence.course_id == COURSE_ID,
    )).all())

    first = set_node_action(
        db,
        user=user,
        course_id=COURSE_ID,
        node_id=node_id,
        action_type="evidence_read",
        active=True,
    )
    second = set_node_action(
        db,
        user=user,
        course_id=COURSE_ID,
        node_id=node_id,
        action_type="evidence_read",
        active=True,
    )
    assert first == second
    assert second["states"][str(node_id)]["evidenceRead"] is True
    rows = db.exec(select(CourseKnowledgeNodeAction).where(
        CourseKnowledgeNodeAction.user_id == user.id,
        CourseKnowledgeNodeAction.node_id == node_id,
        CourseKnowledgeNodeAction.action_type == "evidence_read",
    )).all()
    assert len(rows) == 1
    evidence_rows = db.exec(select(LearningEvidence).where(
        LearningEvidence.user_id == user.id,
        LearningEvidence.course_id == COURSE_ID,
    )).all()
    assert len(evidence_rows) == evidence_before + 1
    action_evidence = evidence_rows[-1]
    assert action_evidence.source_type == "knowledge_graph"
    assert action_evidence.event_type == "evidence_read_enabled"
    assert action_evidence.score is None

    set_node_action(
        db,
        user=user,
        course_id=COURSE_ID,
        node_id=node_id,
        action_type="evidence_read",
        active=False,
    )
    state = get_node_actions(
        db,
        user=user,
        course_id=COURSE_ID,
        node_id=node_id,
    )
    assert state["states"][str(node_id)]["evidenceRead"] is False


def test_node_actions_are_user_scoped_and_concurrent_retries_are_idempotent(
    db: Session,
) -> None:
    student = _student(db)
    graph = get_course_map(db, user=student, course_id=COURSE_ID)["maps"][0]
    node_id = UUID(next(node["id"] for node in graph["nodes"] if node["type"] == "concept"))
    other_user = User(
        email=f"graph-action-{uuid4().hex}@example.com",
        username="graph-action-reviewer",
        hashed_password="not-used-in-service-test",
        is_superuser=True,
    )
    db.add(other_user)
    db.commit()

    def set_same_action() -> dict:
        with Session(engine) as worker:
            worker_user = worker.get(User, student.id)
            assert worker_user is not None
            return set_node_action(
                worker,
                user=worker_user,
                course_id=COURSE_ID,
                node_id=node_id,
                action_type="review_queued",
                active=True,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: set_same_action(), range(2)))
        assert all(item["states"][str(node_id)]["reviewQueued"] is True for item in results)
        db.expire_all()
        rows = db.exec(select(CourseKnowledgeNodeAction).where(
            CourseKnowledgeNodeAction.user_id == student.id,
            CourseKnowledgeNodeAction.node_id == node_id,
            CourseKnowledgeNodeAction.action_type == "review_queued",
        )).all()
        assert len(rows) == 1
        assert get_node_actions(
            db,
            user=other_user,
            course_id=COURSE_ID,
            node_id=node_id,
        )["states"] == {}
    finally:
        db.exec(delete(CourseKnowledgeNodeAction).where(
            CourseKnowledgeNodeAction.user_id.in_([student.id, other_user.id]),
            CourseKnowledgeNodeAction.node_id == node_id,
        ))
        db.commit()
        db.delete(other_user)
        db.commit()


def test_malformed_resource_node_id_is_ignored_instead_of_breaking_graph(db: Session) -> None:
    user = _student(db)
    bad_node = CourseKnowledgeNode(
        course_id=COURSE_ID,
        map_type="knowledge",
        normalized_key=f"bad-resource-{uuid4().hex}",
        label="损坏的旧资源引用",
        node_type="resource",
        attributes={"resource_id": "not-a-uuid"},
    )
    db.add(bad_node)
    db.commit()
    try:
        payload = get_course_map(db, user=user, course_id=COURSE_ID)
        assert all(node["id"] != str(bad_node.id) for node in payload["maps"][0]["nodes"])
    finally:
        db.delete(bad_node)
        db.commit()


def test_first_course_graph_load_is_concurrency_safe(db: Session) -> None:
    template = db.get(Course, COURSE_ID)
    assert template is not None
    course_id = uuid4()
    user_id = uuid4()
    course = Course(
        id=course_id,
        name="并发图谱测试课程",
        description="只用于验证首次图谱物化锁。",
        course_type="测试",
        identifier=f"GRAPH-{course_id.hex[:10]}",
        ud_id=template.ud_id,
    )
    user = User(
        id=user_id,
        email=f"graph-concurrency-{user_id.hex}@example.com",
        username="graph-concurrency",
        hashed_password="not-used-in-service-test",
        is_superuser=True,
    )
    db.add(course)
    db.add(user)
    db.commit()

    def first_load() -> dict:
        with Session(engine) as worker:
            worker_user = worker.get(User, user_id)
            assert worker_user is not None
            return get_course_map(
                worker,
                user=worker_user,
                course_id=course_id,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            payloads = list(pool.map(lambda _: first_load(), range(2)))
        assert [item["summary"]["nodeCount"] for item in payloads] == [1, 1]
        db.expire_all()
        roots = db.exec(select(CourseKnowledgeNode).where(
            CourseKnowledgeNode.course_id == course_id,
            CourseKnowledgeNode.normalized_key == "course-root",
        )).all()
        assert len(roots) == 1
    finally:
        db.exec(delete(CourseKnowledgeEdge).where(CourseKnowledgeEdge.course_id == course_id))
        db.exec(delete(CourseKnowledgeNodeAction).where(CourseKnowledgeNodeAction.course_id == course_id))
        db.exec(delete(CourseKnowledgeNode).where(CourseKnowledgeNode.course_id == course_id))
        db.commit()
        db.delete(course)
        db.delete(user)
        db.commit()
