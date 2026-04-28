import logging
import subprocess
import sys
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings
from app.core.db import engine, init_db
from app.db.base_class import Base
from app.models.chat_thread import ChatThread  # noqa: F401
from app.models.chat import Chat  # noqa: F401
from app.models.chat_feedback import ChatFeedback  # noqa: F401
from app.models.chat_artifact import ChatArtifact  # noqa: F401
from app.models.ai_usage_log import AIUsageLog  # noqa: F401
from app.models.item import Item  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_memory_profile import UserMemoryProfile  # noqa: F401

logger = logging.getLogger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)


def run_schema_migrations() -> None:
    """在应用启动时补齐增量 schema 变更。"""
    alembic_ini = BACKEND_ROOT / "alembic.ini"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(alembic_ini),
            "upgrade",
            "head",
        ],
        cwd=BACKEND_ROOT,
        check=True,
    )


@app.on_event("startup")
def ensure_sqlalchemy_tables() -> None:
    # SQLAlchemy tables used by chat/history modules
    Base.metadata.create_all(bind=engine)
    # SQLModel tables used by auth/business modules + bootstrap admin user
    with Session(engine) as session:
        init_db(session)
    run_schema_migrations()
    logger.info("Schema migrations are up to date")

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
