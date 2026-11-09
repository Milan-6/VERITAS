import io
import pytest


def create_minimal_pdf_bytes(title: str = "Test PDF Document") -> bytes:
    """Generate minimal valid PDF bytes with proper %PDF- signature."""
    pdf_content = (
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
    return pdf_content


def test_upload_valid_pdf(client, auth_headers):
    pdf_bytes = create_minimal_pdf_bytes("Quantum Computing Breakthrough")
    files = {"file": ("quantum_research.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    
    response = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert "document" in data
    assert data["document"]["filename"] == "quantum_research.pdf"
    assert data["document"]["file_size_bytes"] == len(pdf_bytes)
    assert data["document"]["status"] in ["UPLOADED", "QUEUED", "PROCESSING", "COMPLETED"]
    assert "job" in data
    assert data["job"]["id"] is not None


def test_upload_unauthorized_fails(client):
    pdf_bytes = create_minimal_pdf_bytes()
    files = {"file": ("unauth.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 401


def test_upload_invalid_extension_fails(client, auth_headers):
    files = {"file": ("malicious.exe", io.BytesIO(b"%PDF-malicious-content"), "application/pdf")}
    response = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 400
    assert "Invalid file extension" in response.json()["detail"]


def test_upload_invalid_mime_type_fails(client, auth_headers):
    pdf_bytes = create_minimal_pdf_bytes()
    files = {"file": ("research.pdf", io.BytesIO(pdf_bytes), "text/plain")}
    response = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 400
    assert "Invalid MIME type" in response.json()["detail"]


def test_upload_empty_file_fails(client, auth_headers):
    files = {"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 400
    assert "Empty file rejected" in response.json()["detail"]


def test_upload_missing_magic_bytes_fails(client, auth_headers):
    # File named .pdf with application/pdf MIME, but payload lacks %PDF- header
    fake_pdf = b"NOT_A_PDF_HEADER_JUST_RANDOM_TEXT"
    files = {"file": ("corrupt.pdf", io.BytesIO(fake_pdf), "application/pdf")}
    response = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert response.status_code == 400
    assert "Malformed file" in response.json()["detail"]


def test_batch_upload(client, auth_headers):
    pdf1 = create_minimal_pdf_bytes("Paper 1")
    pdf2 = create_minimal_pdf_bytes("Paper 2")

    files = [
        ("files", ("paper1.pdf", io.BytesIO(pdf1), "application/pdf")),
        ("files", ("paper2.pdf", io.BytesIO(pdf2), "application/pdf")),
    ]
    response = client.post("/api/v1/documents/upload-batch", headers=auth_headers, files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["total_uploaded"] == 2
    assert len(data["successful"]) == 2
    assert len(data["failed"]) == 0
