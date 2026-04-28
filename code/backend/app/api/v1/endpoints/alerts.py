import asyncio
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime
from sqlmodel import Session

from app.api.deps import CurrentUser
from app.core.security import verify_token_from_query
from app.core.db import engine

# 教育学参数联动3：真实预警
try:
    from app.services.alert_rule_engine import alert_rule_engine, AlertEvent as EngineAlertEvent
    from app.services.behavior_analysis import behavior_service
    ALERT_ENGINE_AVAILABLE = True
except ImportError:
    ALERT_ENGINE_AVAILABLE = False

router = APIRouter()


class AlertEvent:
    def __init__(
        self,
        alert_id: str,
        student_id: str,
        alert_time: str,
        reason: str,
        severity: str,
        student_name: Optional[str] = None,
    ):
        self.id = alert_id
        self.student_id = student_id
        self.alert_time = alert_time
        self.reason = reason
        self.severity = severity
        self.student_name = student_name

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "alert_time": self.alert_time,
            "reason": self.reason,
            "severity": self.severity,
            "student_name": self.student_name,
            "alert_type": "unknown",
            "resolved": False,
        }


def generate_real_alert(tc_id: str) -> Optional[AlertEvent]:
    """
    基于真实课堂行为数据生成预警（教育学参数联动3）
    如果edu_analyzer不可用，回退到mock数据
    """
    import uuid
    import random
    
    # 尝试获取真实行为数据
    if ALERT_ENGINE_AVAILABLE:
        try:
            latest_report = getattr(behavior_service, '_last_educational_report', None)
            latest_profiles = getattr(behavior_service, '_last_person_profiles', {})
            
            if latest_report:
                alerts = alert_rule_engine.evaluate(
                    latest_report,
                    latest_profiles or {},
                )
                if alerts:
                    alert = alerts[0]  # 取最高优先级
                    # 同时持久化到数据库（供history查询）
                    try:
                        from app.models import StudentBehaviorAlert
                        from uuid import UUID
                        from app.core.db import engine
                        with Session(engine) as db_session:
                            db_alert = StudentBehaviorAlert(
                                id=UUID(alert.id),
                                student_id=UUID(alert.student_id) if alert.student_id else None,
                                tc_id=UUID(tc_id) if tc_id else None,
                                alert_time=datetime.fromisoformat(alert.alert_time),
                                reason=alert.reason,
                                severity=alert.severity,
                                alert_type=alert.alert_type,
                                trigger_lei=alert.trigger_metrics.get("lei"),
                                trigger_attention_deviation=alert.trigger_metrics.get("attention_deviation"),
                                trigger_contagion_index=alert.trigger_metrics.get("contagion_index"),
                            )
                            db_session.add(db_alert)
                            db_session.commit()
                    except Exception:
                        pass  # 持久化失败不应阻塞预警推送
                    return AlertEvent(
                        alert_id=alert.id,
                        student_id=alert.student_id or f"class-{tc_id}",
                        alert_time=alert.alert_time,
                        reason=alert.reason,
                        severity=alert.severity,
                        student_name=alert.student_name or ("课堂群体" if alert.student_id is None else alert.student_id),
                    )
        except Exception:
            pass
    
    # 回退到mock数据（保持原有行为）
    severities = ["low", "medium", "high"]
    reasons = [
        "学生连续5分钟未查看屏幕",
        "检测到学生使用手机",
        "学生注意力下降",
        "检测到学生离开座位",
        "学生频繁转头",
    ]
    student_names = ["张三", "李四", "王五", "赵六", "钱七"]
    
    return AlertEvent(
        alert_id=str(uuid.uuid4()),
        student_id=f"student-{random.randint(1, 100)}",
        alert_time=datetime.now().isoformat(),
        reason=random.choice(reasons),
        severity=random.choice(severities),
        student_name=random.choice(student_names),
    )


async def event_generator(tc_id: str, current_user: CurrentUser):
    """
    Generate SSE events for alerts.
    教育学参数联动3：优先使用真实行为数据生成预警
    """
    try:
        while True:
            alert = generate_real_alert(tc_id)
            if alert:
                event_data = json.dumps(alert.to_dict())
                yield f"data: {event_data}\n\n"
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass


@router.get("/stream")
async def stream_alerts(
    tc_id: str = Query(..., description="Teaching class ID"),
    token: str = Query(..., description="JWT token for authentication"),
):
    """
    Stream real-time alerts via Server-Sent Events (SSE).
    
    This endpoint pushes alerts to connected clients in real-time.
    The token is passed as a query parameter because EventSource 
    doesn't support custom headers.
    """
    current_user = verify_token_from_query(token)
    
    return StreamingResponse(
        event_generator(tc_id, current_user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
async def get_alert_history(
    tc_id: Optional[str] = Query(None, description="Teaching class ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
):
    """
    Get historical alerts for a teaching class.
    教育学参数联动3：优先返回真实预警记录
    """
    # 尝试从数据库读取真实预警
    try:
        from uuid import UUID
        from app.models import StudentBehaviorAlert
        try:
            tc_uuid = UUID(tc_id)
        except ValueError:
            tc_uuid = None
        with Session(engine) as session:
            query = session.query(StudentBehaviorAlert)
            if tc_uuid is not None:
                query = query.filter(StudentBehaviorAlert.tc_id == tc_uuid)
            db_alerts = (
                query.order_by(StudentBehaviorAlert.alert_time.desc())
                .limit(limit)
                .all()
            )
            if db_alerts:
                return {
                    "alerts": [
                        {
                            "id": str(a.id),
                            "student_id": str(a.student_id) if a.student_id else None,
                            "alert_time": a.alert_time.isoformat(),
                            "reason": a.reason,
                            "severity": a.severity,
                            "alert_type": a.alert_type,
                            "resolved": a.resolved,
                        }
                        for a in db_alerts
                    ]
                }
    except Exception:
        pass
    
    # 回退到mock数据
    mock_alerts = [generate_real_alert(tc_id).to_dict() for _ in range(min(limit, 10))]
    return {"alerts": mock_alerts}
