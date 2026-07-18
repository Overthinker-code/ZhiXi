import os
import re
import secrets
import warnings
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
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
    SECRET_KEY: str = ""
    # Short-lived bearer token. A future refresh-cookie flow may extend sessions
    # without keeping a replayable access token valid for days.
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    FRONTEND_HOST: str = "http://localhost:5173"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"
    TRUSTED_HOSTS: Annotated[list[str] | str, BeforeValidator(parse_cors)] = [
        "localhost",
        "127.0.0.1",
        "testserver",
    ]
    # One extra MiB above the file limit accommodates multipart boundaries.
    MAX_REQUEST_SIZE: int = 26 * 1024 * 1024
    AUTH_RATE_LIMIT_ATTEMPTS: int = 5
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 300
    AUTH_RATE_LIMIT_MAX_IDENTITIES: int = 4096
    AI_RATE_LIMIT_REQUESTS: int = 12
    AI_RATE_LIMIT_WINDOW_SECONDS: int = 60
    AI_BUDGET_MAX_IDENTITIES: int = 4096
    AI_BUDGET_CLEANUP_INTERVAL_SECONDS: int = 30
    AI_SSE_MAX_CONCURRENT_PER_USER: int = 2
    AI_SYNC_MAX_CONCURRENT_PER_USER: int = 1
    AI_SSE_TIMEOUT_SECONDS: int = 180
    AI_SYNC_TIMEOUT_SECONDS: int = 240
    WS_MAX_MESSAGE_SIZE: int = 3 * 1024 * 1024
    WS_MESSAGE_RATE_PER_SECOND: int = 4
    WS_IDLE_TIMEOUT_SECONDS: int = 30
    WS_ALLOW_QUERY_TOKEN_IN_LOCAL: bool = True

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
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

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

    def _check_default_secret(
        self,
        var_name: str,
        value: str | None,
        *,
        minimum_length: int | None = None,
    ) -> None:
        normalized = re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())
        is_placeholder = not normalized or normalized in {
            "changethis",
            "changeme",
            "secret",
            "password",
            "password123",
            "postgres",
            "admin",
            "example",
            "placeholder",
            "replacewithsecurevalue",
            "yourpasswordhere",
            "yoursecrethere",
        } or normalized.startswith(("replacewith", "yourpassword", "yoursecret"))
        is_too_short = minimum_length is not None and len(value or "") < minimum_length
        if is_placeholder or is_too_short:
            requirement = (
                f" and contain at least {minimum_length} characters"
                if minimum_length
                else ""
            )
            message = (
                f"{var_name} must not use a placeholder{requirement} "
                "outside local development."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        if self.ENVIRONMENT == "local" and not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_urlsafe(32)
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY, minimum_length=32)
        self._check_default_secret(
            "POSTGRES_PASSWORD", self.POSTGRES_PASSWORD, minimum_length=12
        )
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD",
            self.FIRST_SUPERUSER_PASSWORD,
            minimum_length=12,
        )

        if self.ENVIRONMENT == "production":
            if not self.TRUSTED_HOSTS or "*" in self.TRUSTED_HOSTS:
                raise ValueError(
                    "TRUSTED_HOSTS must be an explicit non-wildcard allowlist in production."
                )
            if not self.all_cors_origins:
                raise ValueError("At least one explicit frontend origin is required in production.")
            if any(origin == "*" for origin in self.all_cors_origins):
                raise ValueError("Wildcard CORS origins are forbidden in production.")
            if self.CODE_SANDBOX_ENABLED:
                raise ValueError("CODE_SANDBOX_ENABLED is forbidden in production.")
            if self.ENABLE_MOCK_ROUTES:
                raise ValueError("ENABLE_MOCK_ROUTES is forbidden in production.")
            if self.DEMO_FAKE_CHAT_CACHE:
                raise ValueError("DEMO_FAKE_CHAT_CACHE is forbidden in production.")
            if self.DEVELOPER_PANEL_ENABLED:
                raise ValueError("DEVELOPER_PANEL_ENABLED is forbidden in production.")

        return self

    # 新增教育系统的配置
    BASE_PATH: str = str(Path(__file__).resolve().parent.parent.parent)
    UPLOAD_DIR: str = os.path.join(BASE_PATH, "files")
    MAX_UPLOAD_SIZE: int = 25 * 1024 * 1024
    RAG_UPLOAD_DIR: str = os.path.join(BASE_PATH, "uploads")
    CHROMA_DB_PATH: str = os.path.join(BASE_PATH, "vector_db")

    # Fixed public catalog APIs used for deliberate external-resource refreshes.
    # No user supplied URL is fetched by this feature.
    EXTERNAL_DISCOVERY_TIMEOUT_SECONDS: float = 2.5
    EXTERNAL_DISCOVERY_MAX_RESULTS_PER_PROVIDER: int = 3
    EXTERNAL_DISCOVERY_MAX_TOPICS: int = 3
    EXTERNAL_DISCOVERY_STALE_HOURS: int = 72
    EXTERNAL_DISCOVERY_USER_AGENT: str = "ZhiXiStudentResourceDiscovery/1.0 (+https://zhixi.local)"

    CHAT_PROVIDER: str = "mimo"
    CHAT_MODEL: str = "mimo-v2.5-pro"
    CHAT_TEMPERATURE: float = 0.0
    # 前端未传 max_tokens 时，协作图各专员/汇总使用的默认输出上限（可按机器与模型调大）
    CHAT_DEFAULT_MAX_TOKENS: int = 16384
    # 主管结构化路由 JSON 不需要过长，单独设上限即可
    CHAT_SUPERVISOR_MAX_TOKENS: int = 4096
    # 协作图多次累加消息后发给模型前截断，降低上下文窗口撑爆概率（首条一般为 RAG 系统消息）
    CHAT_CONTEXT_HEAD_MESSAGES: int = 1
    CHAT_CONTEXT_TAIL_MESSAGES: int = 16
    CHAT_CONTEXT_MAX_MESSAGE_CHARS: int = 8000

    EMBEDDINGS_PROVIDER: str = "hash"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:14b"
    OLLAMA_EMBEDDINGS_MODEL: str = "nomic-embed-text"
    VECTOR_STORE_TYPE: str = "chroma"

    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE: str | None = None

    MIMO_API_KEY: str | None = None
    MIMO_API_BASE: str = "https://api.xiaomimimo.com/v1"
    MIMO_CHAT_MODEL: str = "mimo-v2.5-pro"
    MIMO_FAST_MODEL: str = "mimo-v2.5"
    MIMO_MULTIMODAL_MODEL: str = "mimo-v2.5"
    MIMO_TTS_MODEL: str = "mimo-v2.5-tts"
    MIMO_TIMEOUT_SECONDS: int = 120
    RESOURCE_GENERATION_AI_ENABLED: bool = True
    RESOURCE_GENERATION_TIMEOUT_SECONDS: int = 45

    # Independent input/output moderation. ``http`` means a dedicated
    # moderation endpoint, never a chat-model prompt. Local rules remain as a
    # deterministic fail-safe when the provider is unavailable.
    CONTENT_SAFETY_PROVIDER: Literal["local", "http"] = "local"
    CONTENT_SAFETY_API_URL: str | None = None
    CONTENT_SAFETY_API_KEY: str | None = None
    CONTENT_SAFETY_TIMEOUT_SECONDS: float = 2.5

    MULTIMODAL_PROVIDER: str = "mimo"
    MULTIMODAL_MODEL: str = "mimo-v2.5"
    MULTIMODAL_FALLBACK_MODEL: str = "mimo-v2.5-pro"
    MULTIMODAL_API_BASE: str | None = None
    MULTIMODAL_API_KEY: str | None = None
    MULTIMODAL_TIMEOUT_SECONDS: int = 180

    RAG_TOP_K: int = 4
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    # Hash embeddings are not semantic. Require lexical coverage before a hash
    # candidate can be cited so unrelated vector noise becomes RAG_EMPTY.
    # Keep the deterministic hash fallback conservative. 0.16 rejects common
    # single-term collisions (for example an unrelated query containing only
    # “实验”) while retaining the seeded course paraphrase set.
    RAG_HASH_MIN_LEXICAL_SCORE: float = 0.16
    # Course knowledge retrieval needs a stricter evidence gate than an
    # explicitly attached document. Hybrid RRF can otherwise lift unrelated
    # top-ranked chunks above the generic vector floor.
    RAG_COURSE_SEMANTIC_MIN_SCORE: float = 0.34
    RAG_VECTOR_MIN_SCORE: float = 0.20
    RAG_LEXICAL_MAX_DOCUMENTS: int = 2500

    REDIS_BROKER_URL: str = "redis://127.0.0.1:6379/0"
    REDIS_RESULT_BACKEND: str = "redis://127.0.0.1:6379/1"
    YOLO_SERVICE_HOST: str = "http://127.0.0.1"
    YOLO_SERVICE_PORT: int = 8002

    DIGITAL_HUMAN_INPUT_DIR: str = os.path.join(BASE_PATH, "digital_human_inputs")
    DIGITAL_HUMAN_OUTPUT_DIR: str = os.path.join(BASE_PATH, "digital_human_outputs")
    DIGITAL_HUMAN_ASSET_DIR: str = os.path.join(BASE_PATH, "digital_human_assets")
    DIGITAL_HUMAN_ENGINE: str = "musetalk"
    DIGITAL_HUMAN_ALLOW_FALLBACK_RENDERER: bool = True
    DIGITAL_HUMAN_EDGE_TTS_BIN: str = ""
    DIGITAL_HUMAN_EDGE_TTS_VOICE: str = "zh-CN-YunxiNeural"
    DIGITAL_HUMAN_EDGE_TTS_FALLBACK_VOICES: str = (
        "zh-CN-XiaoxiaoNeural,zh-CN-YunjianNeural,zh-CN-YunyangNeural"
    )
    DIGITAL_HUMAN_EDGE_TTS_RETRIES: int = 2
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
    LEARNING_REPORT_LLM_TIMEOUT_SECONDS: int = 8
    DEMO_MODE: bool = False
    DEMO_FAKE_CHAT_CACHE: bool = False
    DEVELOPER_PANEL_ENABLED: bool = True
    ENABLE_MOCK_ROUTES: bool = False
    CODE_SANDBOX_ENABLED: bool = False

    # 讯飞/星火 API 预留（赛题合规项，未配置时回退 CHAT_PROVIDER）
    IFLYTEK_APP_ID: str | None = None
    IFLYTEK_API_KEY: str | None = None
    IFLYTEK_API_SECRET: str | None = None
    IFLYTEK_SPARK_MODEL: str = "generalv3.5"


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
