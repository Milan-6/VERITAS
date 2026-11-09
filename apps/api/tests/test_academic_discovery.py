import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.services.discovery import (
    validate_safe_url,
    reconstruct_abstract,
    external_discovery_service,
)
from app.models.document import Document, DocumentProcessingJob, DocumentStatus
from app.models.user import User


MOCK_OPENALEX_RESPONSE = {
    "meta": {"count": 1, "page": 1, "per_page": 10},
    "results": [
        {
            "id": "https://openalex.org/W1234567890",
            "doi": "https://doi.org/10.1145/3456789",
            "title": "Quantum Attention Networks for Natural Language Inference",
            "publication_year": 2024,
            "authorships": [
                {"author": {"display_name": "Dr. Sarah Chen"}},
                {"author": {"display_name": "Prof. Marcus Vance"}},
            ],
            "abstract_inverted_index": {
                "Quantum": [0],
                "attention": [1],
                "networks": [2],
                "demonstrate": [3],
                "quantum": [4],
                "advantage": [5],
                "on": [6],
                "inference": [7],
                "benchmarks.": [8],
            },
            "primary_location": {
                "landing_page_url": "https://doi.org/10.1145/3456789",
                "pdf_url": "https://arxiv.org/pdf/2401.12345.pdf",
                "source": {"display_name": "ACM Computing Surveys"},
            },
            "open_access": {
                "is_oa": True,
                "oa_url": "https://arxiv.org/pdf/2401.12345.pdf",
            },
            "cited_by_count": 84,
            "referenced_works": ["https://openalex.org/W999001"],
            "related_works": ["https://openalex.org/W999002"],
        }
    ],
}


def test_abstract_reconstruction():
    """Verifies that OpenAlex inverted indexes are accurately inverted and concatenated."""
    index = {
        "This": [0],
        "study": [1],
        "evaluates": [2],
        "retrieval": [3],
        "grounding.": [4],
    }
    abstract = reconstruct_abstract(index)
    assert abstract == "This study evaluates retrieval grounding."

    assert reconstruct_abstract(None) is None
    assert reconstruct_abstract({}) is None


def test_ssrf_url_validation_rejections():
    """
    Verifies that validate_safe_url blocks private, loopback, link-local,
    cloud metadata, and non-HTTP protocols.
    """
    # 1. Loopback addresses
    with pytest.raises(HTTPException) as exc1:
        validate_safe_url("http://127.0.0.1/test.pdf")
    assert exc1.value.status_code == 400
    assert "SSRF violation" in exc1.value.detail

    with pytest.raises(HTTPException) as exc2:
        validate_safe_url("http://localhost:8000/private.pdf")
    assert exc2.value.status_code == 400

    # 2. Cloud metadata IP (169.254.169.254)
    with pytest.raises(HTTPException) as exc3:
        validate_safe_url("http://169.254.169.254/latest/meta-data/")
    assert exc3.value.status_code == 400
    assert "SSRF violation" in exc3.value.detail

    # 3. Private IP ranges (RFC 1918)
    with pytest.raises(HTTPException) as exc4:
        validate_safe_url("http://10.0.0.1/secret.pdf")
    assert exc4.value.status_code == 400

    with pytest.raises(HTTPException) as exc5:
        validate_safe_url("http://192.168.1.100/internal.pdf")
    assert exc5.value.status_code == 400

    # 4. Non-HTTP scheme
    with pytest.raises(HTTPException) as exc6:
        validate_safe_url("file:///etc/passwd")
    assert exc6.value.status_code == 400
    assert "Scheme 'file' is forbidden" in exc6.value.detail

    with pytest.raises(HTTPException) as exc7:
        validate_safe_url("ftp://server.com/file.pdf")
    assert exc7.value.status_code == 400

    # 5. Embedded credentials
    with pytest.raises(HTTPException) as exc8:
        validate_safe_url("http://admin:password@attacker.com/paper.pdf")
    assert exc8.value.status_code == 400
    assert "embedded authentication credentials" in exc8.value.detail


def test_external_discovery_search_mocked():
    """
    Verifies that OpenAlex search query normalization maps to unified ExternalPaperMetadata
    without making live network requests.
    """
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = MOCK_OPENALEX_RESPONSE
    mock_response.raise_for_status = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_response

    with patch("httpx.Client", return_value=mock_client):
        res = external_discovery_service.search_works("quantum attention", page=1, per_page=10)

        assert res.query == "quantum attention"
        assert res.total_results == 1
        assert len(res.results) == 1

        paper = res.results[0]
        assert paper.title == "Quantum Attention Networks for Natural Language Inference"
        assert "Dr. Sarah Chen" in paper.authors
        assert paper.publication_year == 2024
        assert paper.doi == "10.1145/3456789"
        assert paper.is_open_access is True
        assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345.pdf"
        assert paper.citation_count == 84
        assert paper.venue == "ACM Computing Surveys"
        assert "Quantum attention networks demonstrate" in paper.abstract


def test_citation_network_mapping_mocked():
    """
    Verifies citation graph traversal for inbound citations, outbound references,
    and related research works.
    """
    mock_client = MagicMock()

    # Setup responses for main work, cited_by, related_to, and references
    def mock_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "https://doi.org/" in url:
            resp.json.return_value = MOCK_OPENALEX_RESPONSE["results"][0]
        elif "cites:" in kwargs.get("params", {}).get("filter", ""):
            resp.json.return_value = {"results": [MOCK_OPENALEX_RESPONSE["results"][0]]}
        elif "related_to:" in kwargs.get("params", {}).get("filter", ""):
            resp.json.return_value = {"results": [MOCK_OPENALEX_RESPONSE["results"][0]]}
        elif "openalex_id:" in kwargs.get("params", {}).get("filter", ""):
            resp.json.return_value = {"results": [MOCK_OPENALEX_RESPONSE["results"][0]]}
        else:
            resp.json.return_value = {"results": []}
        return resp

    mock_client.__enter__.return_value.get.side_effect = mock_get

    with patch("httpx.Client", return_value=mock_client):
        net = external_discovery_service.get_citation_network(
            document_id="doc_test_123",
            document_title="Quantum Attention Networks",
            doi="10.1145/3456789",
        )

        assert net.document_id == "doc_test_123"
        assert net.citation_count == 84
        assert len(net.cited_by) >= 1
        assert len(net.top_related) >= 1
        assert len(net.references) >= 1


def test_direct_ingest_api_ssrf_rejection(client: TestClient, auth_headers: dict):
    """
    Verifies that the /api/v1/discovery/ingest endpoint rejects SSRF URLs with HTTP 400.
    """
    payload = {
        "doi_or_url": "http://127.0.0.1:8080/cloud-credentials.pdf",
    }
    response = client.post("/api/v1/discovery/ingest", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "SSRF violation" in response.json()["detail"]


def create_valid_test_pdf_bytes(title: str = "Test PDF Document") -> bytes:
    """Generate minimal valid PDF bytes with proper %PDF- signature and xref table."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >> endobj\n"
        b"4 0 obj << /Length 55 >> stream\n"
        b"BT /F1 12 Tf 72 712 Td (VERITAS Research Paper: " + title.encode("ascii") + b") Tj ET\n"
        b"endstream\nendobj\n"
        b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000214 00000 n \n"
        b"trailer << /Size 5 /Root 1 0 R >>\nstartxref\n320\n%%EOF"
    )


def test_direct_ingest_paper_flow(client: TestClient, auth_headers: dict, db):
    """
    Verifies successful direct paper ingestion via URL:
    Mocks the remote PDF download, persists document in database, and queues background processing.
    """
    valid_mock_pdf_bytes = create_valid_test_pdf_bytes("Quantum NLP Foundations")

    mock_async_response = MagicMock()
    mock_async_response.status_code = 200
    mock_async_response.content = valid_mock_pdf_bytes

    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.get.return_value = mock_async_response

    # Mock DNS lookup to return a public IP so SSRF check passes
    with patch("httpx.AsyncClient", return_value=mock_async_client), \
         patch("socket.getaddrinfo", return_value=[(2, 1, 0, "", ("93.184.216.34", 443))]):

        payload = {
            "doi_or_url": "https://example.com/papers/quantum_nlp.pdf",
            "title": "Quantum NLP Foundations",
        }
        res = client.post("/api/v1/discovery/ingest", json=payload, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()

        assert data["document_id"] is not None
        assert data["job_id"] is not None
        assert data["title"] == "Quantum NLP Foundations"
        assert data["status"] in ("UPLOADED", "COMPLETED")

        # Verify document exists in database
        doc = db.query(Document).filter(Document.id == data["document_id"]).first()
        assert doc is not None
        assert doc.status in ("UPLOADED", "COMPLETED")
        assert "Quantum NLP Foundations" in doc.doc_metadata.title

        # Verify duplicate ingestion returns existing document
        res_dup = client.post("/api/v1/discovery/ingest", json=payload, headers=auth_headers)
        assert res_dup.status_code == 201
        dup_data = res_dup.json()
        assert dup_data["document_id"] == data["document_id"]
        assert "already exists" in dup_data["message"]
