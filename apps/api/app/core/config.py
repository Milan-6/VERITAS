import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent  # d:\Project-1

class Settings(BaseModel):
    PROJECT_NAME: str = "VERITAS"
    TAGLINE: str = "Research Intelligence. Grounded in Truth."
    API_V1_PREFIX: str = "/api/v1"
    
    # Storage settings
    STORAGE_DIR: Path = Field(
        default_factory=lambda: Path(os.getenv("VERITAS_STORAGE_DIR", str(BASE_DIR / "uploads" / "documents")))
    )
    MAX_UPLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_MIME_TYPES: list[str] = ["application/pdf"]
    ALLOWED_EXTENSIONS: list[str] = [".pdf"]
    
    # Database
    DATABASE_URL: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/veritas.db")
    )
    
    # Security
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", "veritas-secure-grounded-truth-dev-key-change-in-prod-3829472947")
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Task Queue / Background Jobs
    CELERY_TASK_ALWAYS_EAGER: bool = Field(
        default_factory=lambda: os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() in ("true", "1", "yes")
    )
    REDIS_URL: str = Field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

    # Rate Limiting & Telemetry (Phase 13)
    RATE_LIMIT_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    )
    RATE_LIMIT_DEFAULT_REQUESTS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_DEFAULT_REQUESTS", "120"))
    )
    RATE_LIMIT_DEFAULT_WINDOW: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_DEFAULT_WINDOW", "60"))
    )
    RATE_LIMIT_HEAVY_REQUESTS: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_HEAVY_REQUESTS", "20"))
    )
    RATE_LIMIT_HEAVY_WINDOW: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_HEAVY_WINDOW", "60"))
    )

    # Vector Database (Qdrant)
    QDRANT_HOST: str | None = Field(default_factory=lambda: os.getenv("QDRANT_HOST", None))
    QDRANT_PORT: int = Field(default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333")))
    QDRANT_URL: str | None = Field(default_factory=lambda: os.getenv("QDRANT_URL", None))
    QDRANT_API_KEY: str | None = Field(default_factory=lambda: os.getenv("QDRANT_API_KEY", None))
    QDRANT_COLLECTION: str = "veritas_research_chunks"
    QDRANT_TIMEOUT: float = Field(default_factory=lambda: float(os.getenv("QDRANT_TIMEOUT", "5.0")))
    QDRANT_IN_MEMORY: bool = Field(
        default_factory=lambda: os.getenv("QDRANT_IN_MEMORY", "false").lower() in ("true", "1", "yes")
    )
    QDRANT_LOCAL_PATH: str = Field(
        default_factory=lambda: os.getenv("QDRANT_LOCAL_PATH", str(BASE_DIR / "data" / "qdrant"))
    )

    # Embedding Settings
    GEMINI_API_KEY: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    )
    EMBEDDING_MODEL: str = "models/text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # LLM Settings (Phase 3)
    LLM_MODEL: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gemini-2.0-flash"))
    LLM_TEMPERATURE: float = 0.0  # Greedy deterministic decoding
    STRICT_ABSTENTION_MESSAGE: str = "This is not mentioned in the provided research corpus."

    # External Discovery Settings (Phase 6)
    OPENALEX_MAILTO: str = Field(
        default_factory=lambda: os.getenv("OPENALEX_MAILTO", "veritas-research@antigravity.ai")
    )
    DISCOVERY_REQUEST_TIMEOUT: float = 15.0
    DISCOVERY_USER_AGENT: str = "VERITAS-Research-Intelligence/1.0 (mailto:veritas-research@antigravity.ai)"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

settings = Settings()

# Ensure storage directory exists
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
