from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage
from sqlmodel import Session, select

from app.models.knowledge_graph import KnowledgeGraph
from app.models import Resource
from app.models.user_memory_profile import UserMemoryProfile
from app.schemas.knowledge_graph import KnowledgeGraphDraft, KnowledgeGraphPublic
from app.services.chat_model_factory import ChatModelFactory
from app.services.resource_subject_service import resolve_resource_subject


class KnowledgeGraphGenerationError(RuntimeError):
    pass


class KnowledgeGraphService:
    def generate(
        self,
        db: Session,
        *,
        owner_id: UUID,
        course: str,
        knowledge_point: str,
        course_id: UUID | None = None,
    ) -> KnowledgeGraphPublic:
        draft = self._generate_with_llm(course=course, knowledge_point=knowledge_point)
        graph_json = self._normalize_graph(db, owner_id=owner_id, draft=draft)
        record = KnowledgeGraph(
            user_id=owner_id,
            course=course.strip(),
            knowledge_point=knowledge_point.strip(),
            title=draft.title.strip(),
            root=draft.root.strip(),
            graph_json=graph_json,
        )
        db.add(record)
        db.flush([record])
        resource = Resource(
            title=record.title,
            type="knowledge_graph",
            subject=resolve_resource_subject(course, knowledge_point, record.title),
            content_type="application/json",
            content={
                "knowledge_graph_id": str(record.id),
                "root": record.root,
                "nodes": graph_json["nodes"],
                "edges": graph_json["edges"],
            },
            knowledge_point=record.knowledge_point,
            difficulty="personalized",
            source="agent",
            uploader_id=owner_id,
            course_id=course_id,
        )
        db.add(resource)
        db.flush([resource])
        record.resource_id = resource.id
        db.add(record)
        db.commit()
        db.refresh(record)
        return self.to_public(record)

    def _generate_with_llm(self, *, course: str, knowledge_point: str) -> KnowledgeGraphDraft:
        prompt = f"""你是 KnowledgeGraph Agent。请为课程“{course}”中的知识点“{knowledge_point}”生成结构化知识图谱。

只输出一个 JSON 对象，禁止输出 Markdown、Mermaid、代码围栏或解释文字。固定格式：
{{
  "title": "图谱标题",
  "root": "根知识点",
  "nodes": [{{"id": "stable_id", "name": "节点名称", "mastery_score": null}}],
  "edges": [{{"source": "父节点id", "target": "子节点id", "label": null}}]
}}

要求：
1. 生成 8 至 24 个节点，覆盖概念、组成、机制和典型应用。
2. id 使用简短稳定的英文 snake_case，且必须唯一。
3. 每条边的 source 和 target 必须引用 nodes 中存在的 id。
4. root 必须对应一个节点名称；不要生成 Mermaid 字符串。
5. mastery_score 保留为 null，系统会根据学生画像补充。"""
        model = ChatModelFactory.create(temperature=0.2, max_tokens=2600, reasoning=False)
        try:
            structured = model.with_structured_output(KnowledgeGraphDraft)
            result = structured.invoke([HumanMessage(content=prompt)])
            return result if isinstance(result, KnowledgeGraphDraft) else KnowledgeGraphDraft.model_validate(result)
        except Exception:
            try:
                response = model.invoke([HumanMessage(content=prompt)])
                raw = str(getattr(response, "content", response) or "")
                match = re.search(r"\{[\s\S]*\}", raw)
                payload = json.loads(match.group(0) if match else raw)
                return KnowledgeGraphDraft.model_validate(payload)
            except Exception as exc:
                raise KnowledgeGraphGenerationError("知识图谱结构化生成失败") from exc

    def _normalize_graph(
        self,
        db: Session,
        *,
        owner_id: UUID,
        draft: KnowledgeGraphDraft,
    ) -> dict[str, list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, node in enumerate(draft.nodes):
            node_id = self._safe_id(node.id, fallback=f"node_{index + 1}")
            base_id = node_id
            suffix = 2
            while node_id in seen:
                node_id = f"{base_id}_{suffix}"
                suffix += 1
            seen.add(node_id)
            nodes.append({"id": node_id, "name": node.name.strip(), "mastery_score": node.mastery_score})

        if not any(item["name"] == draft.root for item in nodes):
            root_id = self._safe_id("root", fallback="root")
            while root_id in seen:
                root_id += "_1"
            nodes.insert(0, {"id": root_id, "name": draft.root.strip(), "mastery_score": None})
            seen.add(root_id)

        original_to_safe = {
            original.id: normalized["id"]
            for original, normalized in zip(draft.nodes, nodes[-len(draft.nodes):])
        }
        edges: list[dict[str, Any]] = []
        edge_seen: set[tuple[str, str, str]] = set()
        for edge in draft.edges:
            source = original_to_safe.get(edge.source, self._safe_id(edge.source, fallback=""))
            target = original_to_safe.get(edge.target, self._safe_id(edge.target, fallback=""))
            label = (edge.label or "").strip()
            key = (source, target, label)
            if source in seen and target in seen and source != target and key not in edge_seen:
                edges.append({"source": source, "target": target, "label": label or None})
                edge_seen.add(key)

        profile = db.exec(
            select(UserMemoryProfile).where(UserMemoryProfile.user_id == owner_id)
        ).first()
        memory = (profile.memory_profile or {}) if profile else {}
        mastery = memory.get("knowledge_state") or memory.get("mastery_map") or {}
        if isinstance(mastery, dict):
            for node in nodes:
                score = mastery.get(node["name"])
                if isinstance(score, (int, float)):
                    node["mastery_score"] = max(0.0, min(1.0, round(float(score), 4)))

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def _safe_id(value: str, *, fallback: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_]", "_", (value or "").strip()).strip("_").lower()
        return normalized[:80] or fallback

    @staticmethod
    def to_public(record: KnowledgeGraph) -> KnowledgeGraphPublic:
        return KnowledgeGraphPublic(
            id=record.id,
            user_id=record.user_id,
            course=record.course,
            knowledge_point=record.knowledge_point,
            title=record.title,
            root=record.root,
            graph_json=record.graph_json,
            created_time=record.created_time,
            resource_id=str(record.resource_id or record.id),
        )


knowledge_graph_service = KnowledgeGraphService()
