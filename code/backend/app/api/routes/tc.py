from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, and_, or_, join

from app import models
from app.api import deps
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=models.TCsPublic)
def read_tcs(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    course_id: UUID = None,
    lecturer_id: UUID = None,
    name: str = None,
) -> Any:
    """
    获取教学班列表。
    """
    query = select(models.TC)
    conditions = []

    if course_id:
        conditions.append(models.TC.course_id == course_id)
    if lecturer_id:
        conditions.append(models.TC.lecturer_id == lecturer_id)
    if name:
        conditions.append(models.TC.name.contains(name))

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)
    tcs = db.exec(query).all()

    # 添加课程和教师名称
    for tc in tcs:
        course = db.get(models.Course, tc.course_id)
        lecturer = db.get(models.Teacher, tc.lecturer_id)
        if course:
            tc.course_name = course.name
        if lecturer:
            tc.lecturer_name = lecturer.name

    count_query = select(models.TC)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total = len(db.exec(count_query).all())

    return models.TCsPublic(data=tcs, count=total)


@router.post("/", response_model=models.TCPublic)
def create_tc(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    tc_in: models.TCCreate,
) -> Any:
    """
    创建新教学班。
    """
    # 检查课程是否存在
    course = db.get(models.Course, tc_in.course_id)
    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程",
        )

    # 检查教师是否存在
    lecturer = db.get(models.Teacher, tc_in.lecturer_id)
    if not lecturer:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教师",
        )

    # 检查是否已存在相同的课程-教师组合
    query = select(models.TC).where(
        and_(
            models.TC.course_id == tc_in.course_id,
            models.TC.lecturer_id == tc_in.lecturer_id,
        )
    )
    existing_tc = db.exec(query).first()
    if existing_tc:
        raise HTTPException(
            status_code=400,
            detail="相同的课程-教师组合已存在",
        )

    tc = models.TC.from_orm(tc_in)

    # 如果没有提供名称，自动生成
    if not tc.name:
        tc.name = f"{course.name} - {lecturer.name}"

    db.add(tc)
    db.commit()
    db.refresh(tc)

    # 添加课程和教师名称
    tc.course_name = course.name
    tc.lecturer_name = lecturer.name

    return tc


@router.get("/{tc_id}", response_model=models.TCPublic)
def read_tc(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    tc_id: UUID,
) -> Any:
    """
    通过ID获取教学班信息。
    """
    tc = db.get(models.TC, tc_id)
    if not tc:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教学班",
        )

    # 添加课程和教师名称
    course = db.get(models.Course, tc.course_id)
    lecturer = db.get(models.Teacher, tc.lecturer_id)
    if course:
        tc.course_name = course.name
    if lecturer:
        tc.lecturer_name = lecturer.name

    return tc


@router.put("/{tc_id}", response_model=models.TCPublic)
def update_tc(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    tc_id: UUID,
    tc_in: models.TCUpdate,
) -> Any:
    """
    更新教学班信息。
    """
    tc = db.get(models.TC, tc_id)
    if not tc:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教学班",
        )

    course = None
    lecturer = None

    # 如果要更新course_id，检查课程是否存在
    if tc_in.course_id and tc_in.course_id != tc.course_id:
        course = db.get(models.Course, tc_in.course_id)
        if not course:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的课程",
            )
    else:
        course = db.get(models.Course, tc.course_id)

    # 如果要更新lecturer_id，检查教师是否存在
    if tc_in.lecturer_id and tc_in.lecturer_id != tc.lecturer_id:
        lecturer = db.get(models.Teacher, tc_in.lecturer_id)
        if not lecturer:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的教师",
            )
    else:
        lecturer = db.get(models.Teacher, tc.lecturer_id)

    # 如果要更新course_id或lecturer_id，检查组合是否已存在
    if (tc_in.course_id and tc_in.course_id != tc.course_id) or (
        tc_in.lecturer_id and tc_in.lecturer_id != tc.lecturer_id
    ):
        query = select(models.TC).where(
            and_(
                models.TC.course_id == (tc_in.course_id or tc.course_id),
                models.TC.lecturer_id == (tc_in.lecturer_id or tc.lecturer_id),
            )
        )
        existing_tc = db.exec(query).first()
        if existing_tc and existing_tc.id != tc_id:
            raise HTTPException(
                status_code=400,
                detail="相同的课程-教师组合已存在",
            )

    tc_data = tc_in.dict(exclude_unset=True)
    for key, value in tc_data.items():
        setattr(tc, key, value)

    # 如果名称为空，自动生成
    if not tc.name:
        tc.name = f"{course.name} - {lecturer.name}"

    db.add(tc)
    db.commit()
    db.refresh(tc)

    # 添加课程和教师名称
    if course:
        tc.course_name = course.name
    if lecturer:
        tc.lecturer_name = lecturer.name

    return tc


@router.delete("/{tc_id}")
def delete_tc(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    tc_id: UUID,
) -> Any:
    """
    删除教学班。
    """
    tc = db.get(models.TC, tc_id)
    if not tc:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教学班",
        )

    # 检查是否有关联的课程计划、视频或学生
    query_plans = select(models.CoursePlan).where(models.CoursePlan.tc_id == tc_id)
    query_videos = select(models.Video).where(models.Video.tc_id == tc_id)
    query_students = select(models.StudentTC).where(models.StudentTC.tc_id == tc_id)

    if (
        db.exec(query_plans).first()
        or db.exec(query_videos).first()
        or db.exec(query_students).first()
    ):
        raise HTTPException(
            status_code=400,
            detail="该教学班存在关联的课程计划、视频或学生，无法删除",
        )

    db.delete(tc)
    db.commit()

    return {"detail": "教学班已成功删除"}


@router.get("/{tc_id}/videos", response_model=models.VideosPublic)
def get_tc_videos(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    tc_id: UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    获取教学班的所有视频。
    """
    tc = db.get(models.TC, tc_id)
    if not tc:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教学班",
        )

    query = (
        select(models.Video)
        .where(models.Video.tc_id == tc_id)
        .offset(skip)
        .limit(limit)
    )
    videos = db.exec(query).all()

    count_query = select(models.Video).where(models.Video.tc_id == tc_id)
    total = len(db.exec(count_query).all())

    return models.VideosPublic(data=videos, count=total)
