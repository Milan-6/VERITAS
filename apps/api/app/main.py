from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1.auth import router as auth_router
from app.api.v1.documents import router as documents_router

# Initialize tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VERITAS API",
    description="VERITAS: Research Intelligence. Grounded in Truth. Core Ingestion & Extraction Engine.",
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


@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "product": settings.PROJECT_NAME,
        "tagline": settings.TAGLINE,
        "version": "1.0.0",
        "phase": "Phase 1 - Document Processing Engine",
    }
