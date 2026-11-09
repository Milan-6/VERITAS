# VERITAS
> **Research Intelligence. Grounded in Truth.**

[![Phase 1 Status](https://img.shields.io/badge/Phase%201-COMPLETED-00E5FF?style=flat-square)](docs/PHASE_TRACKER.md)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14.2-black?style=flat-square)](https://nextjs.org)
[![Tests](https://img.shields.io/badge/Tests-18%20Passed-emerald?style=flat-square)](apps/api/tests)

---

## 1. Overview

**VERITAS** is an enterprise-grade research intelligence and literature synthesis platform designed to ingest, decompose, reason over, and cite complex academic literature (PDFs, preprints, journal articles, and technical documentation) with cryptographic traceability, deterministic citation provenance, and strict multi-tenant isolation.

*(Note: Formerly referenced during early ideation as ScholarPulse AI, which is permanently retired).*

---

## 2. Phase 1 Architecture & Capabilities

Phase 1 establishes the production-grade foundation for document ingestion, decomposition, and state tracking:

```
[ User Browser / Client ]
           │ (HTTPS / Multipart Upload)
           ▼
┌────────────────────────────────────────────────────────┐
│  Next.js 14 Web Frontend (App Router, Tailwind CSS)    │
│  - Drag-and-drop file ingestion (Single & Batch)       │
│  - Real-time progress tracking & status polling        │
│  - Literature catalog & Provenance Chunk Inspector    │
└─────────────────────────┬──────────────────────────────┘
                          │ (REST API / Bearer Token)
                          ▼
┌────────────────────────────────────────────────────────┐
│  FastAPI Backend Core                                  │
│  - File signature validation (%PDF- magic bytes)       │
│  - SHA-256 cryptographic hashing & deduplication       │
│  - Multi-tenant tenant/workspace authorization guard   │
│  - Asynchronous background worker queue                │
└────────────┬────────────────────────────┬──────────────┘
             │                            │
             ▼                            ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│ Database (SQLAlchemy 2.0) │  │ Layout Ingestion Engine │
│ - Alembic Versioned DDL   │  │ - PyMuPDF (fitz)        │
│ - Documents, Metadata     │  │ - Section recognition   │
│ - Provenance Chunks       │  │ - Bounding box mapping  │
│ - Extracted Pages         │  │ - Math & Figure parsing │
└───────────────────────────┘  └─────────────────────────┘
```

### Key Technical Capabilities Implemented
* **Secure PDF Ingestion:**
  * File extension, MIME type, and magic bytes (`%PDF-`) verification.
  * Size quota enforcement (50MB maximum), rejecting empty (0-byte) or corrupted payloads.
  * Isolated storage using UUID paths to prevent directory traversal and script execution.
  * SHA-256 deduplication to prevent redundant processing.
* **Layout-Aware PDF Extraction:**
  * PyMuPDF layout analysis preserving multi-column academic reading order.
  * Structural extraction: Title, Authors, Abstract, Keywords, DOI, Sections, Subsections, Paragraphs, Tables, Figure captions, and Mathematical expressions.
  * Strict page-level provenance: `document_id`, `page_number`, `section`, `subsection`, `chunk_id`, `extraction_method`, and `bounding_box` coordinates (`x0`, `y0`, `x1`, `y1`).
* **Asynchronous Background Processing:**
  * Multi-worker thread pool executing extraction decoupled from the HTTP cycle.
  * State lifecycle: `UPLOADED` → `QUEUED` → `PROCESSING` → `COMPLETED` / `FAILED`.
  * Automatic attempt tracking, error logging, and retry APIs.
* **Multi-Tenant Security:**
  * Application-level workspace isolation and document ownership verification.
  * Defense against IDOR and cross-user data leakage.
* **Modern Scientific UI:**
  * Next.js 14 App Router with deep navy/charcoal styling and restrained cyan accents.
  * Real-time upload progress, polling telemetry, and detailed provenance chunk inspection.

---

## 3. Directory Layout

```
d:/Project-1/
├── apps/
│   ├── api/                     # FastAPI Backend Application
│   │   ├── app/
│   │   │   ├── api/v1/          # REST route handlers (auth, documents)
│   │   │   ├── core/            # Config, Database session, Security
│   │   │   ├── models/          # SQLAlchemy ORM models (Alembic managed)
│   │   │   ├── schemas/         # Pydantic DTO request/response schemas
│   │   │   ├── services/        # Storage validation, PyMuPDF parser, Pipeline
│   │   │   └── workers/         # Background job manager & queue
│   │   ├── alembic/             # Version-controlled database migrations
│   │   ├── tests/               # Pytest test suite (18 automated tests)
│   │   └── pyproject.toml
│   └── web/                     # Next.js Frontend Application
│       ├── src/
│       │   ├── app/             # Next.js App Router (page, layout, globals)
│       │   ├── components/      # UI components (Header, Upload, Catalog, Detail)
│       │   ├── lib/             # API client & token storage
│       │   └── types/           # TypeScript interfaces
│       ├── package.json
│       └── tailwind.config.ts
├── docs/                        # Engineering & Architecture documentation
│   ├── ENGINEERING_AUDIT.md
│   ├── PHASE_TRACKER.md
│   ├── SECURITY_THREAT_MODEL.md
│   ├── TECHNOLOGY_DECISIONS.md
│   └── VERITAS_PHASE_1_IMPLEMENTATION_REPORT.md
├── uploads/                     # Isolated document storage (gitignored)
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 4. Getting Started

### 4.1. Prerequisites
* Python 3.11+ (Python 3.13 tested)
* Node.js 18+ (v24.19.0 tested)
* Git

### 4.2. Backend Setup
```bash
# 1. Install dependencies
cd apps/api
pip install -r requirements.txt # or pip install -e .

# 2. Run database migrations
python -m alembic upgrade head

# 3. Start FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`

### 4.3. Frontend Setup
```bash
# 1. Install dependencies
cd apps/web
npm install

# 2. Start Next.js development server
npm run dev
```
Web platform will be accessible at: `http://localhost:3000`

---

## 5. Verification & Testing

The backend includes a comprehensive automated test suite covering upload validation, extraction accuracy, multi-tenant authorization, and asynchronous background jobs.

To run the test suite:
```bash
python -m pytest apps/api/tests -v
```

### Verified Test Results (18/18 Passing):
* `test_auth.py`:
  * Healthcheck endpoint verification (`GET /health`)
  * User registration and token issuance (`POST /api/v1/auth/register`)
  * Duplicate email prevention
  * Password verification and authentication (`POST /api/v1/auth/login`)
  * Profile retrieval (`GET /api/v1/auth/me`)
* `test_upload_validation.py`:
  * Valid PDF acceptance and checksum verification
  * Unauthorized upload rejection (401)
  * Invalid file extension rejection (.exe, .txt)
  * Incorrect MIME type rejection
  * Empty 0-byte file rejection
  * Corrupted file / missing `%PDF-` signature rejection
  * Batch file upload verification
* `test_authorization.py`:
  * IDOR prevention: User B cannot retrieve User A's document (404)
  * Deletion prevention: User B cannot delete User A's document (404)
  * Workspace listing isolation: User B's catalog never leaks User A's documents
* `test_extraction_pipeline.py`:
  * PyMuPDF layout analysis over multi-page academic PDF
  * Metadata extraction: Title, Authors, Abstract, Keywords, DOI (`10.1145/...`)
  * Section recognition (Abstract, Introduction, Methodology, Results, References)
  * Mathematical expression and figure caption classification
  * Bounding box preservation and provenance chunk generation
* `test_background_jobs.py`:
  * Background queue transition (`PENDING` → `RUNNING` → `COMPLETED`)
  * Real-time polling endpoint (`GET /api/v1/documents/{id}/status`)
  * Retry execution endpoint (`POST /api/v1/documents/{id}/retry`)
  * Duplicate file upload deduplication via SHA-256
