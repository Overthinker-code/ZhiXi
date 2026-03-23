from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, and_, or_

from app import models
from app.api import deps
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=models.TeachersPublic)
def read_teachers(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    name: str = None,
    identifier: str = None,
    ud_id: UUID = None,
) -> Any:
    """
    获取教师列表。
    """
    query = select(models.Teacher)
    conditions = []

    if name:
        conditions.append(models.Teacher.name.contains(name))
    if identifier:
        conditions.append(models.Teacher.identifier.contains(identifier))
    if ud_id:
        conditions.append(models.Teacher.ud_id == ud_id)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)
    teachers = db.exec(query).all()

    count_query = select(models.Teacher)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total = len(db.exec(count_query).all())

    return models.TeachersPublic(data=teachers, count=total)


@router.post("/", response_model=models.TeacherPublic)
def create_teacher(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    teacher_in: models.TeacherCreate,
) -> Any:
    """
    创建新教师。
    """
    # 检查UD是否存在
    ud = db.get(models.UD, teacher_in.ud_id)
    if not ud:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的大学-院系",
        )

    # 检查是否已存在相同标识符的教师
    query = select(models.Teacher).where(
        and_(
            models.Teacher.ud_id == teacher_in.ud_id,
            models.Teacher.identifier == teacher_in.identifier,
        )
    )
    existing_teacher = db.exec(query).first()
    if existing_teacher:
        raise HTTPException(
            status_code=400,
            detail="相同院系下已存在该教师标识符",
        )

    teacher = models.Teacher.from_orm(teacher_in)
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    return teacher


@router.get("/{teacher_id}", response_model=models.TeacherPublic)
def read_teacher(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    teacher_id: UUID,
) -> Any:
    """
    通过ID获取教师信息。
    """
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教师",
        )

    return teacher


@router.put("/{teacher_id}", response_model=models.TeacherPublic)
def update_teacher(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    teacher_id: UUID,
    teacher_in: models.TeacherUpdate,
) -> Any:
    """
    更新教师信息。
    """
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教师",
        )

    # 如果要更新ud_id，检查UD是否存在
    if teacher_in.ud_id and teacher_in.ud_id != teacher.ud_id:
        ud = db.get(models.UD, teacher_in.ud_id)
        if not ud:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的大学-院系",
            )

    # 如果要更新identifier或ud_id，检查组合是否已存在
    if (teacher_in.identifier and teacher_in.identifier != teacher.identifier) or (
        teacher_in.ud_id and teacher_in.ud_id != teacher.ud_id
    ):
        query = select(models.Teacher).where(
            and_(
                models.Teacher.ud_id == (teacher_in.ud_id or teacher.ud_id),
                models.Teacher.identifier
                == (teacher_in.identifier or teacher.identifier),
            )
        )
        existing_teacher = db.exec(query).first()
        if existing_teacher and existing_teacher.id != teacher_id:
            raise HTTPException(
                status_code=400,
                detail="相同院系下已存在该教师标识符",
            )

    teacher_data = teacher_in.dict(exclude_unset=True)
    for key, value in teacher_data.items():
        setattr(teacher, key, value)

    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    return teacher


@router.delete("/{teacher_id}")
def delete_teacher(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    teacher_id: UUID,
) -> Any:
    """
    删除教师。
    """
    teacher = db.get(models.Teacher, teacher_id)
    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教师",
        )

    # 检查是否有关联的教学班
    query_tc = select(models.TC).where(models.TC.lecturer_id == teacher_id)

    if db.exec(query_tc).first():
        raise HTTPException(
            status_code=400,
            detail="该教师存在关联的教学班，无法删除",
        )

    db.delete(teacher)
    db.commit()

    return {"detail": "教师已成功删除"}


@router.get("/by-name/", response_model=models.TeacherPublic)
def get_teacher_by_name(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    name: str,
    ud_id: UUID = None,
) -> Any:
    """
    通过姓名查找教师。
    """
    query = select(models.Teacher).where(models.Teacher.name == name)

    if ud_id:
        query = query.where(models.Teacher.ud_id == ud_id)

    teacher = db.exec(query).first()

    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教师",
        )

    return teacher
