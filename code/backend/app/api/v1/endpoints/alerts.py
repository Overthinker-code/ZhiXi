import asyncio
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from datetime import datetime
from sqlmodel import Session, select

from app.api.deps import CurrentUser, SessionDep, get_optional_current_user
from app.core.security import verify_token_from_query
from app.models import Student, StudentTC, TC, User

# 教育学参数联动3：真实预警
try:
    from app.services.alert_rule_engine import alert_rule_engine, AlertEvent as EngineAlertEvent
    from app.services.behavior_analysis import behavior_service
    ALERT_ENGINE_AVAILABLE = True
except ImportError:
    ALERT_ENGINE_AVAILABLE = False

router = APIRouter()


def _require_tc_access(session: Session, *, user: User, tc_id: UUID) -> TC:
    """Enforce object-level access for a concrete teaching class."""

    teaching_class = session.get(TC, tc_id)
    if teaching_class is None:
        raise HTTPException(status_code=404, detail="Teaching class not found")
    if user.is_superuser:
        return teaching_class
    enrolled = session.exec(
        select(StudentTC.id)
        .join(Student, Student.id == StudentTC.student_id)
        .where(Student.user_id == user.id, StudentTC.tc_id == tc_id)
        .limit(1)
    ).first()
    if enrolled is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teaching class access denied",
        )
    return teaching_class


def _resolve_stream_user(
    session: Session,
    *,
    header_user: User | None,
    query_token: str | None,
) -> tuple[User, bool]:
    """Prefer Authorization and retain query JWT only as deprecated fallback."""

    if header_user is not None:
        return header_user, False
    if not query_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    subject = verify_token_from_query(query_token)
    try:
        user_id = UUID(str(subject))
    except (TypeError, ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return user, True


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


async def event_generator(tc_id: UUID, current_user: User):
    """
    Generate SSE events for alerts.
    教育学参数联动3：优先使用真实行为数据生成预警
    """
    try:
        while True:
            alert = generate_real_alert(str(tc_id))
            if alert:
                event_data = json.dumps(alert.to_dict())
                yield f"data: {event_data}\n\n"
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass


@router.get("/stream")
async def stream_alerts(
    session: SessionDep,
    tc_id: UUID = Query(..., description="Teaching class ID"),
    token: str | None = Query(
        default=None,
        description="Deprecated JWT fallback; use Authorization header",
        deprecated=True,
    ),
    current_user: User | None = Depends(get_optional_current_user),
):
    """
    Stream real-time alerts via Server-Sent Events (SSE).
    
    This endpoint pushes alerts to connected clients in real-time.
    The token is passed as a query parameter because EventSource 
    doesn't support custom headers.
    """
    resolved_user, query_token_used = _resolve_stream_user(
        session,
        header_user=current_user,
        query_token=token,
    )
    _require_tc_access(session, user=resolved_user, tc_id=tc_id)
    headers = {
        "Cache-Control": "no-cache, no-store",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "Referrer-Policy": "no-referrer",
    }
    if query_token_used:
        headers.update(
            {
                "Deprecation": "true",
                "Warning": '299 - "Query token authentication is deprecated; use Authorization header"',
            }
        )
    return StreamingResponse(
        event_generator(tc_id, resolved_user),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get("/history")
async def get_alert_history(
    session: SessionDep,
    current_user: CurrentUser,
    tc_id: UUID = Query(..., description="Teaching class ID"),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Get historical alerts for a teaching class.
    教育学参数联动3：优先返回真实预警记录
    """
    _require_tc_access(session, user=current_user, tc_id=tc_id)
    # 尝试从数据库读取真实预警
    try:
        from app.models import StudentBehaviorAlert
        db_alerts = session.exec(
            select(StudentBehaviorAlert)
            .where(StudentBehaviorAlert.tc_id == tc_id)
            .order_by(StudentBehaviorAlert.alert_time.desc())
            .limit(limit)
        ).all()
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
    mock_alerts = [
        generate_real_alert(str(tc_id)).to_dict() for _ in range(min(limit, 10))
    ]
    return {"alerts": mock_alerts}
