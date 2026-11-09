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
