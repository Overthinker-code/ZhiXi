from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from sqlalchemy import and_

from app.api import deps
from app.models import User, Course, Resource, Video, Log, Alert, TC, StudentTC, Teacher

router = APIRouter()


POPULAR_DEMO_MAP = {
    "discussion": [
        {
            "key": 1,
            "title": "事务隔离级别课堂讨论",
            "click_number": 268,
            "increases": 16,
        },
        {
            "key": 2,
            "title": "大模型落地应用交流",
            "click_number": 231,
            "increases": 12,
        },
        {
            "key": 3,
            "title": "树与图算法答疑串",
            "click_number": 198,
            "increases": 9,
        },
    ],
    "homework": [
        {
            "key": 1,
            "title": "数据库范式设计作业",
            "click_number": 642,
            "increases": 18,
        },
        {
            "key": 2,
            "title": "数据结构周测练习",
            "click_number": 588,
            "increases": 13,
        },
        {
            "key": 3,
            "title": "AI 应用场景分析报告",
            "click_number": 521,
            "increases": 11,
        },
    ],
}


@router.get("/teacher/stats")
def dashboard_teacher_stats(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """
    获取教师 Dashboard 统计数据
    
    返回：
    - today_login_count: 今天登录人数
    - total_courses: 总课程数
    - total_resources: 总资源数
    - total_teaching_classes: 总教学班数
    - active_students: 活跃学生数
    """
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(tomorrow, datetime.min.time())
    
    # 统计今天登录人数（不重复计算同一用户多次登录）
    today_logins = db.exec(
        select(func.count(func.distinct(Log.user_id))).where(
            and_(
                Log.action == "login",
                Log.created_at >= today_start,
                Log.created_at < today_end
            )
        )
    ).one()
    
    # 统计总课程数
    total_courses = db.exec(select(func.count(Course.id))).one()
    
    # 统计总资源数（Resource + Video）
    total_resources = db.exec(select(func.count(Resource.id))).one()
    total_videos = db.exec(select(func.count(Video.id))).one()
    
    # 统计总教师数
    total_teachers = db.exec(select(func.count(Teacher.id))).one()

    # 统计总教学班数
    total_teaching_classes = db.exec(select(func.count(TC.id))).one()
    
    # 统计活跃学生数（统计参加教学班的学生数，不重复计算）
    active_students = db.exec(
        select(func.count(func.distinct(StudentTC.student_id))).where(
            StudentTC.tc_id.isnot(None)
        )
    ).one() or 0
    
    return {
        "today_login_count": today_logins or 0,
        "total_courses": total_courses or 0,
        "total_resources": (total_resources or 0) + (total_videos or 0),
        "total_teachers": total_teachers or 0,
        "total_teaching_classes": total_teaching_classes or 0,
        "active_students": active_students or 0,
        # 兼容旧版前端字段，避免已部署页面出现 undefined / NaN
        "total_classes": total_teaching_classes or total_courses or 0,
    }


@router.get("/teacher/alerts-trend")
def dashboard_teacher_alerts_trend(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    days: int = Query(7, ge=1, le=30),
) -> List[dict]:
    """
    获取近 N 天告警趋势
    
    参数：
    - days: 天数（default=7）
    
    返回：每天的告警数量
    """
    result = []
    for i in range(days - 1, -1, -1):
        date = datetime.utcnow().date() - timedelta(days=i)
        date_start = datetime.combine(date, datetime.min.time())
        date_end = datetime.combine(date + timedelta(days=1), datetime.min.time())
        
        alert_count = db.exec(
            select(func.count(Alert.id)).where(
                and_(
                    Alert.alert_time >= date_start,
                    Alert.alert_time < date_end
                )
            )
        ).one() or 0
        
        result.append({
            "date": date.isoformat(),
            "alert_count": alert_count
        })
    
    return result


@router.get("/teacher/popular")
def dashboard_teacher_popular(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    type: str = Query("course"),
    limit: int = Query(3, ge=1, le=10),
) -> List[dict]:
    """
    获取热门内容
    
    参数：
    - type: 类型 (course, resource, video)
    - limit: 返回个数 (default=3)
    
    返回：热门内容列表
    """
    result = []
    
    if type == "course":
        # 按 click_number 降序排列
        courses = db.exec(
            select(Course)
            .order_by(Course.click_number.desc())
            .limit(limit)
        ).all()
        
        for idx, course in enumerate(courses, 1):
            result.append({
                "key": idx,
                "title": course.name,
                "click_number": course.click_number,
                "increases": max(0, course.click_number // 100)  # 估算增长值
            })
    elif type == "resource":
        # 资源暂无 click_number，使用 mock 数据
        resources = db.exec(
            select(Resource)
            .limit(limit)
        ).all()
        
        for idx, resource in enumerate(resources, 1):
            result.append({
                "key": idx,
                "title": resource.title,
                "click_number": 0,
                "increases": 0
            })
    elif type == "video":
        # 视频暂无 click_number，使用 mock 数据
        videos = db.exec(
            select(Video)
            .limit(limit)
        ).all()
        
        for idx, video in enumerate(videos, 1):
            result.append({
                "key": idx,
                "title": video.title,
                "click_number": 0,
                "increases": 0
            })
    elif type in POPULAR_DEMO_MAP:
        result = POPULAR_DEMO_MAP[type][:limit]

    # 如果结果为空，返回示例数据
    if not result:
        result = [
            {
                "key": 1,
                "title": "示例课程",
                "click_number": 1820,
                "increases": 14,
            }
        ]
    
    return result


@router.get("/teacher/content-distribution")
def dashboard_teacher_content_distribution(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> dict:
    """
    获取内容分布
    
    返回：各类型内容的数量分布
    """
    resources_count = db.exec(select(func.count(Resource.id))).one() or 0
    courses_count = db.exec(select(func.count(Course.id))).one() or 0
    # TODO: 需要添加 homework 和 discussions 模型，暂时使用 0
    homework_count = 0
    discussions_count = 0
    
    total = resources_count + courses_count + homework_count + discussions_count
    
    return {
        "total": total,
        "items": [
            {"name": "resources", "value": resources_count},
            {"name": "courses", "value": courses_count},
            {"name": "homework", "value": homework_count},
            {"name": "discussions", "value": discussions_count},
        ]
    }
