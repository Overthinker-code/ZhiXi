import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session

from app import models
from app.api import deps
from app.core import security
from app.core.db import engine
from app.services.behavior_analysis import behavior_service
from app.services.behavior_ws import behavior_ws_service, FrameMessage
from app.models import TokenPayload

router = APIRouter()


class PersonResult(BaseModel):
    """单个人员检测结果"""
    id: int
    bbox: list[float]  # [x1, y1, x2, y2]
    behavior: str
    confidence: float
    score: float
    color: str
    reason: str | None = None
    track_id: str | None = None
    raw_behavior: str | None = None
    detection_confidence: float | None = None
    behavior_confidence: float | None = None
    pose_quality: float | None = None
    bbox_quality: float | None = None
    temporal_stability: float | None = None
    temporal_volatility: float | None = None


class BehaviorAnalysisResult(BaseModel):
    """行为分析结果"""
    status: str
    behaviors: list[dict]
    persons: list[PersonResult]
    overall_score: float
    learning_status: str
    timestamp: str
    image_width: int = 0
    image_height: int = 0
    classroom_metrics: dict = {}


class VideoAnalysisResult(BaseModel):
    """视频分析结果"""
    status: str
    frame_analyses: list[dict] = []
    summary: dict = {}
    video_info: dict = {}
    persons: list[PersonResult] = []  # 添加人员检测数据
    classroom_metrics: dict = {}


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
            persons=result.get("persons", []),
            overall_score=result["overall_score"],
            learning_status=result["learning_status"],
            timestamp=datetime.now().isoformat(),
            image_width=result.get("image_width", 0),
            image_height=result.get("image_height", 0),
            classroom_metrics=result.get("classroom_metrics", {}),
        )
    except HTTPException:
        raise
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
                "id": str(uuid4()),
                "course_id": course_id,
                "timestamp": datetime.now().isoformat(),
                "duration": result.get("video_info", {}).get("duration", 0),
                "average_score": result.get("summary", {}).get("average_score", 0),
                "overall_status": result.get("summary", {}).get("overall_status", "无法评估"),
                "behavior_statistics": result.get("summary", {}).get("behavior_statistics", {}),
                "key_moments": result["summary"].get("key_moments", []),
            }
            analysis_records.append(record)

        return VideoAnalysisResult(
            status="success",
            frame_analyses=result.get("frame_analyses", []),
            summary=result.get("summary", {}),
            video_info=result.get("video_info", {}),
            persons=result.get("persons", []),
            classroom_metrics=result.get("classroom_metrics", {}),
        )
    except HTTPException:
        raise
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


@router.get("/cameras")
def get_classroom_cameras(
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取各课堂对应的远程摄像头地址列表
    ============================================================================
    【手动配置区域】如需新增/修改教室摄像头地址，请直接编辑下方 return 语句。
    生产环境建议改为从数据库或环境变量读取。
    格式支持：HTTP / MJPEG / FLV / HLS(m3u8)
    示例：{"id": "db", "cameraUrl": "http://192.168.1.101:8080/video"}
    ============================================================================
    """
    return {
        "cameras": [
            {"id": "db", "cameraUrl": "http://192.168.1.101:8080/video"},
            {"id": "ds", "cameraUrl": "http://192.168.1.102:8080/video"},
            {"id": "ai", "cameraUrl": "http://192.168.1.103:8080/video"},
            {"id": "eco", "cameraUrl": "http://192.168.1.104:8080/video"},
        ]
    }


@router.get("/behaviors/definitions")
async def get_behavior_definitions(
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    获取支持的行为类型定义（从 YOLO 服务转发，确保前后端定义一致）
    """
    return await behavior_service.get_behavior_definitions()


# ---------------------------------------------------------------------------
# WebSocket 实时行为检测接口
# 后端2 —— 张伟杰
# 路径: WS /api/v1/behavior/ws/realtime?course_id=<uuid>&token=<jwt>
# ---------------------------------------------------------------------------

async def _verify_ws_token(token: str) -> Optional[models.User]:
    """验证 WebSocket 连接中的 JWT Token"""
    payload = security.decode_access_token(token)
    if not payload:
        return None
    try:
        token_data = TokenPayload(**payload)
    except Exception:
        return None
    with Session(engine) as session:
        user = session.get(models.User, token_data.sub)
        if user and user.is_active:
            return user
    return None


@router.websocket("/ws/realtime")
async def behavior_realtime_ws(
    websocket: WebSocket,
    course_id: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
):
    """
    WebSocket 实时行为分析通道。

    前端发送：
    {
        "type": "frame",
        "frame_id": 101,
        "timestamp": 1713580000,
        "image_base64": "data:image/jpeg;base64,..."
    }

    后端返回：
    {
        "type": "analysis",
        "frame_id": 101,
        "timestamp": 1713580000,
        "persons": [
            {
                "track_id": "person_1",
                "bbox": [120, 80, 260, 320],
                "status": "focused",
                "score": 0.92
            }
        ],
        "summary": {
            "focused_count": 18,
            "unfocused_count": 4,
            "absent_count": 2
        }
    }
    """
    if not token:
        await websocket.close(code=4401, reason="Missing token")
        return
    user = await _verify_ws_token(token)
    if user is None:
        await websocket.close(code=4401, reason="Invalid token")
        return

    await websocket.accept()

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg_dict = json.loads(raw_msg)
                frame_msg = FrameMessage.model_validate(msg_dict)
            except (json.JSONDecodeError, Exception) as e:
                await websocket.send_json(
                    {"type": "error", "detail": f"Invalid frame message: {str(e)}"}
                )
                continue

            # 实时课堂优先调用 YOLO 姿态检测服务；不可用时保留原本地 CV 降级链路。
            result = await behavior_service.analyze_realtime_frame(
                frame_msg.image_base64,
                frame_msg.frame_id,
            )
            if result is None:
                result = behavior_ws_service.analyze_frame(
                    frame_msg.image_base64, frame_msg.frame_id
                )
            await websocket.send_json(result.model_dump())

    except WebSocketDisconnect:
        # 正常断开，无需处理
        pass
    except Exception as e:
        # 连接异常时尝试发送错误信息后关闭
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
            await websocket.close()
        except Exception:
            pass
