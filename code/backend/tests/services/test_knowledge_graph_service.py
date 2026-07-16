from uuid import uuid4

from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session, select

from app.api.v1.endpoints.ai_chat import (
    _infer_resource_request,
    _is_knowledge_graph_intent,
    _is_resource_generation_intent,
    _knowledge_graph_context,
    _knowledge_graph_package,
)
from app.models import Resource
from app.models.knowledge_graph import KnowledgeGraph
from app.models.user import User  # noqa: F401
from app.models.user_memory_profile import UserMemoryProfile
from app.schemas.knowledge_graph import KnowledgeGraphDraft
from app.services.generated_knowledge_graph_service import knowledge_graph_service


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_chat_intent_and_context_are_specific_to_knowledge_graph() -> None:
    assert _is_knowledge_graph_intent("帮我生成数据库事务的知识图谱")
    assert _knowledge_graph_context("帮我生成数据库事务的知识图谱") == ("数据库", "事务")
    assert _knowledge_graph_context("生成TCP拥塞控制知识结构图") == ("计算机网络", "拥塞控制")
    assert not _is_knowledge_graph_intent("帮我解释数据库事务")
    assert not _is_knowledge_graph_intent("生成数据库练习题")


def test_natural_language_resource_intent_and_type_inference() -> None:
    assert _is_resource_generation_intent("帮我生成数据库事务学习资料")
    assert _is_resource_generation_intent("给我出10道机器学习练习题")
    assert not _is_resource_generation_intent("数据库事务是什么")
    document = _infer_resource_request("帮我生成数据库事务学习资料")
    quiz = _infer_resource_request("给我出10道机器学习练习题")
    assert document.types == ["lecture_note"]
    assert document.target == "数据库事务"
    assert quiz.types == ["quiz"]
    assert quiz.target == "机器学习"


def test_structured_graph_is_persisted_and_enriched_with_mastery(monkeypatch) -> None:
    db = _session()
    owner_id = uuid4()
    course_id = uuid4()
    db.add(
        UserMemoryProfile(
            user_id=owner_id,
            memory_profile={"mastery_map": {"锁机制": 0.35}},
        )
    )
    db.commit()
    draft = KnowledgeGraphDraft.model_validate(
        {
            "title": "数据库事务知识图谱",
            "root": "数据库事务",
            "nodes": [
                {"id": "transaction", "name": "数据库事务"},
                {"id": "acid", "name": "ACID"},
                {"id": "lock", "name": "锁机制"},
            ],
            "edges": [
                {"source": "transaction", "target": "acid"},
                {"source": "transaction", "target": "lock"},
                {"source": "missing", "target": "lock"},
            ],
        }
    )
    monkeypatch.setattr(
        knowledge_graph_service,
        "_generate_with_llm",
        lambda **_: draft,
    )

    result = knowledge_graph_service.generate(
        db,
        owner_id=owner_id,
        course="数据库",
        knowledge_point="事务",
        course_id=course_id,
    )

    assert result.resource_type == "knowledge_graph"
    assert len(result.graph_json.nodes) == 3
    assert len(result.graph_json.edges) == 2
    lock = next(node for node in result.graph_json.nodes if node.id == "lock")
    assert lock.mastery_score == 0.35
    stored = db.exec(select(KnowledgeGraph)).one()
    resource = db.exec(select(Resource)).one()
    assert stored.resource_id == resource.id
    assert result.resource_id == str(resource.id)
    assert resource.type == "knowledge_graph"
    assert resource.course_id == course_id
    assert resource.content["nodes"]
    assert "nodes" in stored.graph_json and "edges" in stored.graph_json
    assert "mermaid" not in stored.graph_json
    package = _knowledge_graph_package(result)
    artifact = package["artifacts"][0]
    assert artifact["course"] == "数据库"
    assert artifact["knowledge_point"] == "事务"
    assert artifact["graph_json"]["nodes"] == result.graph_json.model_dump()["nodes"]
    assert artifact["graph_json"]["edges"] == result.graph_json.model_dump()["edges"]
