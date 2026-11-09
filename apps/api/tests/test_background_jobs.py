import io
import time
from test_upload_validation import create_minimal_pdf_bytes


def test_job_status_and_retry(client, auth_headers):
    pdf_bytes = create_minimal_pdf_bytes("Job Status Test Paper")
    files = {"file": ("job_test.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    
    # 1. Upload
    res = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert res.status_code == 201
    doc_id = res.json()["document"]["id"]
    job_id = res.json()["job"]["id"]

    # 2. Check status endpoint
    status_res = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert status_res.status_code == 200
    job_data = status_res.json()
    assert job_data["document_id"] == doc_id
    assert "progress_pct" in job_data
    assert job_data["status"] in ["PENDING", "RUNNING", "COMPLETED"]

    # Give thread worker a moment to complete
    time.sleep(0.5)

    # 3. Check document detail
    detail_res = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["status"] in ["QUEUED", "PROCESSING", "COMPLETED"]

    # 4. Trigger Retry
    retry_res = client.post(f"/api/v1/documents/{doc_id}/retry", headers=auth_headers)
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] in ["PENDING", "RUNNING", "COMPLETED"]


def test_duplicate_upload_prevention(client, auth_headers):
    pdf_bytes = create_minimal_pdf_bytes("Unique Research Paper for Deduplication")
    files1 = {"file": ("unique_paper.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    
    # First upload
    res1 = client.post("/api/v1/documents/upload", headers=auth_headers, files=files1)
    assert res1.status_code == 201
    doc1_id = res1.json()["document"]["id"]

    # Wait for processing
    time.sleep(0.5)

    # Second upload with identical bytes
    files2 = {"file": ("unique_paper_copy.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res2 = client.post("/api/v1/documents/upload", headers=auth_headers, files=files2)
    assert res2.status_code == 201
    assert "already exists" in res2.json()["message"]
    # Re-used existing document ID
    assert res2.json()["document"]["id"] == doc1_id
