from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.chat import router as chat_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.discovery import router as discovery_router
from app.api.v1.graph import router as graph_router
from app.api.v1.agent import router as agent_router

# Initialize tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VERITAS API",
    description="VERITAS: Research Intelligence. Grounded in Truth. Core Ingestion, Extraction, Hybrid Retrieval, Evidence Verification, Literature Analysis, Academic Discovery, Knowledge Graph & Autonomous Agent.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(retrieval_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
app.include_router(discovery_router, prefix=settings.API_V1_PREFIX)
app.include_router(graph_router, prefix=settings.API_V1_PREFIX)
app.include_router(agent_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "product": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": "1.0.0",
        "phase": "Phase 9 - Autonomous AI Research Agent",
    }
