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
    file,
    rag,
    chat_threads,
    dashboard_mock,
    dashboard,
    user_center_mock,
    health,
    learning_report,
    learning_path,
    ai_metrics,
    digital_human_assistant,
    alerts,
    resource_workshop,
    resource_generation,
    ai_chat,
    student_hub,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(education.router, prefix="/education", tags=["education"])
api_router.include_router(chat_threads.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(file.router, prefix="/file", tags=["file"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(
    digital_human.router, prefix="/digital-human", tags=["digital-human"]
)
if settings.ENABLE_MOCK_ROUTES:
    api_router.include_router(dashboard_mock.router, tags=["dashboard"])
    api_router.include_router(user_center_mock.router, tags=["user-center"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(learning_report.router, prefix="/learning-report", tags=["learning-report"])
api_router.include_router(learning_path.router, prefix="/learning-path", tags=["learning-path"])
api_router.include_router(student_hub.router, prefix="/student-hub", tags=["student-hub"])
api_router.include_router(ai_metrics.router, prefix="/ai-metrics", tags=["ai-metrics"])
api_router.include_router(resource_workshop.router, prefix="/resource-workshop", tags=["resource-workshop"])
api_router.include_router(resource_generation.router, prefix="/resource-generation", tags=["resource-generation"])
api_router.include_router(ai_chat.router, prefix="/ai", tags=["ai-chat"])
api_router.include_router(
    digital_human_assistant.router, tags=["classroom-assistant"]
)
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(health.router, tags=["ops"])
api_router.include_router(behavior_analysis.router, prefix="/behavior", tags=["behavior-analysis"])
# api_router.include_router(utils.router)
# api_router.include_router(items.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
