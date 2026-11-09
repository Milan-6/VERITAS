import io
import uuid
import pytest
from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage
from app.services.chunker import SemanticChunkData
from app.services.vector_store import vector_store
from tests.test_upload_validation import create_minimal_pdf_bytes


def test_chat_session_creation_and_listing(client, auth_headers, auth_headers_2, test_user, test_user_2):
    # 1. User 1 creates session
    res1 = client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"title": "Quantum Computing Analysis"}
    )
    assert res1.status_code == 201
    session_data1 = res1.json()
    assert session_data1["title"] == "Quantum Computing Analysis"
    assert session_data1["user_id"] == test_user.id
    session_id1 = session_data1["id"]

    # 2. User 2 creates session
    res2 = client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers_2,
        json={"title": "Photosynthesis In Plants"}
    )
    assert res2.status_code == 201
    session_id2 = res2.json()["id"]

    # 3. List sessions for User 1: MUST NOT see User 2's session (Tenant Isolation)
    list_res1 = client.get("/api/v1/chat/sessions", headers=auth_headers)
    assert list_res1.status_code == 200
    user1_session_ids = [s["id"] for s in list_res1.json()]
    assert session_id1 in user1_session_ids
    assert session_id2 not in user1_session_ids

    # 4. List sessions for User 2: MUST NOT see User 1's session
    list_res2 = client.get("/api/v1/chat/sessions", headers=auth_headers_2)
    assert list_res2.status_code == 200
    user2_session_ids = [s["id"] for s in list_res2.json()]
    assert session_id2 in user2_session_ids
    assert session_id1 not in user2_session_ids


def test_tenant_isolation_in_chat_sessions(client, auth_headers, auth_headers_2, test_user, test_user_2):
    """
    CRITICAL SECURITY TEST (SEC-01):
    Proves User 2 cannot access, read, or post messages to User 1's ChatSession.
    """
    # 1. User 1 creates a private research session
    res = client.post(
        "/api/v1/chat/sessions",
        headers=auth_headers,
        json={"title": "Confidential Drug Discovery"}
    )
    assert res.status_code == 201
    user1_session_id = res.json()["id"]

    # 2. User 2 attempts to read User 1's session -> Must be 403 Forbidden or 404
    get_res = client.get(f"/api/v1/chat/sessions/{user1_session_id}", headers=auth_headers_2)
    assert get_res.status_code in [403, 404]

    # 3. User 2 attempts to send a message into User 1's session -> Must be 403 Forbidden or 404
    post_res = client.post(
        f"/api/v1/chat/sessions/{user1_session_id}/messages",
        headers=auth_headers_2,
        json={"content": "Attempting cross-tenant data injection"}
    )
    assert post_res.status_code in [403, 404]

    # 4. User 2 attempts to delete User 1's session -> Must be 403 Forbidden or 404
    del_res = client.delete(f"/api/v1/chat/sessions/{user1_session_id}", headers=auth_headers_2)
    assert del_res.status_code in [403, 404]


def test_grounded_chat_response_and_inline_citations(client, auth_headers, test_user, db):
    """
    Verifies that when relevant research exists in the corpus, the assistant returns
    a grounded response citing [Document: X, Page: Y] with metadata.
    """
    # 1. Index document and chunk for User 1
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    chunks = [
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_1",
            document_id=doc_id,
            page_number=3,
            section_title="4 Results",
            subsection="Accuracy Metrics",
            context_header="[Document: Transformer Efficiency] [Section: 4 Results]",
            content_text="The sparse transformer architecture achieves an optimal perplexity score of 14.8 on the benchmark corpus.",
            embedded_text="[Document: Transformer Efficiency] [Section: 4 Results]\nThe sparse transformer architecture achieves an optimal perplexity score of 14.8 on the benchmark corpus.",
            token_count=20,
            chunk_index=1,
        )
    ]
    vector_store.index_chunks(
        tenant_id=test_user.id,
        document_id=doc_id,
        document_title="Transformer Efficiency",
        chunks=chunks,
    )

    # 2. Create Chat Session
    sess_res = client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Perplexity Study"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # 3. Ask question regarding the indexed research
    msg_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "What perplexity score does the sparse transformer achieve?"}
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    # Grounded assertion
    assert "14.8" in msg_data["content"]
    assert "[Document: Transformer Efficiency, Page: 3]" in msg_data["content"]
    assert len(msg_data["citations"]) >= 1
    assert msg_data["citations"][0]["document_title"] == "Transformer Efficiency"
    assert msg_data["citations"][0]["page_number"] == 3


def test_strict_abstention_on_out_of_scope_query(client, auth_headers, test_user):
    """
    ZERO-TOLERANCE FOR HALLUCINATION TEST:
    Verifies that when a question cannot be answered from the retrieved context,
    the assistant returns EXACTLY the mandated fallback string.
    """
    # 1. Create Session
    sess_res = client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Abstention Verification"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # 2. Ask completely out-of-scope question with zero evidence in corpus
    msg_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "What is the secret recipe for dark chocolate soufflé cake?"}
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"

    # MANDATED EXACT ABSTENTION STRING
    expected_abstention = "This is not mentioned in the provided research corpus."
    assert msg_data["content"] == expected_abstention
    # No citations when abstaining
    assert msg_data["citations"] == []


def test_chat_session_history_and_deletion(client, auth_headers, test_user):
    # 1. Create Session
    sess_res = client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Multi-turn Session"})
    session_id = sess_res.json()["id"]

    # 2. Send first message
    client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "Hello research assistant"}
    )

    # 3. Retrieve session detail
    detail_res = client.get(f"/api/v1/chat/sessions/{session_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["messages"]) == 2  # user + assistant

    # 4. Delete session
    del_res = client.delete(f"/api/v1/chat/sessions/{session_id}", headers=auth_headers)
    assert del_res.status_code == 204

    # 5. Verify deleted
    get_after_del = client.get(f"/api/v1/chat/sessions/{session_id}", headers=auth_headers)
    assert get_after_del.status_code == 404
