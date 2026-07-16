from typing import List, Optional
import json

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from app.api.deps import CurrentUser
from app.api import deps
from app.services import knowledge_graph_service
from app.services.rag_service import RAGService
from app.core.upload_security import validate_upload
from sqlmodel import Session
from uuid import UUID

router = APIRouter()
rag_service = RAGService()

ALLOWED_UPLOAD_EXTENSIONS = {
    ".c",
    ".cpp",
    ".doc",
    ".docx",
    ".java",
    ".js",
    ".pdf",
    ".ppt",
    ".pptx",
    ".py",
    ".sql",
    ".ts",
    ".txt",
    ".md",
    ".markdown",
}
SYSTEM_SCOPE = "system"
PERSONAL_SCOPE = "personal"
ALL_SCOPE = "all"


def _rag_role(current_user: CurrentUser) -> str:
    """Derive RAG privileges from the persisted authorization model only."""

    return "admin" if bool(getattr(current_user, "is_superuser", False)) else "user"


def _is_rag_admin(current_user: CurrentUser) -> bool:
    return _rag_role(current_user) == "admin"


def _resolve_upload_scope(scope: str, current_user: CurrentUser) -> str:
    normalized_scope = (scope or PERSONAL_SCOPE).strip().lower()
    if normalized_scope not in {SYSTEM_SCOPE, PERSONAL_SCOPE}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported scope: {scope}. "
                f"Allowed scopes: {SYSTEM_SCOPE}, {PERSONAL_SCOPE}"
            ),
        )
    if normalized_scope == SYSTEM_SCOPE and not _is_rag_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can upload system knowledge-base files",
        )
    if not _is_rag_admin(current_user):
        return PERSONAL_SCOPE
    return normalized_scope


def _resolve_list_scope(scope: str) -> str:
    normalized_scope = (scope or ALL_SCOPE).strip().lower()
    if normalized_scope not in {ALL_SCOPE, SYSTEM_SCOPE, PERSONAL_SCOPE}:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported scope filter: {scope}. "
                f"Allowed values: {ALL_SCOPE}, {SYSTEM_SCOPE}, {PERSONAL_SCOPE}"
            ),
        )
    return normalized_scope


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: Optional[int] = Field(default=4, ge=1, le=20)
    filter_type: Optional[str] = None
    # The public course-knowledge endpoint always needs an authorization
    # boundary. General chat may still use a user's own personal documents via
    # the service API, but must not query course-system chunks without a course.
    course_id: str = Field(min_length=1)

    @field_validator("query")
    @classmethod
    def validate_query_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("query must not be blank")
        return normalized


class QueryResponse(BaseModel):
    results: List[dict]


class FilesResponse(BaseModel):
    files: List[dict]


class CommitRequest(BaseModel):
    file_id: UUID


def _parse_knowledge_point_ids(raw: str) -> list[str]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value.split(",")
    if isinstance(parsed, str):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise HTTPException(status_code=400, detail="knowledge_point_ids must be a list")
    return [str(item).strip() for item in parsed if str(item).strip()]


def _validate_course_binding(
    *,
    session: Session,
    current_user: CurrentUser,
    course_id: str,
    chapter_id: str,
    knowledge_point_ids: list[str],
) -> str:
    """Validate the authorization boundary before persisting course metadata.

    Chapters are currently course-content identifiers rather than database
    entities, so their ownership is enforced by requiring a verified course
    binding. Persistent graph-node UUIDs are validated again by graph APIs when
    they are used as business state.
    """

    normalized_course_id = (course_id or "").strip()
    if not normalized_course_id:
        if (chapter_id or "").strip() or knowledge_point_ids:
            raise HTTPException(
                status_code=422,
                detail="chapter_id and knowledge_point_ids require a course_id",
            )
        return ""
    try:
        course_uuid = UUID(normalized_course_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid course_id") from exc
    if not knowledge_graph_service.can_access_course(
        session, user=current_user, course_id=course_uuid
    ):
        # Do not reveal whether an inaccessible course exists.
        raise HTTPException(status_code=404, detail="未找到指定课程资料")
    return str(course_uuid)


@router.post("/upload")
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    scope: str = Form(PERSONAL_SCOPE),
    course_id: str = Form(""),
    chapter_id: str = Form(""),
    knowledge_point_ids: str = Form(""),
    session: Session = Depends(deps.get_db),
):
    """Upload document into knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    await validate_upload(file, allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS)

    effective_scope = _resolve_upload_scope(scope, current_user)
    parsed_knowledge_point_ids = _parse_knowledge_point_ids(knowledge_point_ids)
    validated_course_id = _validate_course_binding(
        session=session,
        current_user=current_user,
        course_id=course_id,
        chapter_id=chapter_id,
        knowledge_point_ids=parsed_knowledge_point_ids,
    )

    try:
        result = await rag_service.process_uploaded_file(
            file,
            scope=effective_scope,
            owner_id=str(current_user.id),
            course_id=validated_course_id,
            chapter_id=chapter_id,
            knowledge_point_ids=parsed_knowledge_point_ids,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
def query_knowledge_base(
    request: QueryRequest,
    current_user: CurrentUser,
    session: Session = Depends(deps.get_db),
):
    """Query knowledge base."""
    try:
        try:
            course_uuid = UUID(request.course_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid course_id") from exc
        if not knowledge_graph_service.can_access_course(
            session, user=current_user, course_id=course_uuid
        ):
            raise HTTPException(status_code=404, detail="未找到指定课程资料")
        results = rag_service.query_knowledge_base(
            query=request.query,
            k=request.k,
            filter_type=request.filter_type,
            user_id=str(current_user.id),
            is_admin=_is_rag_admin(current_user),
            course_id=request.course_id,
        )
        return QueryResponse(results=results)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
def reset_knowledge_base(current_user: CurrentUser):
    """Reset knowledge base."""
    if not _is_rag_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only administrators can reset the knowledge base",
        )
    try:
        return rag_service.reset_knowledge_base()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files", response_model=FilesResponse)
def list_reference_files(
    current_user: CurrentUser, scope: str = Query(ALL_SCOPE)
):
    try:
        normalized_scope = _resolve_list_scope(scope)
        files = rag_service.list_reference_files(
            user_id=str(current_user.id),
            is_admin=_is_rag_admin(current_user),
            scope_filter=normalized_scope,
        )
        return FilesResponse(files=files)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_id}")
def delete_reference_file(file_id: str, current_user: CurrentUser):
    try:
        result = rag_service.delete_reference_file(
            file_id,
            user_id=str(current_user.id),
            is_admin=_is_rag_admin(current_user),
        )
        if result.get("message") == "Permission denied":
            raise HTTPException(status_code=403, detail=result.get("message"))
        if result.get("status") != "success":
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/preview")
async def preview_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    preview_chars: int = Form(800),
    preview_chunks: int = Form(5),
    chunk_preview_chars: int = Form(300),
    scope: str = Form(PERSONAL_SCOPE),
    course_id: str = Form(""),
    chapter_id: str = Form(""),
    knowledge_point_ids: str = Form(""),
    session: Session = Depends(deps.get_db),
):
    """Preview upload: parse and split document without committing into vector DB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    await validate_upload(file, allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS)

    effective_scope = _resolve_upload_scope(scope, current_user)
    parsed_knowledge_point_ids = _parse_knowledge_point_ids(knowledge_point_ids)
    validated_course_id = _validate_course_binding(
        session=session,
        current_user=current_user,
        course_id=course_id,
        chapter_id=chapter_id,
        knowledge_point_ids=parsed_knowledge_point_ids,
    )

    async def event_stream():
        try:
            async for payload in rag_service.stream_preview(
                file,
                preview_chars=preview_chars,
                preview_chunks=preview_chunks,
                chunk_preview_chars=chunk_preview_chars,
                scope=effective_scope,
                owner_id=str(current_user.id),
                course_id=validated_course_id,
                chapter_id=chapter_id,
                knowledge_point_ids=parsed_knowledge_point_ids,
            ):
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_payload = {"stage": "error", "message": str(e)}
            yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/upload/commit")
def commit_preview(request: CommitRequest, current_user: CurrentUser):
    try:
        result = rag_service.commit_preview(
            str(request.file_id),
            user_id=str(current_user.id),
            is_admin=_is_rag_admin(current_user),
        )
        if result.get("message") == "Permission denied":
            raise HTTPException(status_code=403, detail=result.get("message"))
        if result.get("status") != "success":
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/cancel")
def cancel_preview(request: CommitRequest, current_user: CurrentUser):
    try:
        result = rag_service.cancel_preview(
            str(request.file_id),
            user_id=str(current_user.id),
            is_admin=_is_rag_admin(current_user),
        )
        if result.get("message") == "Permission denied":
            raise HTTPException(status_code=403, detail=result.get("message"))
        if result.get("status") != "success":
            raise HTTPException(status_code=404, detail=result.get("message"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
