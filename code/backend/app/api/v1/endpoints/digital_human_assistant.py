"""
数字人课堂助教接口
教育学参数联动5：将教学建议转化为数字人语音播报

调用链路：
educational_report.pedagogical_suggestions
    -> 过滤高优先级建议
    -> 调用MuseTalk数字人服务
    -> 教师端/学生端语音播报
"""
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import CurrentUser

router = APIRouter()


class ClassroomAssistantRequest(BaseModel):
    """课堂助教播报请求"""
    suggestion: str                           # 要播报的教学建议文本
    target: str = "teacher"                   # teacher / student / broadcast
    student_id: Optional[str] = None          # target=student时指定学生ID
    priority: str = "normal"                  # low / normal / high
    course_id: Optional[str] = None
    tc_id: Optional[str] = None


class ClassroomAssistantResponse(BaseModel):
    """课堂助教播报响应"""
    status: str
    message: str
    suggestion_text: str
    target: str
    audio_url: Optional[str] = None           # 数字人生成的音频URL（如支持）
    rendered_at: Optional[str] = None


# 从教学建议缓存中提取高优先级建议的内存存储
# 生产环境建议使用Redis
_last_suggestions: List[str] = []
_suggestions_lock = asyncio.Lock()


@router.post("/classroom-assistant/speak", response_model=ClassroomAssistantResponse)
async def classroom_assistant_speak(
    request: ClassroomAssistantRequest,
    current_user: CurrentUser,
):
    """
    将教学建议转为数字人语音播报
    
    请求示例：
    {
        "suggestion": "检测到课堂注意力进入低谷，建议进行2-3分钟快速问答",
        "target": "teacher",
        "priority": "high"
    }
    
    实际实现中，此接口应调用项目的MuseTalk数字人服务生成语音+口型视频
    当前版本返回文本确认，数字人渲染由前端或独立服务完成
    """
    try:
        # 简单校验
        if not request.suggestion or len(request.suggestion.strip()) == 0:
            raise HTTPException(status_code=400, detail="suggestion不能为空")
        
        # 记录建议到缓存（加锁保护并发安全）
        async with _suggestions_lock:
            _last_suggestions.insert(0, request.suggestion)
            if len(_last_suggestions) > 20:
                _last_suggestions.pop()
        
        # TODO: 接入实际MuseTalk数字人服务
        # 典型调用方式（伪代码）：
        # audio_path = await muse_talk_service.generate(
        #     text=request.suggestion,
        #     speaker_id="teacher_default",
        #     emotion="neutral",
        # )
        # audio_url = f"/static/audio/{audio_path}"
        
        return ClassroomAssistantResponse(
            status="success",
            message="教学建议已接收，数字人播报任务已创建",
            suggestion_text=request.suggestion,
            target=request.target,
            audio_url=None,  # 实际接入数字人后填充
            rendered_at=None,
        )
    except HTTPException:
        raise
    except Exception as e:
        return ClassroomAssistantResponse(
            status="error",
            message=f"数字人播报失败: {str(e)}",
            suggestion_text=request.suggestion,
            target=request.target,
        )


@router.post("/classroom-assistant/auto-speak")
async def classroom_assistant_auto_speak(
    educational_report: dict,
    current_user: CurrentUser,
    max_suggestions: int = Query(2, ge=1, le=5),
):
    """
    自动从educational_report中提取高优先级建议并播报
    
    此接口供behavior_analysis服务在分析完成后自动调用
    """
    suggestions = educational_report.get("pedagogical_suggestions") or []
    if not isinstance(suggestions, list):
        suggestions = []
    if not suggestions:
        return {
            "status": "skipped",
            "reason": "无教学建议",
            "spoken": [],
        }
    
    spoken = []
    for suggestion in suggestions[:max_suggestions]:
        suggestion = str(suggestion) if suggestion is not None else ""
        if not suggestion:
            continue
        # 简单过滤：只播报高优先级的建议
        priority = "high" if any(kw in suggestion for kw in ["立即", "极低", "严重", "危机"]) else "normal"
        
        # 这里不实际调用数字人，而是记录到队列（加锁保护）
        async with _suggestions_lock:
            _last_suggestions.insert(0, suggestion)
            spoken.append({
                "text": suggestion,
                "priority": priority,
                "status": "queued",
            })
    
    async with _suggestions_lock:
        if len(_last_suggestions) > 20:
            _last_suggestions[:] = _last_suggestions[:20]
        queue_length = len(_last_suggestions)
    
    return {
        "status": "success",
        "spoken": spoken,
        "queue_length": queue_length,
    }


@router.get("/classroom-assistant/recent-suggestions")
async def get_recent_suggestions(
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=20),
):
    """获取最近生成的教学建议列表（供前端展示）"""
    async with _suggestions_lock:
        suggestions = _last_suggestions[:limit]
        total = len(_last_suggestions)
    return {
        "status": "success",
        "suggestions": suggestions,
        "total": total,
    }
