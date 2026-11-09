import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure app is importable
API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.user import User
from app.models.workspace import Workspace
from app.core.security import hash_password, create_access_token
from app.workers.queue import job_manager

# In-memory SQLite with StaticPool so all connections share the same in-memory DB
engine_test = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# Wire job_manager to use test DB session factory
job_manager.session_factory = TestingSessionLocal


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
