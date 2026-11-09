# Technology Decisions & Target Architecture: VERITAS
**Product:** VERITAS  
**Tagline:** Research Intelligence. Grounded in Truth.  
**Phase:** Phase 0 Baseline & Phase 1 Execution  
**Date:** 2026-11-09  
**Role:** Principal Software Architect & Lead Engineer  
**Status:** APPROVED & FROZEN FOR PHASE 1  

---

## 1. Architectural Vision

VERITAS is an enterprise-grade Research Intelligence and Literature Synthesis platform designed to ingest, process, reason over, and cite complex academic literature (PDFs, ArXiv preprints, journals, and technical documentation) with cryptographic traceability, deterministic citation provenance, and sub-second hybrid retrieval.

To achieve production resilience, VERITAS is designed as a **Modular Monolith** with clear bounded contexts, decoupled asynchronous workers, and strict multi-tenant data isolation.

---

## 2. Technology Stack Mapping Matrix

| Layer / Subsystem | Current Baseline | Target Production Stack | Decision Rationale & Technical Justification |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | Greenfield (None) | **Next.js 14/15 (App Router)** | Server-side rendering (SSR) for SEO and initial load speed; React Server Components (RSC) for streaming complex academic analytics; tight TypeScript contract with OpenAPI. |
| **Frontend UI & State** | Greenfield (None) | **Tailwind CSS + Shadcn UI + TanStack Query + Zustand** | High developer velocity; accessible accessible component primitives; robust server-state caching/invalidation for real-time document processing updates. |
| **Backend Framework** | Greenfield (None) | **FastAPI (Python 3.12/3.13)** | Industry-standard async ASGI framework; native Pydantic v2 data validation; auto-generated OpenAPI 3.1 documentation; first-class ecosystem for AI/ML pipelines. |
| **Relational Database** | Greenfield (None) | **PostgreSQL 16+** | Uncompromising ACID compliance; relational integrity for users, organizations, papers, citation graphs; rich `JSONB` support for document parsing metadata. |
| **Database ORM & Client** | Greenfield (None) | **SQLAlchemy 2.0 (Async Engine) + asyncpg** | High-performance asynchronous database driver with strict typing, connection pooling, and resilient transaction management. |
| **Schema Migrations** | Greenfield (None) | **Alembic** | Deterministic, version-controlled schema evolution; automatic migration generation; zero-downtime migration capabilities. |
| **Vector Database** | Greenfield (None) | **Qdrant (Vector Engine)** | Native Rust implementation with exceptional latency; payload-based payload indexing allowing hardware-accelerated filtered search by `tenant_id`, `document_id`, and `year`; native hybrid dense+sparse vectors. |
| **Asynchronous Task Queue** | Greenfield (None) | **Celery + Redis** | Decouples intensive document ingestion, OCR, embedding calculations, and external LLM batch synthesis from the user-facing HTTP request-response cycle. |
| **Document Ingestion Engine** | Greenfield (None) | **Hybrid Layout-Aware Parser (Docling / PyMuPDF + Marker)** | Replaces naive recursive chunking. Accurately preserves two-column academic reading order, tables, mathematical formulas (LaTeX), and bibliography links. |
| **Hybrid Search & Embeddings** | Greenfield (None) | **Dense (BGE-M3 / OpenAI text-embedding-3) + Sparse (BM25 / SPLADE)** | Academic queries frequently contain exact acronyms, chemical formulas, or author names (where dense embeddings fail) combined with conceptual semantic intent (where keyword search fails). Hybrid search solves both. |
| **Reranking Engine** | Greenfield (None) | **FlashRank / BGE-Reranker-Large / Cohere Rerank** | Cross-encoder reranking over top-K retrieval candidates to eliminate hallucinated context and improve NDCG@10 citation precision. |
| **LLM Gateway & Orchestration** | Greenfield (None) | **LiteLLM / Structured Pydantic Outputs** | Unified interface for frontier LLMs (OpenAI, Anthropic Claude 3.5, Google Gemini 1.5 Pro) with automatic fallback, rate limiting, and structured JSON extraction. |

---

## 3. Core Architectural Decisions & Trade-Offs

### 3.1. Architecture Pattern: Modular Monolith vs Microservices
* **Decision:** We adopt a **Modular Monolith** structure (housed in a monorepo) rather than distributed microservices.
* **Rationale:**
  * At Phase 0–5, distributed microservices introduce massive overhead: distributed transactions, network latency, complex observability, and API schema divergence.
  * A modular monolith enforces domain boundaries at the module and package level (`auth`, `documents`, `citations`, `chat`, `analytics`) with in-process function calls, while keeping asynchronous workloads isolated on worker nodes via Celery.
  * When individual domains experience disproportionate load (e.g. document ingestion), Celery workers scale horizontally without re-architecting the web or API layers.

### 3.2. Vector Storage: Qdrant vs pgvector vs Pinecone
* **Decision:** Dedicated **Qdrant** instance.
* **Trade-Off Analysis:**
  * *Why not Pinecone?* Closed-source, vendor lock-in, latency across cloud boundaries, higher long-term cost for high-dimensional payload storage, and compliance friction with private proprietary research.
  * *Why not pgvector?* While convenient for simple vector storage, pgvector suffers under concurrent write/indexing operations, lacks sophisticated payload-based filtering optimizations at massive scale (millions of chunks with deep metadata), and lacks native, first-class sparse-vector (SPLADE/BM25) fusion out-of-the-box compared to Qdrant's hybrid index engine.
  * *Qdrant Advantage:* Qdrant supports payload schema indexes, tenant-based payload partitions, hybrid search (dense + sparse vectors with Reciprocal Rank Fusion), and snapshot backup mechanisms.

### 3.3. Document Parsing: Layout-Aware Parsing vs Naive Recursive Chunking
* **Decision:** **Strictly Forbidden:** Naive character/recursive splitting (`RecursiveCharacterTextSplitter`).
* **Adopted Architecture:** Layout-aware document decomposition pipeline:
  1. **Visual Structure Extraction:** Detection of reading order, headers, section hierarchies, tables, captions, and formulas.
  2. **Semantic Block Boundaries:** Chunks are constructed along natural document boundaries (sections, sub-sections, paragraphs, tables) rather than arbitrary character/token cutoffs.
  3. **Metadata Enrichment:** Each chunk retains hierarchical metadata (`document_id`, `section_title`, `page_number`, `bounding_box`, `tenant_id`, `is_table`).

### 3.4. Database & Tenancy Isolation Pattern
* **Decision:** **Hybrid Shared-Database / Tenant-Keyed Isolation with Row-Level Security (RLS)**.
* **Rationale:**
  * Complete database-per-tenant introduces excessive DevOps friction, migration orchestration complexity, and idle resource costs.
  * Pure application-level filtering (`WHERE tenant_id = ...`) is vulnerable to developer omission bugs.
  * Target Strategy: Every database entity must include an indexed `tenant_id` foreign key, validated at the API middleware layer and enforced via PostgreSQL Row-Level Security (RLS) policies and Qdrant mandatory payload filter clauses.

---

## 4. Repository Scaffolding Blueprint for Phase 1

The following directory layout is formally adopted for execution in Phase 1:

```
d:/Project-1/
├── apps/
│   ├── api/                     # FastAPI Backend Application
│   │   ├── app/
│   │   │   ├── api/             # API Route Handlers (v1)
│   │   │   ├── core/            # Config, Security, Database session
│   │   │   ├── models/          # SQLAlchemy Database Models
│   │   │   ├── schemas/         # Pydantic Request/Response DTOs
│   │   │   ├── services/        # Business Logic & AI Orchestration
│   │   │   └── workers/         # Celery Tasks & Ingestion Pipelines
│   │   ├── alembic/             # Database Migration Scripts
│   │   ├── pyproject.toml       # Python Dependency Manifest
│   │   └── Dockerfile
│   └── web/                     # Next.js Frontend Application
│       ├── src/
│       │   ├── app/             # Next.js App Router (Pages & Layouts)
│       │   ├── components/      # UI & Academic Feature Components
│       │   ├── hooks/           # Custom React & Data Hooks
│       │   ├── lib/             # API Client & Utility Functions
│       │   └── types/           # TypeScript Shared Interfaces
│       ├── package.json         # Node Dependency Manifest
│       ├── tailwind.config.ts
│       └── tsconfig.json
├── docs/                        # Architecture & Planning Documentation
│   ├── ENGINEERING_AUDIT.md
│   ├── TECHNOLOGY_DECISIONS.md
│   └── SECURITY_THREAT_MODEL.md
├── scripts/                     # Local Dev, Seeding, and CI Scripts
└── docker-compose.yml           # Local Orchestration (Postgres, Qdrant, Redis)
```
