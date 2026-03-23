from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, and_, or_

from app import models
from app.api import deps
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=models.StudentsPublic)
def read_students(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    name: str = None,
    identifier: str = None,
    ud_id: UUID = None,
    tc_id: UUID = None,
) -> Any:
    """
    获取学生列表。
    """
    query = select(models.Student)
    conditions = []

    if name:
        conditions.append(models.Student.name.contains(name))
    if identifier:
        conditions.append(models.Student.identifier.contains(identifier))
    if ud_id:
        conditions.append(models.Student.ud_id == ud_id)

    # tc_id需要特殊处理，因为是多对多关系
    students = []

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)

    if tc_id:
        # 如果指定了tc_id，需要通过关联表查询
        query_tc_students = select(models.StudentTC.student_id).where(
            models.StudentTC.tc_id == tc_id
        )
        student_ids = db.exec(query_tc_students).all()

        if student_ids:
            # 找到这些学生，并应用原来的条件
            query = query.where(models.Student.id.in_([s_id for s_id in student_ids]))
            students = db.exec(query).all()
    else:
        students = db.exec(query).all()

    # 获取学生对应的教学班信息
    for student in students:
        query_tcs = select(models.StudentTC).where(
            models.StudentTC.student_id == student.id
        )
        student_tcs = db.exec(query_tcs).all()

        if student_tcs:
            student.tcs = []
            for student_tc in student_tcs:
                tc = db.get(models.TC, student_tc.tc_id)
                if tc:
                    course = db.get(models.Course, tc.course_id)
                    lecturer = db.get(models.Teacher, tc.lecturer_id)

                    tc_public = models.TCPublic(
                        id=tc.id,
                        name=tc.name,
                        course_id=tc.course_id,
                        lecturer_id=tc.lecturer_id,
                        created_at=tc.created_at,
                        updated_at=tc.updated_at,
                        course_name=course.name if course else None,
                        lecturer_name=lecturer.name if lecturer else None,
                    )
                    student.tcs.append(tc_public)

    count_query = select(models.Student)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    # 不能直接计算总数，因为可能有tc_id筛选
    if tc_id:
        total = len(students)
    else:
        total = len(db.exec(count_query).all())

    return models.StudentsPublic(data=students, count=total)


@router.post("/", response_model=models.StudentPublic)
def create_student(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    student_in: models.StudentCreate,
) -> Any:
    """
    创建新学生。
    """
    # 检查UD是否存在
    ud = db.get(models.UD, student_in.ud_id)
    if not ud:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的大学-院系",
        )

    # 检查是否已存在相同标识符的学生
    query = select(models.Student).where(
        and_(
            models.Student.ud_id == student_in.ud_id,
            models.Student.identifier == student_in.identifier,
        )
    )
    existing_student = db.exec(query).first()
    if existing_student:
        raise HTTPException(
            status_code=400,
            detail="相同院系下已存在该学生标识符",
        )

    # 检查所有的tc_id是否有效
    if student_in.tc_ids:
        for tc_id in student_in.tc_ids:
            tc = db.get(models.TC, tc_id)
            if not tc:
                raise HTTPException(
                    status_code=404,
                    detail=f"未找到ID为{tc_id}的教学班",
                )

    # 创建学生
    student = models.Student(
        name=student_in.name, identifier=student_in.identifier, ud_id=student_in.ud_id
    )
    db.add(student)
    db.commit()
    db.refresh(student)

    # 添加教学班关系
    if student_in.tc_ids:
        for tc_id in student_in.tc_ids:
            student_tc = models.StudentTC(student_id=student.id, tc_id=tc_id)
            db.add(student_tc)
        db.commit()

    # 获取学生的教学班信息
    student.tcs = []
    if student_in.tc_ids:
        for tc_id in student_in.tc_ids:
            tc = db.get(models.TC, tc_id)
            if tc:
                course = db.get(models.Course, tc.course_id)
                lecturer = db.get(models.Teacher, tc.lecturer_id)

                tc_public = models.TCPublic(
                    id=tc.id,
                    name=tc.name,
                    course_id=tc.course_id,
                    lecturer_id=tc.lecturer_id,
                    created_at=tc.created_at,
                    updated_at=tc.updated_at,
                    course_name=course.name if course else None,
                    lecturer_name=lecturer.name if lecturer else None,
                )
                student.tcs.append(tc_public)

    return student


@router.get("/{student_id}", response_model=models.StudentPublic)
def read_student(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    student_id: UUID,
) -> Any:
    """
    通过ID获取学生信息。
    """
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的学生",
        )

    # 获取学生的教学班信息
    query_tcs = select(models.StudentTC).where(
        models.StudentTC.student_id == student_id
    )
    student_tcs = db.exec(query_tcs).all()

    student.tcs = []
    for student_tc in student_tcs:
        tc = db.get(models.TC, student_tc.tc_id)
        if tc:
            course = db.get(models.Course, tc.course_id)
            lecturer = db.get(models.Teacher, tc.lecturer_id)

            tc_public = models.TCPublic(
                id=tc.id,
                name=tc.name,
                course_id=tc.course_id,
                lecturer_id=tc.lecturer_id,
                created_at=tc.created_at,
                updated_at=tc.updated_at,
                course_name=course.name if course else None,
                lecturer_name=lecturer.name if lecturer else None,
            )
            student.tcs.append(tc_public)

    return student


@router.put("/{student_id}", response_model=models.StudentPublic)
def update_student(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    student_id: UUID,
    student_in: models.StudentUpdate,
) -> Any:
    """
    更新学生信息。
    """
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的学生",
        )

    # 如果要更新ud_id，检查UD是否存在
    if student_in.ud_id and student_in.ud_id != student.ud_id:
        ud = db.get(models.UD, student_in.ud_id)
        if not ud:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的大学-院系",
            )

    # 如果要更新identifier或ud_id，检查组合是否已存在
    if (student_in.identifier and student_in.identifier != student.identifier) or (
        student_in.ud_id and student_in.ud_id != student.ud_id
    ):
        query = select(models.Student).where(
            and_(
                models.Student.ud_id == (student_in.ud_id or student.ud_id),
                models.Student.identifier
                == (student_in.identifier or student.identifier),
            )
        )
        existing_student = db.exec(query).first()
        if existing_student and existing_student.id != student_id:
            raise HTTPException(
                status_code=400,
                detail="相同院系下已存在该学生标识符",
            )

    # 更新基本信息
    student_data = student_in.dict(exclude={"tc_ids"}, exclude_unset=True)
    for key, value in student_data.items():
        setattr(student, key, value)

    db.add(student)
    db.commit()
    db.refresh(student)

    # 如果提供了tc_ids，更新教学班关系
    if student_in.tc_ids is not None:
        # 检查所有的tc_id是否有效
        for tc_id in student_in.tc_ids:
            tc = db.get(models.TC, tc_id)
            if not tc:
                raise HTTPException(
                    status_code=404,
                    detail=f"未找到ID为{tc_id}的教学班",
                )

        # 删除现有关系
        query_delete = select(models.StudentTC).where(
            models.StudentTC.student_id == student_id
        )
        existing_relations = db.exec(query_delete).all()
        for relation in existing_relations:
            db.delete(relation)

        # 添加新关系
        for tc_id in student_in.tc_ids:
            student_tc = models.StudentTC(student_id=student_id, tc_id=tc_id)
            db.add(student_tc)

        db.commit()

    # 获取学生的教学班信息
    query_tcs = select(models.StudentTC).where(
        models.StudentTC.student_id == student_id
    )
    student_tcs = db.exec(query_tcs).all()

    student.tcs = []
    for student_tc in student_tcs:
        tc = db.get(models.TC, student_tc.tc_id)
        if tc:
            course = db.get(models.Course, tc.course_id)
            lecturer = db.get(models.Teacher, tc.lecturer_id)

            tc_public = models.TCPublic(
                id=tc.id,
                name=tc.name,
                course_id=tc.course_id,
                lecturer_id=tc.lecturer_id,
                created_at=tc.created_at,
                updated_at=tc.updated_at,
                course_name=course.name if course else None,
                lecturer_name=lecturer.name if lecturer else None,
            )
            student.tcs.append(tc_public)

    return student


@router.delete("/{student_id}")
def delete_student(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    student_id: UUID,
) -> Any:
    """
    删除学生。
    """
    student = db.get(models.Student, student_id)
    if not student:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的学生",
        )

    # 删除所有关联的教学班关系
    query_tc_relations = select(models.StudentTC).where(
        models.StudentTC.student_id == student_id
    )
    tc_relations = db.exec(query_tc_relations).all()
    for relation in tc_relations:
        db.delete(relation)

    db.delete(student)
    db.commit()

    return {"detail": "学生已成功删除"}
