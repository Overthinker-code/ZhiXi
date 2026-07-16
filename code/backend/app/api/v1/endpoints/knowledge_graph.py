from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, SessionDep
from app.models.knowledge_graph import KnowledgeGraph
from app.schemas.knowledge_graph import KnowledgeGraphGenerateRequest, KnowledgeGraphPublic
from app.services.knowledge_graph_service import (
    KnowledgeGraphGenerationError,
    knowledge_graph_service,
)

router = APIRouter()


@router.post("/resource/mindmap/generate", response_model=KnowledgeGraphPublic)
def generate_knowledge_graph(
    request: KnowledgeGraphGenerateRequest,
    session: SessionDep,
    current_user: CurrentUser,
):
    try:
        return knowledge_graph_service.generate(
            session,
            owner_id=current_user.id,
            course=request.course,
            knowledge_point=request.knowledge_point,
        )
    except KnowledgeGraphGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/resource/mindmap/{graph_id}", response_model=KnowledgeGraphPublic)
def get_knowledge_graph(
    graph_id: UUID,
    session: SessionDep,
    current_user: CurrentUser,
):
    record = session.get(KnowledgeGraph, graph_id)
    if not record or (record.user_id != current_user.id and not current_user.is_superuser):
        raise HTTPException(status_code=404, detail="Knowledge graph not found")
    return knowledge_graph_service.to_public(record)
