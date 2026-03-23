from typing import List, Optional
import json

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.services.rag_service import RAGService

router = APIRouter()
rag_service = RAGService()

ALLOWED_UPLOAD_EXTENSIONS = {
    ".doc",
    ".docx",
    ".pdf",
    ".ppt",
    ".pptx",
    ".md",
    ".markdown",
}
SYSTEM_SCOPE = "system"
PERSONAL_SCOPE = "personal"
ALL_SCOPE = "all"
RAG_ADMIN_EMAIL = "admin@example.com"
RAG_USER_EMAIL = "user@example.com"


def _rag_role(current_user: CurrentUser) -> str:
    if bool(getattr(current_user, "is_superuser", False)):
        return "admin"
    email = (current_user.email or "").strip().lower()
    if email == RAG_ADMIN_EMAIL:
        return "admin"
    if email == RAG_USER_EMAIL:
        return "user"
    return "user"


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
            detail=f"Only admin users can upload system files (e.g. {RAG_ADMIN_EMAIL})",
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
    query: str
    k: Optional[int] = 4
    filter_type: Optional[str] = None


class QueryResponse(BaseModel):
    results: List[dict]


class FilesResponse(BaseModel):
    files: List[dict]


class CommitRequest(BaseModel):
    file_id: str


@router.post("/upload")
async def upload_document(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    scope: str = Form(PERSONAL_SCOPE),
):
    """Upload document into knowledge base."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                f"Allowed types: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
            ),
        )

    effective_scope = _resolve_upload_scope(scope, current_user)

    try:
        result = await rag_service.process_uploaded_file(
            file,
            scope=effective_scope,
            owner_id=str(current_user.id),
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
def query_knowledge_base(request: QueryRequest, current_user: CurrentUser):
    """Query knowledge base."""
    try:
        results = rag_service.query_knowledge_base(
            query=request.query,
            k=request.k,
            filter_type=request.filter_type,
            user_id=str(current_user.id),
            is_admin=_is_rag_admin(current_user),
        )
        return QueryResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
def reset_knowledge_base(current_user: CurrentUser):
    """Reset knowledge base."""
    if not _is_rag_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail=f"Only admin users can reset knowledge base (e.g. {RAG_ADMIN_EMAIL})",
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
):
    """Preview upload: parse and split document without committing into vector DB."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                f"Allowed types: {', '.join(ALLOWED_UPLOAD_EXTENSIONS)}"
            ),
        )

    effective_scope = _resolve_upload_scope(scope, current_user)

    async def event_stream():
        try:
            async for payload in rag_service.stream_preview(
                file,
                preview_chars=preview_chars,
                preview_chunks=preview_chunks,
                chunk_preview_chars=chunk_preview_chars,
                scope=effective_scope,
                owner_id=str(current_user.id),
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
            request.file_id,
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
            request.file_id,
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
