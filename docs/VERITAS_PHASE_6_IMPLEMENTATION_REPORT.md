# VERITAS: Phase 6 Implementation Report
**Document Version:** 1.0.0  
**Phase:** Phase 6 — Academic Research Discovery & Citation Networks  
**Product Name:** VERITAS  
**Tagline:** Research Intelligence. Grounded in Truth.  
**Execution Timestamp:** 2026-11-09  

---

## 1. Executive Summary

Phase 6 expands **VERITAS** beyond locally stored research documents by integrating global academic discovery and automated paper ingestion. Researchers can now query over 250 million scientific publications via OpenAlex, map citation networks (inbound citations, outbound references, and related literature), and import Open Access papers directly into their private workspace with a single click or by DOI.

Key capabilities introduced:
1. **Global Literature Discovery Service (`ExternalDiscoveryService`):**
   - High-throughput OpenAlex client supporting search by keyword, title, author, and publication year.
   - Polite pool rate-limit compliance with automated `mailto` parameters and descriptive `User-Agent` headers.
   - Automatic abstract reconstruction from OpenAlex inverted index payloads.
   - In-memory TTL caching (5-minute window) for search queries and works metadata to prevent redundant API calls.
2. **SSRF-Defended Direct Ingestion Pipeline:**
   - Multi-layer Server-Side Request Forgery (SSRF) defense engine validating all target URLs before network retrieval.
   - Strict scheme enforcement (HTTP/HTTPS only), hostname sanity checks, and full DNS resolution against RFC 1918 private IPs, loopback, link-local (cloud IMDS `169.254.169.254`), multicast, and reserved ranges.
   - Resolves DOIs to verified Open Access PDF endpoints.
   - Enforces PDF magic bytes signature (`%PDF-`) and maximum upload size limits (50 MB).
   - Automatically seeds document metadata and queues the document directly into the Phase 1/Phase 2 processing pipeline (validation, PyMuPDF parsing, semantic chunking, and vector embedding) under the active user's workspace/tenant.
3. **Citation Network Graph Traversal:**
   - Programmatically derives inbound citations (`cites:`), outbound references (`referenced_works`), and co-occurrence recommendations (`related_to:`) for any workspace or discovered paper.
4. **Next.js Global Discovery Interface:**
   - Standalone "Global Discovery" navigation tab with keyword search, author/year filters, and direct DOI/URL import bar.
   - Paper cards displaying open-access badges, citation counts, venue, authors, and expandable abstracts.
   - One-click "Import to Workspace" button with real-time progress indicators.
   - Interactive Citation Graph Modal for examining citation provenance and related literature.
   - Added a "Citation Graph" tab inside `DocumentDetailView` for local workspace documents.

---

## 2. Architecture & Discovery Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             VERITAS Frontend                                │
│   • Global Discovery Tab: Search 250M+ Works, Filter by Author/Year         │
│   • One-Click Ingestion & DOI Import Bar                                    │
│   • Citation Network Modal: References, Citing Works & Recommendations      │
│   • Document Detail View: Local Document Citation Graph Tab                 │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Discovery Router                          │
│   • GET  /api/v1/discovery/search (query, page, per_page, author, year)     │
│   • POST /api/v1/discovery/ingest (doi_or_url, workspace_id, title)        │
│   • GET  /api/v1/discovery/citations/{document_id}                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                   ┌───────────────────┴───────────────────┐
                   ▼                                       ▼
┌─────────────────────────────────────┐ ┌─────────────────────────────────────┐
│      ExternalDiscoveryService       │ │        SSRF Defense Engine          │
│ • OpenAlex works API integration    │ │ • Scheme Check (http/https only)    │
│ • Inverted index abstract decoder   │ │ • Hostname blacklist (localhost)   │
│ • In-memory TTL Cache (300s)        │ │ • DNS resolution check via socket   │
│ • Citation mapping (cites, related) │ │ • IP block: 127/8, 10/8, 172.16/12, │
│ • DOI resolution to OA PDF URLs     │ │   192.168/16, 169.254.169.254 (IMDS)│
└─────────────────────────────────────┘ └─────────────────────────────────────┘
                   │                                       │
                   └───────────────────┬───────────────────┘
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Secure Direct Ingestion Pipeline                       │
│   • Streaming download with size limit (<50MB) and 15s timeout              │
│   • Magic bytes signature check (%PDF-)                                     │
│   • StorageService UUID isolation & SHA-256 deduplication                   │
│   • Automatic Document & DocumentProcessingJob creation                     │
│   • Background pipeline execution (PyMuPDF -> Chunker -> Vector Embeddings) │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. SSRF Mitigation Strategies & Security Analysis

Direct server-side downloading of user-specified URLs introduces severe Server-Side Request Forgery (SSRF) vulnerabilities, specifically attacks targeting internal cloud metadata services (e.g., AWS/GCP/Azure IMDS at `169.254.169.254`) or internal VPC microservices.

**Defensive Controls Enforced in `validate_safe_url`:**
1. **Protocol Restriction:** Rejects non-HTTP protocols (`file://`, `ftp://`, `gopher://`, `dict://`).
2. **Credential Sanitization:** Rejects URLs containing userinfo components (`http://admin:secret@host/`).
3. **Hostname Filtering:** Rejects `localhost`, `0.0.0.0`, `127.0.0.1`, `::1`, and domains ending in `.local`, `.internal`, or `.lan`.
4. **Pre-Flight DNS Resolution & Address Validation:**
   - Every hostname is resolved via `socket.getaddrinfo(hostname, None)` prior to initiating HTTP requests.
   - All resolved IP addresses are inspected using Python's standard `ipaddress` module:
     ```python
     if (
         ip.is_private
         or ip.is_loopback
         or ip.is_link_local
         or ip.is_reserved
         or ip.is_multicast
         or ip.is_unspecified
     ):
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail=f"SSRF violation: Host '{hostname}' resolves to restricted network IP '{ip_str}'."
         )
     ```
5. **Streaming Size Limit & Signature Verification:**
   - Downloads enforce a 15-second timeout and 50MB ceiling.
   - Files failing the `%PDF-` magic bytes check are rejected before storage.

---

## 4. External API Data Mappings

OpenAlex data models are mapped into the unified VERITAS `ExternalPaperMetadata` schema:
* `id` $\leftarrow$ OpenAlex work ID (e.g. `https://openalex.org/W2741809807`)
* `title` $\leftarrow$ `work.title`
* `authors` $\leftarrow$ `[a.author.display_name for a in work.authorships]`
* `publication_year` $\leftarrow$ `work.publication_year`
* `abstract` $\leftarrow$ Reconstructed from `work.abstract_inverted_index` by token position mapping
* `doi` $\leftarrow$ Extracted and stripped of URL prefix
* `landing_page_url` $\leftarrow$ `work.primary_location.landing_page_url`
* `pdf_url` $\leftarrow$ `work.best_oa_location.pdf_url` or `work.primary_location.pdf_url`
* `is_open_access` $\leftarrow$ `work.open_access.is_oa or bool(pdf_url)`
* `citation_count` $\leftarrow$ `work.cited_by_count`
* `venue` $\leftarrow$ `work.primary_location.source.display_name`

---

## 5. Automated Verification & Test Results

The test suite was expanded with 6 dedicated test cases in `apps/api/tests/test_academic_discovery.py`:
1. `test_abstract_reconstruction`: Validates accurate inverted index abstract decoding.
2. `test_ssrf_url_validation_rejections`: Tests blocking of loopback, RFC 1918 private IPs, link-local IMDS `169.254.169.254`, file/ftp schemes, and embedded credentials.
3. `test_external_discovery_search_mocked`: Unit test verifying OpenAlex API search response parsing, polite headers, and schema mapping without making live external requests.
4. `test_citation_network_mapping_mocked`: Validates inbound citations, outbound references, and related research recommendations.
5. `test_direct_ingest_api_ssrf_rejection`: Integration test verifying HTTP 400 Bad Request on SSRF injection attempts through the API.
6. `test_direct_ingest_paper_flow`: End-to-end integration test validating mocked PDF download, storage persistence, metadata extraction, background queue processing, and duplicate upload prevention.

**Pytest Execution Summary:**
* **Total Tests:** 44 passed (100% success rate across all phases).
* **Execution Time:** ~3.25 seconds (synchronous, hermetic, zero external rate-limit dependencies).

**Frontend Production Build:**
* `npm run build` compiled cleanly (4/4 routes statically generated, 0 TypeScript or lint errors).

---

## 6. Known Limitations

1. **Paywalled Literature:** Papers without Open Access licenses (`is_open_access: false`) cannot be downloaded directly via automated pipeline; users must upload their institutionally licensed PDFs manually through the Document Catalog.
2. **Polite Pool Compliance:** OpenAlex API requests are directed to the public polite pool using the configured `OPENALEX_MAILTO` parameter. High-volume enterprise installations should provide an OpenAlex Premium API key if rate limits exceed 100,000 calls/day.

---

## 7. Next Phase: Phase 7 Roadmap

With Phase 6 complete, VERITAS is prepared for **Phase 7: Knowledge Graph & Scientific Entity Extraction**:
* Named Entity Recognition (NER) for scientific methods, datasets, benchmarks, and metrics.
* Neo4j or SQLite/PostgreSQL-based knowledge graph nodes and relationships.
* Cross-paper entity resolution and interactive graph visualization.
