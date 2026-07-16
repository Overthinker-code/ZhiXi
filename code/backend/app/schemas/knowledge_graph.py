from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeGraphNode(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    mastery_score: float | None = Field(default=None, ge=0, le=1)


class KnowledgeGraphEdge(BaseModel):
    source: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=80)
    label: str | None = Field(default=None, max_length=80)


class KnowledgeGraphDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    root: str = Field(min_length=1, max_length=160)
    nodes: list[KnowledgeGraphNode] = Field(min_length=1, max_length=60)
    edges: list[KnowledgeGraphEdge] = Field(default_factory=list, max_length=120)


class KnowledgeGraphGenerateRequest(BaseModel):
    course: str = Field(min_length=1, max_length=120)
    knowledge_point: str = Field(min_length=1, max_length=160)


class KnowledgeGraphPayload(BaseModel):
    nodes: list[KnowledgeGraphNode]
    edges: list[KnowledgeGraphEdge]


class KnowledgeGraphPublic(BaseModel):
    id: UUID
    user_id: UUID
    course: str
    knowledge_point: str
    title: str
    root: str
    graph_json: KnowledgeGraphPayload
    created_time: datetime
    resource_type: str = "knowledge_graph"
    resource_id: str

    model_config = ConfigDict(from_attributes=True)
