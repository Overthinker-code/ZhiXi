from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.deps import CurrentUser
from app.services.rag_service import RAGService
from app.core.upload_security import validate_upload

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
    ".md",
    ".markdown",
    ".ppt",
    ".pptx",
    ".py",
    ".sql",
    ".ts",
    ".txt",
}


@router.post("/upload")
async def upload_file_for_thread(
    current_user: CurrentUser,
    file: UploadFile = File(...),
    thread_id: str = Form(...),
    course_id: str = Form(""),
    chapter_id: str = Form(""),
    knowledge_point_ids: str = Form(""),
):
    """会话级文件上传：用于 doc_researcher 在当前线程内检索文档。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    await validate_upload(file, allowed_extensions=ALLOWED_UPLOAD_EXTENSIONS)
    try:
        result = await rag_service.process_uploaded_file(
            file,
            scope="thread",
            owner_id=str(current_user.id),
            thread_id=thread_id,
            course_id=course_id,
            chapter_id=chapter_id,
            knowledge_point_ids=[
                item.strip() for item in knowledge_point_ids.split(",") if item.strip()
            ],
        )
        return {
            "status": "success",
            "file_id": result.get("file_id"),
            "file_name": file.filename,
            "thread_id": thread_id,
            "chunks": result.get("chunks", 0),
            "extraction_method": result.get("extraction_method", "legacy"),
            "ocr_pages": result.get("ocr_pages", 0),
            "preview_snippet": result.get("preview_snippet", ""),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
