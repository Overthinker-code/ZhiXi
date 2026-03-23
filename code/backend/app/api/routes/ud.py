from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, and_

from app import models, crud
from app.api import deps
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=models.UDPublic)
def read_uds(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    university: str = None,
    department: str = None,
) -> Any:
    """
    获取大学-院系列表。
    """
    query = select(models.UD)
    conditions = []

    if university:
        conditions.append(models.UD.university.contains(university))
    if department:
        conditions.append(models.UD.department.contains(department))

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)
    uds = db.exec(query).all()

    count_query = select(models.UD)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total = len(db.exec(count_query).all())

    return models.UDPublic(data=uds, count=total)


@router.post("/", response_model=models.UDPublic)
def create_ud(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    ud_in: models.UDCreate,
) -> Any:
    """
    创建新的大学-院系。
    """
    # 检查是否已存在相同的大学-院系
    query = select(models.UD).where(
        and_(
            models.UD.university == ud_in.university,
            models.UD.department == ud_in.department,
        )
    )
    existing_ud = db.exec(query).first()
    if existing_ud:
        raise HTTPException(
            status_code=400,
            detail="大学-院系组合已存在",
        )

    ud = models.UD.from_orm(ud_in)
    db.add(ud)
    db.commit()
    db.refresh(ud)

    return ud


@router.get("/{ud_id}", response_model=models.UDPublic)
def read_ud(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    ud_id: UUID,
) -> Any:
    """
    通过ID获取大学-院系信息。
    """
    ud = db.get(models.UD, ud_id)
    if not ud:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的大学-院系",
        )

    return ud


@router.put("/{ud_id}", response_model=models.UDPublic)
def update_ud(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    ud_id: UUID,
    ud_in: models.UDUpdate,
) -> Any:
    """
    更新大学-院系信息。
    """
    ud = db.get(models.UD, ud_id)
    if not ud:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的大学-院系",
        )

    # 如果要更新university或department，检查组合是否已存在
    if (ud_in.university and ud_in.university != ud.university) or (
        ud_in.department and ud_in.department != ud.department
    ):
        query = select(models.UD).where(
            and_(
                models.UD.university == (ud_in.university or ud.university),
                models.UD.department == (ud_in.department or ud.department),
            )
        )
        existing_ud = db.exec(query).first()
        if existing_ud and existing_ud.id != ud_id:
            raise HTTPException(
                status_code=400,
                detail="大学-院系组合已存在",
            )

    ud_data = ud_in.dict(exclude_unset=True)
    for key, value in ud_data.items():
        setattr(ud, key, value)

    db.add(ud)
    db.commit()
    db.refresh(ud)

    return ud


@router.delete("/{ud_id}")
def delete_ud(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    ud_id: UUID,
) -> Any:
    """
    删除大学-院系。
    """
    ud = db.get(models.UD, ud_id)
    if not ud:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的大学-院系",
        )

    # 检查是否有关联的教师、课程或学生
    query_teachers = select(models.Teacher).where(models.Teacher.ud_id == ud_id)
    query_courses = select(models.Course).where(models.Course.ud_id == ud_id)
    query_students = select(models.Student).where(models.Student.ud_id == ud_id)

    if (
        db.exec(query_teachers).first()
        or db.exec(query_courses).first()
        or db.exec(query_students).first()
    ):
        raise HTTPException(
            status_code=400,
            detail="该大学-院系存在关联的教师、课程或学生，无法删除",
        )

    db.delete(ud)
    db.commit()

    return {"detail": "大学-院系已成功删除"}
