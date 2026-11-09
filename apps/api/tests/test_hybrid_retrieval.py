import uuid
from qdrant_client import QdrantClient
from app.services.vector_store import QdrantVectorStore
from app.services.retrieval import HybridRetrievalService
from app.services.chunker import SemanticChunkData


def test_tenant_isolation_in_hybrid_retrieval():
    """
    CRITICAL SECURITY TEST (SEC-01):
    Proves that User A cannot retrieve embedded chunks belonging to User B,
    even when querying with identical semantic and keyword terms.
    """
    test_client = QdrantClient(":memory:")
    collection_name = f"test_retrieval_{uuid.uuid4().hex[:8]}"
    vs = QdrantVectorStore(collection_name=collection_name, client=test_client)
    retriever = HybridRetrievalService(vs=vs)

    # 1. Index User A's private confidential research
    doc_a_id = "doc_secret_alpha"
    chunks_a = [
        SemanticChunkData(
            chunk_id=f"chk_{doc_a_id}_1",
            document_id=doc_a_id,
            page_number=1,
            section_title="Quantum Cryptography",
            subsection="Lattice Schemes",
            context_header="[Document: Classified Quantum Algorithms] [Section: Quantum Cryptography]",
            content_text="Post-quantum lattice cryptography relies on learning with errors problem over ideal rings.",
            embedded_text="[Document: Classified Quantum Algorithms] [Section: Quantum Cryptography]\nPost-quantum lattice cryptography relies on learning with errors problem over ideal rings.",
            token_count=20,
            chunk_index=1,
        )
    ]
    vs.index_chunks(
        tenant_id="tenant_A",
        document_id=doc_a_id,
        document_title="Classified Quantum Algorithms",
        chunks=chunks_a,
    )

    # 2. Index User B's public research
    doc_b_id = "doc_public_beta"
    chunks_b = [
        SemanticChunkData(
            chunk_id=f"chk_{doc_b_id}_1",
            document_id=doc_b_id,
            page_number=1,
            section_title="Renewable Energy",
            subsection=None,
            context_header="[Document: Solar Power Studies] [Section: Renewable Energy]",
            content_text="Perovskite solar cell efficiency has improved to 25.8% under standard test conditions.",
            embedded_text="[Document: Solar Power Studies] [Section: Renewable Energy]\nPerovskite solar cell efficiency has improved to 25.8% under standard test conditions.",
            token_count=18,
            chunk_index=1,
        )
    ]
    vs.index_chunks(
        tenant_id="tenant_B",
        document_id=doc_b_id,
        document_title="Solar Power Studies",
        chunks=chunks_b,
    )

    # 3. User A searches for "post-quantum lattice cryptography"
    results_a = retriever.search(
        query="post-quantum lattice cryptography",
        tenant_id="tenant_A",
        top_k=5,
    )
    assert len(results_a) == 1
    assert results_a[0].document_id == doc_a_id
    assert "lattice cryptography" in results_a[0].content_text
    assert results_a[0].score > 0

    # 4. User B searches for the EXACT same query "post-quantum lattice cryptography"
    results_b = retriever.search(
        query="post-quantum lattice cryptography",
        tenant_id="tenant_B",
        top_k=5,
    )
    # MUST NOT return User A's data under any circumstances (Absolute Tenant Isolation)
    assert len(results_b) == 0
    assert doc_a_id not in [r.document_id for r in results_b]


def test_hybrid_search_api_endpoint(client, auth_headers, auth_headers_2, test_user, test_user_2, db):
    # Upload and index a document via pipeline for User 1
    from test_upload_validation import create_minimal_pdf_bytes
    import io

    pdf_bytes = create_minimal_pdf_bytes("Quantum Fault Tolerance Analysis")
    files = {"file": ("quantum_fault.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    upload_res = client.post("/api/v1/documents/upload", headers=auth_headers, files=files)
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["document"]["id"]

    # Search via API endpoint with User 1 auth
    search_payload = {
        "query": "Quantum Fault Tolerance",
        "top_k": 5,
        "dense_weight": 0.6,
        "sparse_weight": 0.4
    }

    res_user1 = client.post("/api/v1/retrieval/search", headers=auth_headers, json=search_payload)
    assert res_user1.status_code == 200
    data1 = res_user1.json()
    assert data1["query"] == "Quantum Fault Tolerance"
    assert "results" in data1

    # Search via API endpoint with User 2 auth (Attacker)
    res_user2 = client.post("/api/v1/retrieval/search", headers=auth_headers_2, json=search_payload)
    assert res_user2.status_code == 200
    data2 = res_user2.json()
    # Attacker's search must return 0 results for User 1's document!
    user2_doc_ids = [r["document_id"] for r in data2["results"]]
    assert doc_id not in user2_doc_ids
