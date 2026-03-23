import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.api.deps import CurrentUser
from app.core.security import verify_token_from_query

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
        }


def generate_mock_alert(tc_id: str) -> AlertEvent:
    import uuid
    import random
    
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
    In production, this would connect to a real alert source (e.g., YOLO analysis).
    """
    try:
        while True:
            alert = generate_mock_alert(tc_id)
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
    tc_id: str = Query(..., description="Teaching class ID"),
    limit: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = None,
):
    """
    Get historical alerts for a teaching class.
    """
    mock_alerts = [generate_mock_alert(tc_id).to_dict() for _ in range(min(limit, 10))]
    return {"alerts": mock_alerts}
