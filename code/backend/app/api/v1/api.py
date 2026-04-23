from fastapi import APIRouter

from app.api.v1.endpoints import (
    users,
    chat,
    rag,
    file,
    dashboard_mock,
    dashboard,
    chat_threads,
    user_center_mock,
    alerts,
    learning_report,
    ai_metrics,
)

api_router = APIRouter()
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat_threads.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(file.router, prefix="/file", tags=["file"])
api_router.include_router(dashboard_mock.router, tags=["dashboard"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(user_center_mock.router, tags=["user-center"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(learning_report.router, prefix="/learning-report", tags=["learning-report"])
api_router.include_router(ai_metrics.router, prefix="/ai-metrics", tags=["ai-metrics"])
