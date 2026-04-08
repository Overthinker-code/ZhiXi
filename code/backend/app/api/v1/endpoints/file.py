from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import CurrentUser
from app.services.rag_service import RAGService

router = APIRouter()
rag_service = RAGService()

ALLOWED_UPLOAD_EXTENSIONS = {
    ".doc",
    ".docx",
    ".pdf",
    ".md",
    ".markdown",
}


@router.post("/upload")
async def upload_file_for_thread(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    thread_id: str = Form(...),
):
    """会话级文件上传：用于 doc_researcher 在当前线程内检索文档。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    file_ext = "." + file.filename.split(".")[-1].lower()
    if file_ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported file type. "
                f"Allowed types: {', '.join(sorted(ALLOWED_UPLOAD_EXTENSIONS))}"
            ),
        )
    try:
        result = await rag_service.process_uploaded_file(
            file,
            scope="thread",
            owner_id=str(current_user.id),
            thread_id=thread_id,
        )
        return {
            "status": "success",
            "file_id": result.get("file_id"),
            "file_name": file.filename,
            "thread_id": thread_id,
            "chunks": result.get("chunks", 0),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
