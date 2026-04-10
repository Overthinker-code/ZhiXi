from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app import models
from app.api import deps
from app.services.behavior_analysis import behavior_service
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
import base64

router = APIRouter()


class BehaviorAnalysisResult(BaseModel):
    """行为分析结果"""
    status: str
    behaviors: list[dict]
    overall_score: float
    learning_status: str
    timestamp: str


class VideoAnalysisResult(BaseModel):
    """视频分析结果"""
    status: str
    frame_analyses: list[dict]
    summary: dict
    video_info: dict


class CourseAnalysisRecord(BaseModel):
    """课程分析记录"""
    id: str
    course_id: str
    timestamp: str
    duration: float
    average_score: float
    overall_status: str
    behavior_statistics: dict


# 存储分析记录（临时用内存存储，后期可改用数据库）
analysis_records: list[dict] = []


@router.post("/analyze/image", response_model=BehaviorAnalysisResult)
async def analyze_image(
    *,
    file: UploadFile = File(...),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    分析单张图片中的学生行为
    """
    try:
        image_data = await file.read()
        result = await behavior_service.analyze_image(image_data)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return BehaviorAnalysisResult(
            status="success",
            behaviors=result["behaviors"],
            overall_score=result["overall_score"],
            learning_status=result["learning_status"],
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze/video", response_model=VideoAnalysisResult)
async def analyze_video(
    *,
    file: UploadFile = File(...),
    course_id: Optional[str] = Form(None),
    sample_interval: int = Form(30),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    分析视频中的学生行为
    - file: 视频文件
    - course_id: 可选，关联的课程ID
    - sample_interval: 采样间隔（帧数），默认30帧
    """
    try:
        video_data = await file.read()
        result = await behavior_service.analyze_video(video_data, sample_interval)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        # 保存分析记录
        if course_id and result.get("summary"):
            record = {
                "id": str(UUID(int=len(analysis_records))),
                "course_id": course_id,
                "timestamp": datetime.now().isoformat(),
                "duration": result["video_info"]["duration"],
                "average_score": result["summary"]["average_score"],
                "overall_status": result["summary"]["overall_status"],
                "behavior_statistics": result["summary"]["behavior_statistics"],
                "key_moments": result["summary"].get("key_moments", []),
            }
            analysis_records.append(record)
        
        return VideoAnalysisResult(
            status="success",
            frame_analyses=result["frame_analyses"],
            summary=result["summary"],
            video_info=result["video_info"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"视频分析失败: {str(e)}")


@router.get("/records")
def get_analysis_records(
    *,
    course_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取历史分析记录
    """
    records = analysis_records
    
    if course_id:
        records = [r for r in records if r["course_id"] == course_id]
    
    # 按时间倒序
    records = sorted(records, key=lambda x: x["timestamp"], reverse=True)
    
    total = len(records)
    records = records[skip : skip + limit]
    
    return {"data": records, "total": total}


@router.get("/records/{record_id}")
def get_analysis_record_detail(
    *,
    record_id: str,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取单个分析记录详情
    """
    for record in analysis_records:
        if record["id"] == record_id:
            return record
    
    raise HTTPException(status_code=404, detail="未找到分析记录")


@router.get("/statistics/{course_id}")
def get_course_behavior_statistics(
    *,
    course_id: str,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取课程的行为统计汇总
    """
    course_records = [r for r in analysis_records if r["course_id"] == course_id]
    
    if not course_records:
        return {
            "course_id": course_id,
            "analysis_count": 0,
            "average_score": 0,
            "behavior_distribution": {},
            "message": "暂无分析数据",
        }
    
    # 计算平均分
    avg_score = sum(r["average_score"] for r in course_records) / len(course_records)
    
    # 汇总行为统计
    behavior_stats = {}
    for record in course_records:
        for behavior, stats in record.get("behavior_statistics", {}).items():
            if behavior not in behavior_stats:
                behavior_stats[behavior] = {"count": 0, "duration": 0}
            behavior_stats[behavior]["count"] += stats.get("count", 0)
            behavior_stats[behavior]["duration"] += stats.get("duration", 0)
    
    return {
        "course_id": course_id,
        "analysis_count": len(course_records),
        "average_score": round(avg_score, 2),
        "behavior_distribution": behavior_stats,
        "recent_records": course_records[:5],
    }


@router.post("/realtime/start")
async def start_realtime_analysis(
    *,
    course_id: str = Form(...),
    camera_id: Optional[str] = Form(None),
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    启动实时行为分析（用于课堂直播监控）
    """
    # 这里可以实现 WebSocket 或长轮询的实时分析
    # 简化版本返回分析会话ID
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{course_id}"
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": "实时分析已启动",
        "camera_id": camera_id,
        "course_id": course_id,
    }


@router.get("/behaviors/definitions")
def get_behavior_definitions(
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取支持的行为类型定义
    """
    return {
        "behaviors": [
            {
                "id": 0,
                "name": "专注学习",
                "score": 1.0,
                "description": "学习状态良好",
                "color": "#52c41a",
            },
            {
                "id": 1,
                "name": "查看手机",
                "score": -0.5,
                "description": "注意力分散",
                "color": "#faad14",
            },
            {
                "id": 2,
                "name": "与他人交谈",
                "score": -0.3,
                "description": "可能影响他人学习",
                "color": "#fa8c16",
            },
            {
                "id": 3,
                "name": "睡觉",
                "score": -1.0,
                "description": "未在学习",
                "color": "#f5222d",
            },
            {
                "id": 4,
                "name": "离开座位",
                "score": -0.8,
                "description": "未在学习区域",
                "color": "#eb2f96",
            },
        ],
        "score_ranges": [
            {"min": 0.7, "max": 1.0, "status": "学习状态优秀", "color": "#52c41a"},
            {"min": 0.3, "max": 0.7, "status": "学习状态良好", "color": "#1890ff"},
            {"min": -0.3, "max": 0.3, "status": "学习状态一般", "color": "#faad14"},
            {"min": -0.7, "max": -0.3, "status": "学习状态较差", "color": "#fa541c"},
            {"min": -1.0, "max": -0.7, "status": "学习状态极差", "color": "#f5222d"},
        ],
    }
