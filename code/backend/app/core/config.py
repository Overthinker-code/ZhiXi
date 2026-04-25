import os
import secrets
import warnings
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
    validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = True
    SMTP_PORT: int = 465
    SMTP_HOST: str | None = "smtp.qq.com"
    SMTP_USER: str | None = "2312671282@qq.com"
    SMTP_PASSWORD: str | None = "fxmfxlrbprhbeacb"
    EMAILS_FROM_EMAIL: EmailStr | None = "2312671282@qq.com"
    EMAILS_FROM_NAME: EmailStr | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self

    # 新增教育系统的配置
    BASE_PATH: str = str(Path(__file__).resolve().parent.parent.parent)
    UPLOAD_DIR: str = os.path.join(BASE_PATH, "files")
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    RAG_UPLOAD_DIR: str = os.path.join(BASE_PATH, "uploads")
    CHROMA_DB_PATH: str = os.path.join(BASE_PATH, "vector_db")

    CHAT_PROVIDER: str = "ollama"
    CHAT_MODEL: str = "DeepSeek-R1"
    CHAT_TEMPERATURE: float = 0.0
    # 前端未传 max_tokens 时，协作图各专员/汇总使用的默认输出上限（可按机器与模型调大）
    CHAT_DEFAULT_MAX_TOKENS: int = 16384
    # 主管结构化路由 JSON 不需要过长，单独设上限即可
    CHAT_SUPERVISOR_MAX_TOKENS: int = 4096
    # 协作图多次累加消息后发给模型前截断，降低上下文窗口撑爆概率（首条一般为 RAG 系统消息）
    CHAT_CONTEXT_HEAD_MESSAGES: int = 1
    CHAT_CONTEXT_TAIL_MESSAGES: int = 16
    CHAT_CONTEXT_MAX_MESSAGE_CHARS: int = 8000

    EMBEDDINGS_PROVIDER: str = "ollama"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "deepseek-r1:7b"
    OLLAMA_EMBEDDINGS_MODEL: str = "nomic-embed-text"
    VECTOR_STORE_TYPE: str = "chroma"

    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None

    RAG_TOP_K: int = 4
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200

    REDIS_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    REDIS_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"
    YOLO_SERVICE_HOST: str = "http://127.0.0.1"
    YOLO_SERVICE_PORT: int = 8002

    DIGITAL_HUMAN_INPUT_DIR: str = os.path.join(BASE_PATH, "digital_human_inputs")
    DIGITAL_HUMAN_OUTPUT_DIR: str = os.path.join(BASE_PATH, "digital_human_outputs")
    DIGITAL_HUMAN_ASSET_DIR: str = os.path.join(BASE_PATH, "digital_human_assets")
    DIGITAL_HUMAN_ENGINE: str = "musetalk"
    DIGITAL_HUMAN_EDGE_TTS_BIN: str = ""
    DIGITAL_HUMAN_EDGE_TTS_VOICE: str = "zh-CN-YunxiNeural"
    DIGITAL_HUMAN_RENDER_TIMEOUT_SECONDS: int = 1800
    DIGITAL_HUMAN_CELERY_ENABLED: bool = True

    DIGITAL_HUMAN_MUSETALK_DIR: str = os.path.join(BASE_PATH, "MuseTalk")
    DIGITAL_HUMAN_MUSETALK_CONDA_BIN: str = "conda"
    DIGITAL_HUMAN_MUSETALK_CONDA_ENV: str = "MuseTalk"
    DIGITAL_HUMAN_MUSETALK_PYTHON: str = ""
    DIGITAL_HUMAN_MUSETALK_TEMPLATE_CONFIG: str = os.path.join(
        DIGITAL_HUMAN_MUSETALK_DIR, "configs", "inference", "test.yaml"
    )
    DIGITAL_HUMAN_MUSETALK_UNET_MODEL_PATH: str = os.path.join(
        DIGITAL_HUMAN_MUSETALK_DIR, "models", "musetalkV15", "unet.pth"
    )
    DIGITAL_HUMAN_MUSETALK_UNET_CONFIG_PATH: str = os.path.join(
        DIGITAL_HUMAN_MUSETALK_DIR, "models", "musetalkV15", "musetalk.json"
    )
    DIGITAL_HUMAN_MUSETALK_VERSION: str = "v15"
    DIGITAL_HUMAN_MUSETALK_EXTRA_ARGS: str = ""
    DIGITAL_HUMAN_MUSETALK_RESULT_DIR: str = os.path.join(
        DIGITAL_HUMAN_OUTPUT_DIR, "musetalk_runs"
    )
    DIGITAL_HUMAN_FFMPEG_PATH: str = ""
    DIGITAL_HUMAN_FACE_IMAGE: str = os.path.join(
        DIGITAL_HUMAN_ASSET_DIR, "teacher_face.jpg"
    )
    DIGITAL_HUMAN_IDLE_VIDEO: str = os.path.join(
        DIGITAL_HUMAN_ASSET_DIR, "teacher_idle.mp4"
    )

    DIGITAL_HUMAN_WAV2LIP_DIR: str = os.path.join(BASE_PATH, "Wav2Lip")
    DIGITAL_HUMAN_WAV2LIP_CHECKPOINT: str = os.path.join(
        DIGITAL_HUMAN_WAV2LIP_DIR, "checkpoints", "wav2lip_gan.pth"
    )

    MEMORY_PROFILE_AUTO_REFRESH: bool = True
    MEMORY_PROFILE_MAX_TURNS: int = 20
    MEMORY_PROFILE_MAX_CHARS: int = 12000
    DEMO_MODE: bool = False
    DEMO_FAKE_CHAT_CACHE: bool = False
    DEVELOPER_PANEL_ENABLED: bool = True


settings = Settings()  # type: ignore

# 确保上传目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "videos"), exist_ok=True)
os.makedirs(settings.RAG_UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
os.makedirs(settings.DIGITAL_HUMAN_INPUT_DIR, exist_ok=True)
os.makedirs(settings.DIGITAL_HUMAN_OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.DIGITAL_HUMAN_ASSET_DIR, exist_ok=True)
os.makedirs(settings.DIGITAL_HUMAN_MUSETALK_RESULT_DIR, exist_ok=True)
