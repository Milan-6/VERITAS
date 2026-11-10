import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from qdrant_client import QdrantClient, models

# Ensure app is importable
API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

# Force synchronous testing & offline deterministic embeddings
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"
os.environ["QDRANT_IN_MEMORY"] = "true"
os.environ["QDRANT_TIMEOUT"] = "5.0"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

from app.core.config import settings
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.QDRANT_IN_MEMORY = True
settings.QDRANT_TIMEOUT = 5.0
settings.GEMINI_API_KEY = ""

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace
from app.core.security import hash_password, create_access_token
from app.workers.queue import job_manager
from app.services.vector_store import vector_store
from app.services.embeddings import DeterministicDenseEmbeddingProvider, GeminiEmbeddingProvider
from app.services.verification import evidence_verifier

evidence_verifier.api_key = ""

# 1. Force synchronous background task execution
job_manager.always_eager = True

# In-memory SQLite with StaticPool so all connections share the same in-memory DB
engine_test = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# Wire job_manager to use test DB session factory
job_manager.session_factory = TestingSessionLocal

# Wire telemetry_service to use test DB session factory (Phase 13)
from app.services.telemetry import telemetry_service
telemetry_service.session_factory = TestingSessionLocal

# Wire audit_service to use test DB session factory (Phase 14)
from app.services.audit import audit_service
audit_service.session_factory = TestingSessionLocal

# In tests, avoid offline Redis socket connection attempts
from app.core.rate_limiter import rate_limiter
rate_limiter._redis_failed = True

# 2. Strict fast in-memory Qdrant Client (timeout=5.0)
test_qdrant_client = QdrantClient(location=":memory:", timeout=5.0)
vector_store.client = test_qdrant_client
vector_store.embedder = DeterministicDenseEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
vector_store._ensure_collection()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine_test)
    yield
    Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(autouse=True)
def clean_tables_after_test():
    yield
    # Clean tables after each test to ensure test isolation
    with engine_test.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            try:
                conn.execute(table.delete())
                conn.commit()
            except Exception:
                pass

    # Clean in-memory Qdrant vectors after each test
    try:
        test_qdrant_client.delete(
            collection_name=vector_store.collection_name,
            points_selector=models.FilterSelector(filter=models.Filter()),
        )
    except Exception:
        pass


@pytest.fixture(autouse=True)
def guard_against_live_embedding_network(monkeypatch):
    """
    Guarantees the test suite NEVER makes live external network calls to Gemini API.
    If any non-mocked Gemini embedding call is attempted, intercepts and returns mock vector safely.
    """
    import httpx

    original_send = httpx.Client.send

    def safe_send(self, request, *args, **kwargs):
        if "googleapis.com" in str(request.url):
            # Return synthetic 200 response with 768-dim embedding values
            return httpx.Response(
                status_code=200,
                json={"embedding": {"values": [0.01] * settings.EMBEDDING_DIMENSION}},
                request=request,
            )
        return original_send(self, request, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", safe_send)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db) -> User:
    user = User(
        email="researcher@veritas.edu",
        full_name="Dr. Jane Veritas",
        hashed_password=hash_password("VeritasPassword123!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_2(db) -> User:
    user = User(
        email="attacker@other.edu",
        full_name="Malicious Actor",
        hashed_password=hash_password("AttackPassword123!"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_token(test_user) -> str:
    return create_access_token({"sub": test_user.id, "email": test_user.email})


@pytest.fixture
def user_2_token(test_user_2) -> str:
    return create_access_token({"sub": test_user_2.id, "email": test_user_2.email})


@pytest.fixture
def auth_headers(user_token) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def auth_headers_2(user_2_token) -> dict:
    return {"Authorization": f"Bearer {user_2_token}"}
