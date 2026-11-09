import io
from test_upload_validation import create_minimal_pdf_bytes


def test_cross_user_document_access_prevented(client, auth_headers, auth_headers_2):
    # 1. User A uploads a document
    pdf_bytes = create_minimal_pdf_bytes("Confidential Research")
    files = {"file": ("confidential.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    upload_res = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document"]["id"]

    # 2. User A can access it
    res_a = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert res_a.status_code == 200
    assert res_a.json()["id"] == doc_id

    # 3. User B attempts unauthorized access (IDOR attack SEC-06)
    res_b = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers_2)
    assert res_b.status_code == 404  # 404 prevents enumeration / info leak

    # 4. User B attempts unauthorized deletion
    res_del_b = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers_2)
    assert res_del_b.status_code == 404

    # 5. User B document listing does not include User A's document
    res_list_b = client.get("/api/v1/documents", headers=auth_headers_2)
    assert res_list_b.status_code == 200
    b_doc_ids = [d["id"] for d in res_list_b.json()]
    assert doc_id not in b_doc_ids

    # 6. User A can delete their own document
    res_del_a = client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
    assert res_del_a.status_code == 204
