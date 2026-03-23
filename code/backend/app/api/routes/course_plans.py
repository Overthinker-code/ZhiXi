from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, and_, or_

from app import models
from app.api import deps
from uuid import UUID

router = APIRouter()


@router.get("/", response_model=models.CoursePlansPublic)
def read_course_plans(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    tc_id: UUID = None,
    week: int = None,
) -> Any:
    """
    获取课程计划列表。
    """
    query = select(models.CoursePlan)
    conditions = []

    if tc_id:
        conditions.append(models.CoursePlan.tc_id == tc_id)
    if week:
        conditions.append(models.CoursePlan.week == week)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)
    course_plans = db.exec(query).all()

    count_query = select(models.CoursePlan)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total = len(db.exec(count_query).all())

    return models.CoursePlansPublic(data=course_plans, count=total)


@router.post("/", response_model=models.CoursePlanPublic)
def create_course_plan(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    course_plan_in: models.CoursePlanCreate,
) -> Any:
    """
    创建新课程计划。
    """
    # 检查教学班是否存在
    tc = db.get(models.TC, course_plan_in.tc_id)
    if not tc:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的教学班",
        )

    # 检查周次是否在有效范围内
    if course_plan_in.week < 1 or course_plan_in.week > 20:
        raise HTTPException(
            status_code=400,
            detail="周次必须在1到20之间",
        )

    # 检查是否已存在相同教学班和周次的课程计划
    query = select(models.CoursePlan).where(
        and_(
            models.CoursePlan.tc_id == course_plan_in.tc_id,
            models.CoursePlan.week == course_plan_in.week,
        )
    )
    existing_plan = db.exec(query).first()
    if existing_plan:
        raise HTTPException(
            status_code=400,
            detail="相同教学班和周次的课程计划已存在",
        )

    course_plan = models.CoursePlan.from_orm(course_plan_in)
    db.add(course_plan)
    db.commit()
    db.refresh(course_plan)

    return course_plan


@router.get("/{course_plan_id}", response_model=models.CoursePlanPublic)
def read_course_plan(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    course_plan_id: UUID,
) -> Any:
    """
    通过ID获取课程计划信息。
    """
    course_plan = db.get(models.CoursePlan, course_plan_id)
    if not course_plan:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程计划",
        )

    return course_plan


@router.put("/{course_plan_id}", response_model=models.CoursePlanPublic)
def update_course_plan(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    course_plan_id: UUID,
    course_plan_in: models.CoursePlanUpdate,
) -> Any:
    """
    更新课程计划信息。
    """
    course_plan = db.get(models.CoursePlan, course_plan_id)
    if not course_plan:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程计划",
        )

    # 如果要更新tc_id，检查教学班是否存在
    if course_plan_in.tc_id and course_plan_in.tc_id != course_plan.tc_id:
        tc = db.get(models.TC, course_plan_in.tc_id)
        if not tc:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的教学班",
            )

    # 如果要更新week，检查是否在有效范围内
    if course_plan_in.week and (course_plan_in.week < 1 or course_plan_in.week > 20):
        raise HTTPException(
            status_code=400,
            detail="周次必须在1到20之间",
        )

    # 如果要更新tc_id或week，检查组合是否已存在
    if (course_plan_in.tc_id and course_plan_in.tc_id != course_plan.tc_id) or (
        course_plan_in.week and course_plan_in.week != course_plan.week
    ):
        query = select(models.CoursePlan).where(
            and_(
                models.CoursePlan.tc_id == (course_plan_in.tc_id or course_plan.tc_id),
                models.CoursePlan.week == (course_plan_in.week or course_plan.week),
            )
        )
        existing_plan = db.exec(query).first()
        if existing_plan and existing_plan.id != course_plan_id:
            raise HTTPException(
                status_code=400,
                detail="相同教学班和周次的课程计划已存在",
            )

    course_plan_data = course_plan_in.dict(exclude_unset=True)
    for key, value in course_plan_data.items():
        setattr(course_plan, key, value)

    db.add(course_plan)
    db.commit()
    db.refresh(course_plan)

    return course_plan


@router.delete("/{course_plan_id}")
def delete_course_plan(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    course_plan_id: UUID,
) -> Any:
    """
    删除课程计划。
    """
    course_plan = db.get(models.CoursePlan, course_plan_id)
    if not course_plan:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程计划",
        )

    db.delete(course_plan)
    db.commit()

    return {"detail": "课程计划已成功删除"}
