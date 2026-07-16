from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.api import deps
from app.models import User
from app.services import knowledge_graph_service


router = APIRouter()


class NodeActionUpdate(BaseModel):
    active: bool


def _require_course_access(
    session: Session,
    *,
    current_user: User,
    course_id: UUID,
) -> None:
    if not knowledge_graph_service.can_access_course(
        session, user=current_user, course_id=course_id
    ):
        # Do not reveal whether an inaccessible course exists.
        raise HTTPException(status_code=404, detail="未找到指定课程图谱")


@router.get("/courses/{course_id}")
def read_course_knowledge_graph(
    course_id: UUID,
    session: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    map_type: str = Query(default="knowledge"),
) -> dict[str, Any]:
    _require_course_access(session, current_user=current_user, course_id=course_id)
    try:
        return knowledge_graph_service.get_course_map(
            session, user=current_user, course_id=course_id, map_type=map_type
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="不支持的图谱类型") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="未找到指定课程图谱") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="未找到指定课程图谱") from exc


@router.get("/courses/{course_id}/nodes/{node_id}/neighbors")
def read_node_neighbors(
    course_id: UUID,
    node_id: UUID,
    session: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    depth: int = Query(default=1, ge=1, le=2),
    map_type: str = Query(default="knowledge"),
) -> dict[str, Any]:
    _require_course_access(session, current_user=current_user, course_id=course_id)
    try:
        return knowledge_graph_service.get_neighbors(
            session,
            user=current_user,
            course_id=course_id,
            node_id=node_id,
            depth=depth,
            map_type=map_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="不支持的图谱类型") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="未找到指定课程图谱") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="未找到指定图谱节点") from exc


@router.get("/courses/{course_id}/actions")
def read_course_node_actions(
    course_id: UUID,
    session: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    map_type: str = Query(default="knowledge"),
    node_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    _require_course_access(session, current_user=current_user, course_id=course_id)
    try:
        return knowledge_graph_service.get_node_actions(
            session,
            user=current_user,
            course_id=course_id,
            map_type=map_type,
            node_id=node_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="不支持的图谱类型") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="未找到指定课程图谱") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="未找到指定图谱节点") from exc


@router.put("/courses/{course_id}/nodes/{node_id}/actions/{action_type}")
def update_course_node_action(
    course_id: UUID,
    node_id: UUID,
    action_type: Literal["evidence_read", "review_queued", "resource_requested"],
    payload: NodeActionUpdate,
    session: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    map_type: str = Query(default="knowledge"),
) -> dict[str, Any]:
    _require_course_access(session, current_user=current_user, course_id=course_id)
    try:
        return knowledge_graph_service.set_node_action(
            session,
            user=current_user,
            course_id=course_id,
            node_id=node_id,
            action_type=action_type,
            active=payload.active,
            map_type=map_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="不支持的节点动作或图谱类型") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="未找到指定课程图谱") from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="未找到指定图谱节点") from exc
