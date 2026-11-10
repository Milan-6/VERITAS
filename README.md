# VERITAS
> **Research Intelligence. Grounded in Truth.**

[![Platform Status](https://img.shields.io/badge/Status-v1.0%20Production%20Ready-00E5FF?style=flat-square)](docs/PHASE_TRACKER.md)
[![Test Suite](https://img.shields.io/badge/Tests-78%20Passed%20(100%25)-emerald?style=flat-square)](apps/api/tests)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2%20Standalone-black?style=flat-square)](https://nextjs.org)
[![Docker](https://img.shields.io/badge/Docker%20Compose-Orchestrated-2496ED?style=flat-square)](docker-compose.yml)
[![Qdrant](https://img.shields.io/badge/Qdrant-v1.8.4-DC2626?style=flat-square)](https://qdrant.tech)

---

## 1. Overview

**VERITAS** is an enterprise-grade AI research intelligence, literature discovery, and synthesis platform designed to ingest, decompose, reason over, and cite complex academic literature (PDFs, preprints, journal articles, and technical documentation) with cryptographic traceability, deterministic citation provenance, strict multi-tenant isolation, and automated evidence entailment verification.

Unlike standard conversational RAG interfaces that suffer from hallucinations, VERITAS implements a post-generation Evidence Verification Engine that grades every response, claim by claim, against source bounding boxes and mathematical passages before delivery.

---

## 2. Core Capabilities Across Phases 1–15

* **Phase 1: Ingestion & Decomposition Engine:** PyMuPDF layout analysis preserving multi-column academic reading order, cryptographic SHA-256 deduplication, and page bounding-box provenance.
* **Phase 2: Hybrid Semantic Retrieval:** Dense vector embeddings (`text-embedding-004`) combined with sparse BM25 lexical search and Reciprocal Rank Fusion (RRF) on Qdrant.
* **Phase 3: Grounded Conversational Memory:** Multi-turn chat assistant with strict abstention rules, deterministic source citation tags, and context windows.
* **Phase 4: Evidence Verification Engine:** Post-generation natural language inference (NLI) pipeline grading responses as `FULLY_ENTAILED`, `PARTIALLY_ENTAILED`, or `UNGROUNDED_HALLUCINATION`.
* **Phase 5: Comparative Literature Analysis:** Cross-paper synthesis matrix extracting datasets, methodology, metrics, and detecting academic contradictions.
* **Phase 6: Academic Research Discovery:** OpenAlex discovery client, citation network visualization, and SSRF-protected DOI/URL direct PDF ingestion.
* **Phase 8: Research Knowledge Graph:** Entity extraction (theories, methods, datasets, authors) and relational graph traversal rendered in interactive force-directed canvas.
* **Phase 9: Autonomous AI Research Agent:** Bounded ReAct state machine generating multi-paper synthesized Markdown reports with automated evidence audit cards.
* **Phase 10: Learning Productivity:** Automated generation of conceptual flashcards (Anki CSV export) and diagnostic 5-question quizzes with page citations.
* **Phase 11: Multi-User Collaboration & PDF Dossier:** Multi-tenant workspace sharing (`OWNER`, `EDITOR`, `VIEWER` roles) and formal PDF dossier export via ReportLab.
* **Phase 12: Reference Managers & Webhooks:** Zotero sync client, Fernet symmetric credential encryption, and SSRF-protected HMAC-SHA256 signed event webhooks.
* **Phase 13: Platform Analytics & Telemetry:** Redis-backed sliding-window rate limiting, sub-cent LLM token accounting, and workspace administrative dashboard.
* **Phase 14: Security, Auditing & Compliance:** Native regex prompt injection & DAN jailbreak interception (OWASP LLM01), immutable append-only audit trails, and GDPR Article 17/20 data sovereignty workflows.
* **Phase 15: Production Containerization & DevOps:** Multi-stage Dockerfiles for FastAPI and Next.js standalone runner, orchestrated via Docker Compose with PostgreSQL, Redis, Qdrant, and Celery workers.

---

## 3. System Architecture

```
[ User Browser ] ──── HTTPS ────► [ Next.js 14 Frontend (Port 3000) ]
                                          │
                                          │ REST / SSE
                                          ▼
                               ┌──────────────────────────────────────────┐
                               │     FastAPI Application (Port 8000)      │
                               │  - Prompt Injection Defense              │
                               │  - Rate Limiting Middleware              │
                               │  - Evidence Verification Engine          │
                               │  - Multi-Tenant RBAC Authorization       │
                               └──────┬────────────┬─────────────┬────────┘
                                      │            │             │
                    PostgreSQL 15 ◄───┘            ▼             └──► Redis 7
             (Relational DB & Audit)          Qdrant 1.8.4       (Broker, Rate Limits,
                                            (Hybrid Vectors)       Sliding Windows)
                                                                         ▲
                                                                         │ Tasks
                                                              ┌──────────┴────────┐
                                                              │  Celery Worker    │
                                                              │  - PDF Pipeline   │
                                                              │  - Webhooks       │
                                                              └───────────────────┘
```

---

## 4. Quick Start with Docker Compose (Recommended)

### 4.1 Prerequisites
- **Docker Engine** (v24.0 or higher)
- **Docker Compose** (v2.20 or higher)

### 4.2 Step 1: Configure Environment Variables
Copy the template and configure your secrets:
```bash
cp .env.example .env
```
Edit `.env` and supply:
- `SECRET_KEY`: A strong random string for JWT encryption.
- `GEMINI_API_KEY`: Your Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/)).

### 4.3 Step 2: Build & Start the Entire Stack
```bash
docker compose up --build -d
```
This builds and launches 6 interconnected services:
1. `veritas_postgres`: Relational database with automatic Alembic migrations.
2. `veritas_redis`: In-memory cache and Celery broker.
3. `veritas_qdrant`: High-performance vector database.
4. `veritas_api`: FastAPI backend running Uvicorn on port 8000.
5. `veritas_worker`: Celery background worker handling asynchronous document processing.
6. `veritas_web`: Next.js 14 standalone frontend running on port 3000.

### 4.4 Step 3: Verify Service Health
```bash
docker compose ps
```
All services should display `Up` or `healthy`. You can view live container logs with:
```bash
docker compose logs -f api
```

### 4.5 Step 4: Access the Application
- **Web UI:** [http://localhost:3000](http://localhost:3000)
- **Interactive API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Qdrant Vector Console:** [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### 4.6 Stopping the Stack
```bash
# Stop containers (preserves volume data)
docker compose down

# Stop containers and destroy persistent volumes (clean reset)
docker compose down -v
```

---

## 5. Local Development Setup (Without Docker)

### 5.1 Backend Setup (FastAPI)
```bash
# Navigate to API directory
cd apps/api

# Create & activate Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start API server
uvicorn app.main:app --reload --port 8000
```

### 5.2 Frontend Setup (Next.js 14)
```bash
# Navigate to web directory
cd apps/web

# Install Node dependencies
npm install

# Run local development server
npm run dev
```

---

## 6. Running the Automated Test Suite

The test suite covers unit tests, integration pipelines, multi-tenant RBAC isolation, evidence verification entailment scoring, and GDPR compliance:

```bash
# Execute all 78 platform tests
python -m pytest apps/api/tests
```

Sample output:
```text
============================= test session starts =============================
platform win32 -- Python 3.12/3.13, pytest-9.2.0
collected 78 items

apps/api/tests/test_academic_discovery.py ......                         [  7%]
apps/api/tests/test_advanced_integrations.py .....                       [ 14%]
apps/api/tests/test_agent_workflow.py ...                                [ 17%]
apps/api/tests/test_auth.py ......                                       [ 25%]
apps/api/tests/test_authorization.py .                                   [ 26%]
apps/api/tests/test_background_jobs.py ..                                [ 29%]
apps/api/tests/test_chat_assistant.py .....                              [ 35%]
apps/api/tests/test_chunking.py ..                                       [ 38%]
apps/api/tests/test_collaboration_and_export.py ....                     [ 43%]
apps/api/tests/test_embedding_resilience.py ...                          [ 47%]
apps/api/tests/test_evidence_verification.py ....                        [ 52%]
apps/api/tests/test_extraction_pipeline.py ..                            [ 55%]
apps/api/tests/test_hybrid_retrieval.py ..                               [ 57%]
apps/api/tests/test_knowledge_graph.py ....                              [ 62%]
apps/api/tests/test_learning_productivity.py .....                       [ 69%]
apps/api/tests/test_literature_analysis.py ...                           [ 73%]
apps/api/tests/test_platform_analytics.py ......                         [ 80%]
apps/api/tests/test_security_and_compliance.py .......                   [ 89%]
apps/api/tests/test_upload_validation.py .......                         [ 98%]
apps/api/tests/test_vector_store.py .                                    [100%]

====================== 78 passed in 6.36s =======================
```

---

## 7. Directory Structure

```
d:/Project-1/
├── docker-compose.yml          # Production 6-service stack orchestration
├── .env.example                # Comprehensive environment variable template
├── README.md                   # Platform documentation & deployment guide
├── docs/                       # Architectural specs & phase implementation reports
│   ├── PHASE_TRACKER.md        # Complete 15-phase delivery status tracker
│   ├── VERITAS_PHASE_14_IMPLEMENTATION_REPORT.md
│   └── VERITAS_PHASE_15_IMPLEMENTATION_REPORT.md
├── apps/
│   ├── api/                    # FastAPI Backend Application & Celery Worker
│   │   ├── Dockerfile          # Multi-stage Python 3.12-slim container
│   │   ├── entrypoint.sh       # Database migration & runtime dispatcher
│   │   ├── requirements.txt    # Production Python dependencies
│   │   ├── alembic/            # Database schema migrations
│   │   ├── app/                # API routes, models, services, workers
│   │   └── tests/              # 78 automated regression & integration tests
│   └── web/                    # Next.js 14 Frontend Application
│       ├── Dockerfile          # Multi-stage Node 20-Alpine standalone container
│       ├── next.config.mjs     # Standalone output configuration
│       ├── package.json        # Dependencies & scripts
│       └── src/                # App router, components, visualizers, lib
```

---

## 8. License & Attribution

VERITAS is proprietary software developed with Google Antigravity.  
*Research Intelligence. Grounded in Truth.*
