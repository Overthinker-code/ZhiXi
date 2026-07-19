from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, and_, or_

from app import models
from app.api import deps
from uuid import UUID
from app.services.knowledge_graph_service import can_access_course

router = APIRouter()


def _course_public(course: models.Course) -> models.CoursePublic:
    return models.CoursePublic.model_validate(course, from_attributes=True)


@router.get("/", response_model=models.CoursesPublic)
def read_courses(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 100,
    name: str = None,
    identifier: str = None,
    course_type: str = None,
    ud_id: UUID = None,
) -> Any:
    """
    获取课程列表。
    """
    query = select(models.Course)
    conditions = []

    if name:
        conditions.append(models.Course.name.contains(name))
    if identifier:
        conditions.append(models.Course.identifier.contains(identifier))
    if course_type:
        conditions.append(models.Course.course_type == course_type)
    if ud_id:
        conditions.append(models.Course.ud_id == ud_id)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.offset(skip).limit(limit)
    courses = db.exec(query).all()

    count_query = select(models.Course)
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total = len(db.exec(count_query).all())

    return models.CoursesPublic(
        data=[_course_public(course) for course in courses],
        count=total,
    )


@router.post("/", response_model=models.CoursePublic)
def create_course(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    course_in: models.CourseCreate,
) -> Any:
    """
    创建新课程。
    """
    # 检查UD是否存在
    ud = db.get(models.UD, course_in.ud_id)
    if not ud:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的大学-院系",
        )

    # 检查是否已存在相同标识符的课程
    query = select(models.Course).where(
        and_(
            models.Course.ud_id == course_in.ud_id,
            models.Course.identifier == course_in.identifier,
        )
    )
    existing_course = db.exec(query).first()
    if existing_course:
        raise HTTPException(
            status_code=400,
            detail="相同院系下已存在该课程标识符",
        )

    course = models.Course.from_orm(course_in)
    db.add(course)
    db.commit()
    db.refresh(course)

    return _course_public(course)


@router.get("/{course_id}", response_model=models.CoursePublic)
def read_course(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    course_id: UUID,
) -> Any:
    """
    通过ID获取课程信息。
    """
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程",
        )

    return _course_public(course)


@router.put("/{course_id}", response_model=models.CoursePublic)
def update_course(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    course_id: UUID,
    course_in: models.CourseUpdate,
) -> Any:
    """
    更新课程信息。
    """
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程",
        )

    # 如果要更新ud_id，检查UD是否存在
    if course_in.ud_id and course_in.ud_id != course.ud_id:
        ud = db.get(models.UD, course_in.ud_id)
        if not ud:
            raise HTTPException(
                status_code=404,
                detail="未找到指定的大学-院系",
            )

    # 如果要更新identifier或ud_id，检查组合是否已存在
    if (course_in.identifier and course_in.identifier != course.identifier) or (
        course_in.ud_id and course_in.ud_id != course.ud_id
    ):
        query = select(models.Course).where(
            and_(
                models.Course.ud_id == (course_in.ud_id or course.ud_id),
                models.Course.identifier == (course_in.identifier or course.identifier),
            )
        )
        existing_course = db.exec(query).first()
        if existing_course and existing_course.id != course_id:
            raise HTTPException(
                status_code=400,
                detail="相同院系下已存在该课程标识符",
            )

    course_data = course_in.dict(exclude_unset=True)
    for key, value in course_data.items():
        setattr(course, key, value)

    db.add(course)
    db.commit()
    db.refresh(course)

    return _course_public(course)


@router.delete("/{course_id}")
def delete_course(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
    course_id: UUID,
) -> Any:
    """
    删除课程。
    """
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程",
        )

    # 检查是否有关联的教学班
    query_tc = select(models.TC).where(models.TC.course_id == course_id)

    if db.exec(query_tc).first():
        raise HTTPException(
            status_code=400,
            detail="该课程存在关联的教学班，无法删除",
        )

    db.delete(course)
    db.commit()

    return {"detail": "课程已成功删除"}


@router.get("/by-name/", response_model=models.CoursePublic)
def get_course_by_name(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    name: str,
    ud_id: UUID = None,
) -> Any:
    """
    通过名称查找课程。
    """
    query = select(models.Course).where(models.Course.name == name)

    if ud_id:
        query = query.where(models.Course.ud_id == ud_id)

    course = db.exec(query).first()

    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程",
        )

    return course


@router.get("/{course_id}/resources/analysis")
def get_course_resources_analysis(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    course_id: UUID,
) -> Any:
    """
    获取课程资源分析数据。
    """
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(
            status_code=404,
            detail="未找到指定的课程",
        )

    import random
    return {
        "document_size": round(random.uniform(5.0, 15.0), 1),
        "document_count": random.randint(10000, 100000),
        "video_size": round(random.uniform(8.0, 20.0), 1),
        "video_count": random.randint(50, 300),
        "image_size": round(random.uniform(10.0, 25.0), 1),
        "image_count": random.randint(50, 200),
        "homework_count": random.randint(500, 3000),
    }


@router.get("/{course_id}/workspace")
def get_course_workspace(
    *,
    db: Any = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    course_id: UUID,
) -> Any:
    """返回课程壳层需要的教学班、计划、作业与资源聚合数据。"""
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="未找到指定的课程")
    if not can_access_course(db, user=current_user, course_id=course_id):
        raise HTTPException(status_code=404, detail="未找到指定的课程")

    teaching_classes = list(
        db.exec(select(models.TC).where(models.TC.course_id == course_id)).all()
    )
    tc_ids = [tc.id for tc in teaching_classes]
    plans = (
        list(
            db.exec(
                select(models.CoursePlan)
                .where(models.CoursePlan.tc_id.in_(tc_ids))
                .order_by(models.CoursePlan.week)
            ).all()
        )
        if tc_ids
        else []
    )
    assignments = list(
        db.exec(
            select(models.Assignment)
            .where(models.Assignment.course_id == course_id)
            .order_by(models.Assignment.due_date)
        ).all()
    )
    resources = list(
        db.exec(
            select(models.Resource).where(models.Resource.course_id == course_id)
        ).all()
    )

    return {
        "course": _course_public(course),
        "teaching_classes": teaching_classes,
        "course_plans": plans,
        "assignments": assignments,
        "resources": resources,
        "summary": {
            "teaching_class_count": len(teaching_classes),
            "plan_count": len(plans),
            "assignment_count": len(assignments),
            "resource_count": len(resources),
        },
    }
