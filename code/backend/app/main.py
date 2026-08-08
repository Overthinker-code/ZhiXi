import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
import httpx
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.main import api_router
from app.backend_pre_start import bootstrap_legacy_empty_database
from app.core.config import settings
from app.core.db import engine, init_db
from app.core.http_security import (
    AIRequestBudgetMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
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
from app.models.conversation_message import ConversationMessage  # noqa: F401
from app.models.learning_context import LearningContext  # noqa: F401
from app.models.agent_task import AgentTask  # noqa: F401
from app.models.learning_task import LearningTask  # noqa: F401
from app.models.knowledge_graph import KnowledgeGraph  # noqa: F401
from app.models.resource_library import ResourceFavorite, UserResourceConfig  # noqa: F401
from app.models.external_resource import ExternalResource  # noqa: F401
from app.models.resource_recommendation import PersonalizedResourceRecommendation  # noqa: F401
from app.models.quiz import Question, QuizAttempt, WrongQuestion  # noqa: F401
from app.models.resource_run import (  # noqa: F401
    CourseKnowledgeEdge,
    CourseKnowledgeNode,
    CourseKnowledgeNodeAction,
    ResourceGenerationRun,
    ResourceGenerationStep,
    ResourceKnowledgeLink,
)
from app.models.learning_evidence import (  # noqa: F401
    LearningEvidence,
    LearningPathUpdateEvent,
    ProfileUpdateEvent,
)

logger = logging.getLogger(__name__)
BACKEND_ROOT = (
    Path(sys._MEIPASS) / "backend"  # type: ignore[attr-defined]
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[1]
)


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)


def run_schema_migrations() -> None:
    """在应用启动时补齐增量 schema 变更。"""
    alembic_ini = BACKEND_ROOT / "alembic.ini"
    # Use Alembic's Python API instead of spawning ``python -m alembic``.
    # Besides avoiding an unnecessary child process, this also works when the
    # backend is launched from a frozen Windows executable where
    # ``sys.executable`` is the application launcher rather than python.exe.
    config = AlembicConfig(str(alembic_ini))
    config.set_main_option("script_location", str(BACKEND_ROOT / "app" / "alembic"))
    alembic_command.upgrade(config, "head")


def ensure_sqlalchemy_tables() -> None:
    # Legacy revisions assume a pre-Alembic baseline. Bootstrap only a strictly
    # empty database; all existing databases remain on normal upgrade semantics.
    bootstrapped = bootstrap_legacy_empty_database(
        engine, alembic_ini=BACKEND_ROOT / "alembic.ini"
    )
    # A strictly empty database is created from the current metadata and
    # stamped directly at the Alembic head. Running ``upgrade head`` again in
    # the same startup is redundant and can wait on PostgreSQL DDL locks.
    if not bootstrapped:
        run_schema_migrations()
    # SQLModel tables used by auth/business modules + bootstrap admin user
    with Session(engine) as session:
        init_db(session)
    logger.info("Schema migrations are up to date")


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_sqlalchemy_tables()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.ENVIRONMENT == "local",
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=(
        None
        if settings.ENVIRONMENT == "production"
        else f"{settings.API_V1_STR}/openapi.json"
    ),
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


@app.exception_handler(httpx.TimeoutException)
async def upstream_timeout_handler(_: Request, __: httpx.TimeoutException) -> JSONResponse:
    return JSONResponse(status_code=504, content={"detail": "Upstream service timed out"})


@app.exception_handler(httpx.RequestError)
async def upstream_request_handler(_: Request, __: httpx.RequestError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": "Upstream service unavailable"})

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AIRequestBudgetMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_SIZE)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.TRUSTED_HOSTS)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["Content-Disposition", "X-Request-ID"],
        max_age=600,
    )

app.include_router(api_router, prefix=settings.API_V1_STR)
