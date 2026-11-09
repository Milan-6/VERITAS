# VERITAS: Phase Tracking & Implementation Roadmap
**Product Name:** VERITAS  
**Tagline:** Research Intelligence. Grounded in Truth.  
**Former Name:** ScholarPulse AI (Permanently Retired)  
**Last Updated:** 2026-11-09  

---

## Phase Overview

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | Baseline Audit, Architecture & Threat Modeling | **COMPLETED** |
| **Phase 1** | Foundations, Secure Ingestion & Document Processing Engine | **COMPLETED** |
| **Phase 2+** | Hybrid Retrieval, Graph Citations, Synthesis & Verification | **PLANNED** (Strictly out of scope for Phase 1) |

---

## Phase 1 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P1-M1** | Read Before You Code & Repository Audit | **COMPLETED** | Forensic audit complete; baseline established; host tooling verified (Python 3.13, Node 24, Git 2.55); git repository initialized with strict `.gitignore`. |
| **P1-M2** | Complete Project Rebranding | **COMPLETED** | Complete rebranding from "ScholarPulse AI" to **VERITAS** across all architecture specs, threat models, database models, API titles, and UI components. Tagline: *"Research Intelligence. Grounded in Truth."* |
| **P1-M3** | Database and Backend Foundation | **COMPLETED** | Implemented SQLAlchemy 2.0 models (`Document`, `DocumentMetadata`, `DocumentProcessingJob`, `ExtractedPage`, `ExtractedSection`, `ExtractedContent`, `DocumentWorkspaceAssociation`, `User`, `Workspace`). Configured Alembic and applied initial migration (`c87e726d540a_initial_phase1_schema.py`). Strict multi-tenant authorization guard implemented in `core/security.py`. |
| **P1-M4** | Secure PDF Ingestion & Storage | **COMPLETED** | Implemented `StorageService` validating file extension, MIME type, `%PDF-` magic bytes, 50MB file size limits, 0-byte rejections, and SHA-256 integrity hashing. Secure isolated UUID storage. Endpoints: `POST /upload`, `POST /upload-batch`, `GET /documents`, `GET /documents/{id}`, `DELETE /documents/{id}`, `GET /documents/{id}/download`. |
| **P1-M5** | PDF Extraction Pipeline | **COMPLETED** | Built `PDFParserService` using PyMuPDF (fitz) with `pypdf` fallback. Layout-aware parsing extracts Title, Authors, Abstract, Keywords, DOI, Sections, Subsections, Paragraphs, Tables, Figure captions, Math expressions, and References. Deterministic page-level provenance chunking preserving bounding box coordinates (`x0`, `y0`, `x1`, `y1`). |
| **P1-M6** | Background Processing | **COMPLETED** | Built `BackgroundJobManager` with asynchronous worker pool. Full lifecycle state tracking: `UPLOADED` → `QUEUED` → `PROCESSING` → `COMPLETED` / `FAILED`. Real-time status polling endpoint (`GET /documents/{id}/status`), retry endpoint (`POST /documents/{id}/retry`), duplicate prevention, and detailed error logging. |
| **P1-M7** | Frontend Integration | **COMPLETED** | Next.js 14 App Router platform with deep navy/charcoal styling and cyan accents. Drag-and-drop upload modal with real-time upload progress, document catalog with live status polling, detail drawer with metadata, section hierarchy, page metrics, and provenance chunk inspector. Compiled with 0 errors (`npm run build`). |
| **P1-M8** | Testing and Security Verification | **COMPLETED** | Automated test suite in `apps/api/tests/`: 18 tests executed and 18 PASSED (0 failures). Covers auth, upload validation, magic bytes, empty/oversized files, IDOR cross-user protection, PyMuPDF layout extraction, background job transitions, and deduplication. |
| **P1-M9** | Git Management & Documentation | **COMPLETED** | Atomic Git commits per milestone; created comprehensive `README.md`, `.env.example`, `docker-compose.yml`, and `docs/VERITAS_PHASE_1_IMPLEMENTATION_REPORT.md`. |
