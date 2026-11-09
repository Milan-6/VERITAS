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
| **Phase 1** | Foundations, Secure Ingestion & Document Processing Engine | **IN PROGRESS** |
| **Phase 2+** | Hybrid Retrieval, Graph Citations, Synthesis & Verification | **PLANNED** (Strictly out of scope for Phase 1) |

---

## Phase 1 Detailed Milestones & Tasks

| Task ID | Milestone / Deliverable | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **P1-M1** | Read Before You Code & Repository Audit | **COMPLETED** | Forensic audit complete; baseline established; git repo initialized. |
| **P1-M2** | Complete Project Rebranding | **COMPLETED** | VERITAS branding applied across docs, metadata, headers, and UI specs. |
| **P1-M3** | Database and Backend Foundation | **IN PROGRESS** | Models: `Document`, `DocumentMetadata`, `DocumentProcessingJob`, `ExtractedPage`, `ExtractedSection`, `ExtractedContent`, `DocumentWorkspaceAssociation`. |
| **P1-M4** | Secure PDF Ingestion & Storage | **PENDING** | Magic byte validation, size limits, SHA-256 integrity, secure storage API. |
| **P1-M5** | PDF Extraction Pipeline | **PENDING** | Layout-aware parser (PyMuPDF/PyPDF fallback), metadata extraction, section recognition, page provenance. |
| **P1-M6** | Background Processing | **PENDING** | Asynchronous task queue, worker job management, status tracking, retries, failure handling. |
| **P1-M7** | Frontend Integration | **PENDING** | Upload interface, drag-and-drop, document library, detail views, real status polling. |
| **P1-M8** | Testing and Security Verification | **PENDING** | Unit tests, validation tests, auth tests, extraction tests, end-to-end integration tests. |
| **P1-M9** | Git Management & Documentation | **PENDING** | Atomic commits, README.md, Phase 1 Implementation Report, clean git log. |
