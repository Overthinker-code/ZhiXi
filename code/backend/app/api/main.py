from fastapi import APIRouter

# from app.api.routes import items, login, private, users, utils
from app.api.routes import login, private, users, education
from app.api.v1.endpoints import (
    chat,
    rag,
    chat_threads,
    dashboard_mock,
    user_center_mock,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(education.router, prefix="/education", tags=["education"])
api_router.include_router(chat_threads.router, prefix="/chat", tags=["chat"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(dashboard_mock.router, tags=["dashboard"])
api_router.include_router(user_center_mock.router, tags=["user-center"])
# api_router.include_router(utils.router)
# api_router.include_router(items.router)


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
