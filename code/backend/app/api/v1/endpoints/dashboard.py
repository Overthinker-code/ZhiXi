from typing import Optional, List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func
from sqlalchemy import and_, desc

from uuid import UUID

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
    ).one_or_none() or 0
    
    # 统计总课程数
    total_courses = db.exec(select(func.count(Course.id))).one_or_none() or 0
    
    # 统计总资源数（Resource + Video）
    total_resources = db.exec(select(func.count(Resource.id))).one_or_none() or 0
    total_videos = db.exec(select(func.count(Video.id))).one_or_none() or 0
    
    # 统计总教师数
    total_teachers = db.exec(select(func.count(Teacher.id))).one_or_none() or 0

    # 统计总教学班数
    total_teaching_classes = db.exec(select(func.count(TC.id))).one_or_none() or 0
    
    # 统计活跃学生数（统计参加教学班的学生数，不重复计算）
    active_students = db.exec(
        select(func.count(func.distinct(StudentTC.student_id))).where(
            StudentTC.tc_id.isnot(None)
        )
    ).one_or_none() or 0
    
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
        ).one_or_none() or 0
        
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
    resources_count = db.exec(select(func.count(Resource.id))).one_or_none() or 0
    courses_count = db.exec(select(func.count(Course.id))).one_or_none() or 0
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


# ==================== 教育学参数联动6：课程质量评估 ====================

@router.get("/teacher/course-engagement/{course_id}")
def dashboard_course_engagement(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    course_id: str,
    days: int = Query(30, ge=1, le=90),
) -> dict:
    """
    获取课程质量评估数据（LEI趋势、布鲁姆分布、认知状态变化）
    
    参数：
    - course_id: 课程ID
    - days: 查询最近N天（default=30）
    
    返回：课程参与度时序数据与综合评估
    """
    # 将字符串course_id转换为UUID以兼容PostgreSQL
    try:
        course_uuid = UUID(course_id)
    except ValueError:
        course_uuid = None
    if course_uuid is None:
        return {
            "course_id": course_id,
            "days": days,
            "session_count": 0,
            "message": "暂无课堂评估数据",
            "lei_trend": [],
            "bloom_evolution": [],
            "suggestions": ["请上传课堂视频进行分析以生成评估数据"],
        }
    try:
        from app.models import CourseEngagementRecord
        import json
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        records = db.exec(
            select(CourseEngagementRecord)
            .where(
                CourseEngagementRecord.course_id == course_uuid,
                CourseEngagementRecord.session_date >= start_date
            )
            .order_by(CourseEngagementRecord.session_date.asc())
        ).all()
        
        if not records:
            return {
                "course_id": course_id,
                "days": days,
                "session_count": 0,
                "message": "暂无课堂评估数据",
                "lei_trend": [],
                "bloom_evolution": [],
                "suggestions": ["请上传课堂视频进行分析以生成评估数据"],
            }
        
        # 组装LEI趋势数据
        lei_trend = []
        for r in records:
            entry = {
                "date": r.session_date.isoformat(),
                "lei": round(r.avg_lei or 0.0, 3),
                "cognitive_depth": round(r.avg_cognitive_depth or 0.0, 3),
                "mind_wandering_rate": round(r.mind_wandering_rate or 0.0, 3),
                "student_count": r.student_count or 0,
            }
            # 解析时序数据
            if r.lei_timeline:
                try:
                    timeline = json.loads(r.lei_timeline)
                    entry["timeline"] = timeline
                except Exception:
                    pass
            lei_trend.append(entry)
        
        # 布鲁姆层次演进
        bloom_evolution = []
        for r in records:
            if r.bloom_distribution:
                try:
                    bd = json.loads(r.bloom_distribution)
                    bloom_evolution.append({
                        "date": r.session_date.isoformat(),
                        "distribution": bd,
                    })
                except Exception:
                    pass
        
        # 综合评估与建议
        avg_lei = sum(r.avg_lei or 0.0 for r in records) / len(records)
        avg_depth = sum(r.avg_cognitive_depth or 0.0 for r in records) / len(records)
        avg_mw = sum(r.mind_wandering_rate or 0.0 for r in records) / len(records)
        
        suggestions = []
        if avg_lei >= 0.75:
            suggestions.append(f"课堂整体投入度优秀(平均LEI={avg_lei:.2f})，教学节奏适宜。")
        elif avg_lei >= 0.55:
            suggestions.append(f"课堂投入度良好(平均LEI={avg_lei:.2f})，建议维持当前策略并适当增加互动。")
        else:
            suggestions.append(f"课堂投入度偏低(平均LEI={avg_lei:.2f})，建议检查教学内容难度或增加认知唤醒活动。")
        
        if avg_depth < 0.55:
            suggestions.append("学生认知活动多停留在低阶思维，建议设计更多应用/分析类任务以促进深度学习。")
        elif avg_depth > 0.80:
            suggestions.append("学生处于高认知投入状态，注意控制认知负荷避免过度消耗。")
        
        if avg_mw > 0.25:
            suggestions.append(f"走神率较高({avg_mw:.1%})，建议将连续讲授拆分为15-20分钟模块，中间穿插互动。")
        
        # 趋势判断
        if len(lei_trend) >= 2:
            first_lei = lei_trend[0]["lei"]
            last_lei = lei_trend[-1]["lei"]
            if last_lei > first_lei + 0.1:
                trend_direction = "上升"
            elif last_lei < first_lei - 0.1:
                trend_direction = "下降"
            else:
                trend_direction = "平稳"
        else:
            trend_direction = "未知"
        
        return {
            "course_id": course_id,
            "days": days,
            "session_count": len(records),
            "avg_lei": round(avg_lei, 3),
            "avg_cognitive_depth": round(avg_depth, 3),
            "avg_mind_wandering_rate": round(avg_mw, 3),
            "trend_direction": trend_direction,
            "lei_trend": lei_trend,
            "bloom_evolution": bloom_evolution,
            "suggestions": suggestions,
        }
        
    except Exception as e:
        # 模块未就绪时返回友好提示
        return {
            "course_id": course_id,
            "days": days,
            "session_count": 0,
            "message": f"课程评估模块初始化中: {str(e)}",
            "lei_trend": [],
            "bloom_evolution": [],
            "suggestions": [],
        }


@router.get("/teacher/student-engagement/{student_id}")
def dashboard_student_engagement(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
    student_id: str,
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    """
    获取单个学生的课堂学习投入历史
    
    用于：学生画像、教师个别关注、家长报告
    """
    # 将字符串student_id转换为UUID以兼容PostgreSQL
    try:
        student_uuid = UUID(student_id)
    except ValueError:
        student_uuid = None
    if student_uuid is None:
        return {
            "student_id": student_id,
            "session_count": 0,
            "message": "暂无该学生的课堂行为数据",
            "sessions": [],
        }
    try:
        from app.models import BehaviorSummaryRecord
        import json
        
        records = db.exec(
            select(BehaviorSummaryRecord)
            .where(BehaviorSummaryRecord.student_id == student_uuid)
            .order_by(desc(BehaviorSummaryRecord.session_date))
            .limit(limit)
        ).all()
        
        if not records:
            return {
                "student_id": student_id,
                "session_count": 0,
                "message": "暂无该学生的课堂行为数据",
                "sessions": [],
            }
        
        sessions = []
        for r in records:
            entry = {
                "date": r.session_date.isoformat(),
                "lei": round(r.avg_lei or 0.0, 3),
                "cognitive_depth": round(r.avg_cognitive_depth or 0.0, 3),
                "mind_wandering_rate": round(r.mind_wandering_rate or 0.0, 3),
                "on_task_rate": round(r.on_task_rate or 0.0, 3),
                "contagion_index": round(r.contagion_index or 0.0, 3),
            }
            if r.bloom_distribution:
                try:
                    entry["bloom_distribution"] = json.loads(r.bloom_distribution)
                except Exception:
                    pass
            if r.cognitive_state_distribution:
                try:
                    entry["cognitive_state_distribution"] = json.loads(r.cognitive_state_distribution)
                except Exception:
                    pass
            sessions.append(entry)
        
        # 计算长期趋势
        avg_lei = sum(s["lei"] for s in sessions) / len(sessions) if sessions else 0.0
        avg_mw = sum(s["mind_wandering_rate"] for s in sessions) / len(sessions) if sessions else 0.0
        
        trend = "稳定"
        if len(sessions) >= 3:
            recent = sum(s["lei"] for s in sessions[:3]) / 3
            older = sum(s["lei"] for s in sessions[-3:]) / 3
            if recent > older + 0.1:
                trend = "改善"
            elif recent < older - 0.1:
                trend = "下滑"
        
        return {
            "student_id": student_id,
            "session_count": len(records),
            "avg_lei": round(avg_lei, 3),
            "avg_mind_wandering_rate": round(avg_mw, 3),
            "trend": trend,
            "sessions": sessions,
        }
        
    except Exception as e:
        return {
            "student_id": student_id,
            "session_count": 0,
            "message": f"学生投入度模块初始化中: {str(e)}",
            "sessions": [],
        }
