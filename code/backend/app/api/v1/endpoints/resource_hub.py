from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, SessionDep
from app.models import ExternalResource
from app.schemas.resource_recommendation import (
    ExternalResourceCreate,
    RecommendationActionResponse,
    RecommendationFavoriteRequest,
    ResourceRecommendationResponse,
)
from app.services.resource_subject_service import resolve_resource_subject
from app.services.resource_recommendation_service import resource_recommendation_service


router = APIRouter()


@router.get("/recommendations", response_model=ResourceRecommendationResponse)
def get_resource_recommendations(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    limit: int = Query(default=8, ge=1, le=20),
    refresh: bool = Query(default=False),
) -> Any:
    return resource_recommendation_service.recommend(
        session,
        user_id=current_user.id,
        limit=limit,
        refresh=refresh,
    )


@router.delete("/recommendations/{recommendation_id}", status_code=204)
def dismiss_recommendation(
    *, session: SessionDep, current_user: CurrentUser, recommendation_id: UUID
) -> None:
    try:
        resource_recommendation_service.dismiss(
            session, user_id=current_user.id, recommendation_id=recommendation_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/recommendations/{recommendation_id}/favorite")
def favorite_recommendation(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    recommendation_id: UUID,
    request: RecommendationFavoriteRequest,
) -> Any:
    try:
        return resource_recommendation_service.favorite(
            session,
            user_id=current_user.id,
            recommendation_id=recommendation_id,
            favorite=request.favorite,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/recommendations/{recommendation_id}/regenerate",
    response_model=RecommendationActionResponse,
)
def regenerate_recommendation(
    *, session: SessionDep, current_user: CurrentUser, recommendation_id: UUID
) -> Any:
    try:
        return resource_recommendation_service.regenerate(
            session, user_id=current_user.id, recommendation_id=recommendation_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"推荐资源重新生成失败：{exc}") from exc


@router.post(
    "/recommendations/{recommendation_id}/add-to-library",
    response_model=RecommendationActionResponse,
)
def add_recommendation_to_library(
    *, session: SessionDep, current_user: CurrentUser, recommendation_id: UUID
) -> Any:
    try:
        return resource_recommendation_service.add_to_library(
            session, user_id=current_user.id, recommendation_id=recommendation_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"推荐资源入库失败：{exc}") from exc


@router.post("/external", response_model=ExternalResource)
def save_external_resource(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    request: ExternalResourceCreate,
) -> Any:
    record = ExternalResource(
        title=request.title,
        source=request.source,
        url=str(request.url),
        type=request.type,
        subject=resolve_resource_subject(
            request.subject, request.knowledge_point, request.title
        ),
        knowledge_point=request.knowledge_point,
        difficulty=request.difficulty,
        recommend_reason=request.recommend_reason,
        created_by=current_user.id,
    )
    session.add(record)
    try:
        session.commit()
        session.refresh(record)
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="该外部资源链接已经保存") from exc
    return record
