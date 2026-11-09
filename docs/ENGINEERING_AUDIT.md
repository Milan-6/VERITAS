# Engineering Audit & Baseline Assessment: VERITAS (formerly ScholarPulse AI)
**Product:** VERITAS  
**Tagline:** Research Intelligence. Grounded in Truth.  
**Phase:** Phase 0 (Baseline Assessment) & Phase 1 Inception  
**Date:** 2026-11-09  
**Role:** Principal Software Architect & Lead Engineer  
**Status:** COMPLETE — Greenfield State Identified  

---

## 1. Executive Summary

A comprehensive, forensic inspection of the `VERITAS` workspace (`D:\Project-1`) was conducted to establish the baseline for our 15-phase transformation into a production-grade research intelligence platform.
*(Note: Formerly referenced as ScholarPulse AI during initial ideation; rebranded permanently to VERITAS).*

### Factual Baseline Finding
The workspace is currently in an **absolute Day-0 / Greenfield state**:
* **Source Code:** 0 application source files detected.
* **Package Manifests:** No `package.json`, `pyproject.toml`, `requirements.txt`, or `Cargo.toml`.
* **Database & Migrations:** No PostgreSQL schema definitions, ORM models, or migration scripts (Alembic/Prisma).
* **API Endpoints & Routing:** No FastAPI routers, Express endpoints, or Next.js API routes.
* **AI/RAG Infrastructure:** No document parsing pipelines, no vector store client implementations (Qdrant), and no LLM orchestration layers.
* **Version Control:** Git is installed on the host system (`git version 2.55.0.windows.5`), but the workspace directory is not yet initialized as a Git repository.

While a greenfield state lacks pre-existing functional assets, it presents a **strategic architectural advantage**: there is zero legacy code to refactor, zero technical debt embedded in production databases, and zero architectural anti-patterns (such as naive recursive text splitting or unindexed vector stores) requiring remediation. We have the mandate to construct a pristine, production-grade modular monolith from the ground up.

---

## 2. Deep Repository Scan Results

| Inspection Area | Path / Pattern Checked | Factual Finding | Status |
| :--- | :--- | :--- | :--- |
| **Monorepo / Workspace Config** | `pnpm-workspace.yaml`, `turbo.json`, `nx.json` | None found | **Missing** |
| **Frontend Framework** | `package.json`, `tsconfig.json`, `src/`, `app/` | None found | **Missing** |
| **Backend Framework** | `pyproject.toml`, `requirements.txt`, `main.py`, `app/` | None found | **Missing** |
| **Database Schemas** | `alembic/`, `prisma/`, `models/`, `migrations/` | None found | **Missing** |
| **Vector DB Integration** | `qdrant/`, `vector/`, `embeddings/` | None found | **Missing** |
| **Task Queue / Workers** | `celery.py`, `tasks/`, `worker/` | None found | **Missing** |
| **Infrastructure & Docker** | `Dockerfile`, `docker-compose.yml`, `k8s/` | None found | **Missing** |
| **Environment & Secrets** | `.env`, `.env.example`, `.env.local` | None found | **Clean (No Leaks)** |
| **Documentation** | `README.md`, `docs/`, `SPEC.md` | None found | **Baseline Initiated** |

---

## 3. Host Environment & Runtime Inspection

The underlying host environment was audited to verify developer tool readiness:

* **Node.js:** `v24.19.0` (Active LTS runtime available; ready for Next.js 14/15 modern frontend stack).
* **Python:** `Python 3.13.13` (Available on host system; caution required regarding C-extension and PyTorch/vector dependencies on 3.13, virtual environment isolation needed).
* **Git:** `git version 2.55.0.windows.5` (Available; repository initialization required in Phase 1).
* **pnpm:** Not recognized on system PATH (Needs installation via `npm install -g pnpm` or Corepack enablement).
* **Docker Engine:** Not recognized on system PATH / Daemon not accessible in standard terminal. Containerization strategy must account for local native services or Docker Desktop setup for PostgreSQL, Qdrant, and Redis.

---

## 4. Implementation Inventory (Target vs Actual)

| Component Area | Target Production Standard | Current State | Deficit & Implementation Roadmap |
| :--- | :--- | :--- | :--- |
| **Monorepo Structure** | Monorepo structure (`apps/web`, `apps/api`, `packages/shared`) | None | Must scaffold clean project directory layout in Phase 1. |
| **Frontend Platform** | Next.js 14+ (App Router), TypeScript, Tailwind CSS, Shadcn UI | None | Complete scaffold required: UI components, auth wrappers, query hooks. |
| **Backend API** | FastAPI (Async, Pydantic v2, dependency injection, OpenAPI docs) | None | Complete scaffold required: ASGI app, router modules, lifespan managers. |
| **Relational Database** | PostgreSQL 16+ with SQLAlchemy 2.0 (Async) + Alembic migrations | None | Missing all schemas: Users, Tenants, Documents, Citations, Sessions. |
| **Vector Database** | Qdrant client with tenant-partitioned collections & payload indices | None | Missing collections, HNSW index config, distance metrics (Cosine/Dot). |
| **Document Pipeline** | Multi-format layout-aware parser (PDF, ArXiv, EPUB) + table extractor | None | Zero ingestion pipeline; must implement structural parser over naive splitters. |
| **Embedding & RAG** | Dense + Sparse hybrid retrieval, Cross-Encoder reranking, citation mapping | None | Zero retrieval logic; requires end-to-end vector pipeline & evaluation. |
| **Async Task Engine** | Celery + Redis for ingestion queues, dead-letter queues, status polling | None | Document processing currently cannot run asynchronously. |
| **Auth & Security** | JWT / Session auth with strict multi-tenant Row-Level Security | None | No identity or tenancy boundaries established. |

---

## 5. Technical Debt & Architectural Risks

Because this repository is greenfield, "technical debt" in the traditional sense of buggy legacy code does not exist. Instead, the architectural risks are **Foundational Design Risks**:

1. **Host Tooling & Runtime Constraints:**
   * Python 3.13 is extremely new. Certain machine learning wheels (PyTorch, Tokenizers, ONNX, or specific scientific computing packages) frequently encounter binary wheel incompatibilities on Windows for the newest Python minor releases. We must isolate a stable Python virtual environment (e.g., Python 3.11/3.12 if wheels fail, or verified 3.13 wheels).
   * Docker is not currently available on the PATH. PostgreSQL, Redis, and Qdrant must either run via local binaries/services, automated setup scripts, or Docker Desktop must be configured by the host user.
2. **Naive RAG Anti-Pattern Hazard:**
   * In typical academic paper RAG systems, developers default to `RecursiveCharacterTextSplitter` with chunks of 500-1000 tokens. In academic papers, this completely destroys tables, LaTeX formulas, multi-column reading orders, and bibliographic references. We explicitly forbid naive chunking in our architecture.
3. **Tenant Bleed Risk:**
   * Multi-tenancy must be architectural from Day 1. Retrofitting `tenant_id` filtering into vector collections and database tables at Phase 10 is notoriously error-prone and leads to cross-tenant data leaks.

---

## 6. Audit Verdict & Phase 1 Readiness

* **Readiness Status:** **PROCEED TO PHASE 1 (Foundations & Scaffolding)**
* **Prerequisites for Phase 1:**
  1. Initialize Git repository with strict `.gitignore` (ignoring `.env*`, `node_modules`, `venv`, `__pycache__`, `data/`).
  2. Define monorepo directory layout (`apps/web`, `apps/api`, `docs/`, `scripts/`).
  3. Initialize backend virtual environment and configure FastAPI + SQLAlchemy + Alembic scaffolding.
  4. Scaffold Next.js frontend with TypeScript and styling foundations.
