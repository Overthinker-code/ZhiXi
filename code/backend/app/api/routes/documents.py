import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlmodel import Session, select, func

from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.models import (
    DocumentCategory,
    HelpDocument,
    HelpDocumentCreate,
    HelpDocumentPublic,
    HelpDocumentUpdate,
    HelpDocumentsPublic,
    Message,
    User,
)

router = APIRouter(prefix="/api/documents", tags=["documents"])

# 文档存储路径
DOCS_DIR = Path("./uploads/documents")
DOCS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=HelpDocumentPublic)
async def upload_document(
    *,
    session: SessionDep,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    category: DocumentCategory = Form(DocumentCategory.other),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_superuser),
):
    """
    上传帮助文档（仅管理员可用）
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    # 使用UUID创建唯一的文件名，避免冲突
    file_uuid = str(uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{file_uuid}{file_extension}"
    file_path = DOCS_DIR / safe_filename

    # 保存文件
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}",
        )

    # 获取文件大小
    file_size = os.path.getsize(file_path)

    # 创建数据库记录
    document = HelpDocument(
        title=title,
        description=description,
        category=category,
        file_path=str(file_path),
        file_name=file.filename,
        file_size=file_size,
        content_type=file.content_type or "application/octet-stream",
        uploader_id=current_user.id,
        created_at=datetime.utcnow(),
        is_active=True,
    )

    session.add(document)
    session.commit()
    session.refresh(document)

    return document


@router.get("/", response_model=HelpDocumentsPublic)
def get_documents(
    *,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    category: Optional[DocumentCategory] = None,
    include_inactive: bool = False,
):
    """
    获取帮助文档列表
    可以按分类筛选
    普通用户只能看到active=True的文档
    """
    query = select(HelpDocument)

    # 按分类筛选
    if category:
        query = query.where(HelpDocument.category == category)

    # 是否包含非活动文档
    if not include_inactive:
        query = query.where(HelpDocument.is_active == True)

    # 计算总数
    count_query = select(func.count()).select_from(HelpDocument)
    if category:
        count_query = count_query.where(HelpDocument.category == category)
    if not include_inactive:
        count_query = count_query.where(HelpDocument.is_active == True)

    total = session.exec(count_query).one()

    # 获取分页数据
    query = query.offset(skip).limit(limit)
    documents = session.exec(query).all()

    return HelpDocumentsPublic(data=documents, count=total)


@router.get("/{document_id}", response_model=HelpDocumentPublic)
def get_document(
    *,
    session: SessionDep,
    document_id: UUID,
    current_user: Optional[User] = None,
):
    """
    获取指定文档的详细信息
    普通用户只能看到active=True的文档
    """
    document = session.get(HelpDocument, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    # 检查权限：非管理员只能看到活动状态的文档
    if not document.is_active and (not current_user or not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档",
        )

    return document


@router.get("/download/{document_id}")
def download_document(
    *,
    session: SessionDep,
    document_id: UUID,
    current_user: Optional[User] = None,
):
    """
    下载指定文档
    普通用户只能下载active=True的文档
    """
    document = session.get(HelpDocument, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    # 检查权限：非管理员只能下载活动状态的文档
    if not document.is_active and (not current_user or not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权下载此文档",
        )

    file_path = document.file_path

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档文件不存在",
        )

    return FileResponse(
        path=file_path,
        filename=document.file_name,
        media_type=document.content_type,
    )


@router.put("/{document_id}", response_model=HelpDocumentPublic)
def update_document(
    *,
    session: SessionDep,
    document_id: UUID,
    document_update: HelpDocumentUpdate,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    更新文档信息（仅管理员可用）
    """
    document = session.get(HelpDocument, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    # 更新文档属性
    update_data = document_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(document, key, value)

    # 设置更新时间
    document.updated_at = datetime.utcnow()

    session.add(document)
    session.commit()
    session.refresh(document)

    return document


@router.delete("/{document_id}", response_model=Message)
def delete_document(
    *,
    session: SessionDep,
    document_id: UUID,
    current_user: User = Depends(get_current_active_superuser),
):
    """
    删除文档（仅管理员可用）
    """
    document = session.get(HelpDocument, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在",
        )

    # 获取文件路径以便删除
    file_path = document.file_path

    # 从数据库删除记录
    session.delete(document)
    session.commit()

    # 尝试删除文件
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        # 即使文件删除失败，数据库记录已经删除，所以返回部分成功信息
        return Message(message=f"文档记录已删除，但文件删除失败: {str(e)}")

    return Message(message="文档已成功删除")
