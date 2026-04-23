from fastapi import APIRouter

# from app.api.routes import items, login, private, users, utils
from app.api.routes import (
    login,
    private,
    users,
    education,
    behavior_analysis,
    digital_human,
)
from app.api.v1.endpoints import (
    chat,
    rag,
    chat_threads,
    dashboard_mock,
    user_center_mock,
    health,
    learning_report,
    ai_metrics,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(education.router, prefix="/education", tags=["education"])
api_router.include_router(chat_threads.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(
    digital_human.router, prefix="/digital-human", tags=["digital-human"]
)
api_router.include_router(dashboard_mock.router, tags=["dashboard"])
api_router.include_router(user_center_mock.router, tags=["user-center"])
api_router.include_router(learning_report.router, prefix="/learning-report", tags=["learning-report"])
api_router.include_router(ai_metrics.router, prefix="/ai-metrics", tags=["ai-metrics"])
api_router.include_router(health.router, tags=["ops"])
api_router.include_router(behavior_analysis.router, prefix="/behavior", tags=["behavior-analysis"])
# api_router.include_router(utils.router)
# api_router.include_router(items.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
