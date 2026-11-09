import uuid
import pytest
from app.models.document import Document, DocumentMetadata, DocumentStatus
from app.services.academic_extraction import academic_extraction_service
from app.services.literature_matrix import literature_matrix_service
from app.services.chunker import SemanticChunkData
from app.services.vector_store import vector_store


def test_structured_academic_extraction_service(db, test_user):
    # 1. Create document and chunks for User
    doc_id = f"doc_synth_{uuid.uuid4().hex[:8]}"
    chunks = [
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_1",
            document_id=doc_id,
            page_number=1,
            section_title="1 Introduction",
            subsection=None,
            context_header="[Document: Graph Synthesis] [Section: 1 Introduction]",
            content_text="The foundational problem in citation graph analysis is severe relational sparseness.",
            embedded_text="[Document: Graph Synthesis] [Section: 1 Introduction]\nThe foundational problem in citation graph analysis is severe relational sparseness.",
            token_count=18,
            chunk_index=1,
        ),
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_2",
            document_id=doc_id,
            page_number=2,
            section_title="2 Methodology",
            subsection="Neural Graph Relations",
            context_header="[Document: Graph Synthesis] [Section: 2 Methodology]",
            content_text="We propose a relational graph neural network architecture using attention-weighted edge updates.",
            embedded_text="[Document: Graph Synthesis] [Section: 2 Methodology]\nWe propose a relational graph neural network architecture using attention-weighted edge updates.",
            token_count=19,
            chunk_index=2,
        ),
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_3",
            document_id=doc_id,
            page_number=3,
            section_title="3 Experiments",
            subsection="Datasets",
            context_header="[Document: Graph Synthesis] [Section: 3 Experiments]",
            content_text="We evaluated our approach on the benchmark Cora citation corpus containing 2708 scientific publications.",
            embedded_text="[Document: Graph Synthesis] [Section: 3 Experiments]\nWe evaluated our approach on the benchmark Cora citation corpus containing 2708 scientific publications.",
            token_count=20,
            chunk_index=3,
        ),
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_4",
            document_id=doc_id,
            page_number=4,
            section_title="4 Results",
            subsection="Metrics",
            context_header="[Document: Graph Synthesis] [Section: 4 Results]",
            content_text="Our method achieves an optimal 94.2% precision on citation link prediction benchmarks.",
            embedded_text="[Document: Graph Synthesis] [Section: 4 Results]\nOur method achieves an optimal 94.2% precision on citation link prediction benchmarks.",
            token_count=18,
            chunk_index=4,
        ),
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_5",
            document_id=doc_id,
            page_number=5,
            section_title="5 Discussion",
            subsection="Limitations",
            context_header="[Document: Graph Synthesis] [Section: 5 Discussion]",
            content_text="A primary limitation is that computational overhead increases quadratically with citation graph density.",
            embedded_text="[Document: Graph Synthesis] [Section: 5 Discussion]\nA primary limitation is that computational overhead increases quadratically with citation graph density.",
            token_count=19,
            chunk_index=5,
        ),
    ]

    vector_store.index_chunks(
        tenant_id=test_user.id,
        document_id=doc_id,
        document_title="Graph Synthesis",
        chunks=chunks,
    )

    synthesis = academic_extraction_service.synthesize_paper(
        document_id=doc_id,
        tenant_id=test_user.id,
        document_title="Graph Synthesis",
    )

    # Verify 5 structured dimensions are extracted
    assert synthesis.document_id == doc_id
    assert synthesis.problem_statement.topic == "Problem Statement"
    assert "sparseness" in synthesis.problem_statement.summary.lower() or len(synthesis.problem_statement.summary) > 10

    assert synthesis.methodology.topic == "Methodology"
    assert "neural" in synthesis.methodology.summary.lower() or "architecture" in synthesis.methodology.summary.lower()

    assert synthesis.dataset_used.topic == "Dataset Used"
    assert "cora" in synthesis.dataset_used.summary.lower() or "corpus" in synthesis.dataset_used.summary.lower()

    assert synthesis.key_results.topic == "Key Results"
    assert "94.2%" in synthesis.key_results.summary or "precision" in synthesis.key_results.summary.lower()

    assert synthesis.limitations.topic == "Limitations"
    assert "overhead" in synthesis.limitations.summary.lower() or "computational" in synthesis.limitations.summary.lower()


def test_tenant_isolation_in_literature_matrix(client, auth_headers, auth_headers_2, test_user, test_user_2, db):
    """
    CRITICAL SECURITY TEST (SEC-01):
    Proves that a user cannot generate a comparative matrix using documents belonging
    to another user/tenant.
    """
    # 1. User 1 creates Document 1
    doc_user1 = Document(
        user_id=test_user.id,
        filename="user1_private_paper.pdf",
        storage_path="/tmp/doc1.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256=f"hash1_{uuid.uuid4().hex[:8]}",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc_user1)

    # 2. User 2 creates Document 2 and Document 3
    doc_user2_a = Document(
        user_id=test_user_2.id,
        filename="user2_paper_a.pdf",
        storage_path="/tmp/doc2a.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256=f"hash2a_{uuid.uuid4().hex[:8]}",
        status=DocumentStatus.COMPLETED.value,
    )
    doc_user2_b = Document(
        user_id=test_user_2.id,
        filename="user2_paper_b.pdf",
        storage_path="/tmp/doc2b.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256=f"hash2b_{uuid.uuid4().hex[:8]}",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc_user2_a)
    db.add(doc_user2_b)
    db.commit()

    # 3. User 2 attempts to generate a matrix comparing their paper with User 1's private paper
    matrix_payload = {
        "document_ids": [doc_user2_a.id, doc_user1.id],
        "topic_query": "Comparative Evaluation"
    }

    res = client.post("/api/v1/analysis/matrix", headers=auth_headers_2, json=matrix_payload)
    # MUST BE REJECTED with 403 Forbidden or 404 Not Found
    assert res.status_code in [403, 404]


def test_cross_paper_matrix_generation_and_contradiction_detection(client, auth_headers, test_user, db):
    # 1. Create 2 completed documents for User 1
    doc_a = Document(
        user_id=test_user.id,
        filename="gnn_citation.pdf",
        storage_path="/tmp/gnn.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        file_hash_sha256=f"hash_gnn_{uuid.uuid4().hex[:8]}",
        status=DocumentStatus.COMPLETED.value,
    )
    doc_b = Document(
        user_id=test_user.id,
        filename="sparse_transformer.pdf",
        storage_path="/tmp/sparse.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        file_hash_sha256=f"hash_sparse_{uuid.uuid4().hex[:8]}",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc_a)
    db.add(doc_b)
    db.commit()

    meta_a = DocumentMetadata(
        document_id=doc_a.id,
        title="Relational Graph Reasoning in Citations",
        total_pages=5,
    )
    meta_b = DocumentMetadata(
        document_id=doc_b.id,
        title="Sparse Transformer Attention Networks",
        total_pages=6,
    )
    db.add(meta_a)
    db.add(meta_b)
    db.commit()

    # 2. Index distinct chunks for Doc A (Graph Neural Network, 94.2% precision)
    chunks_a = [
        SemanticChunkData(
            chunk_id=f"chk_mat_a_1",
            document_id=doc_a.id,
            page_number=2,
            section_title="Methodology",
            subsection=None,
            context_header="[Document: Relational Graph Reasoning] [Section: Methodology]",
            content_text="We deploy a deep graph neural network for citation edge prediction.",
            embedded_text="[Document: Relational Graph Reasoning] [Section: Methodology]\nWe deploy a deep graph neural network for citation edge prediction.",
            token_count=18,
            chunk_index=1,
        ),
        SemanticChunkData(
            chunk_id=f"chk_mat_a_2",
            document_id=doc_a.id,
            page_number=4,
            section_title="Results",
            subsection=None,
            context_header="[Document: Relational Graph Reasoning] [Section: Results]",
            content_text="The relational model delivers a 94.2% precision score on the benchmark.",
            embedded_text="[Document: Relational Graph Reasoning] [Section: Results]\nThe relational model delivers a 94.2% precision score on the benchmark.",
            token_count=18,
            chunk_index=2,
        ),
    ]
    vector_store.index_chunks(
        tenant_id=test_user.id,
        document_id=doc_a.id,
        document_title="Relational Graph Reasoning in Citations",
        chunks=chunks_a,
    )

    # 3. Index distinct chunks for Doc B (Sparse Transformer, 78.5% precision)
    chunks_b = [
        SemanticChunkData(
            chunk_id=f"chk_mat_b_1",
            document_id=doc_b.id,
            page_number=2,
            section_title="Methodology",
            subsection=None,
            context_header="[Document: Sparse Transformer Attention] [Section: Methodology]",
            content_text="We introduce a sparse transformer attention block to eliminate quadratic token complexity.",
            embedded_text="[Document: Sparse Transformer Attention] [Section: Methodology]\nWe introduce a sparse transformer attention block to eliminate quadratic token complexity.",
            token_count=20,
            chunk_index=1,
        ),
        SemanticChunkData(
            chunk_id=f"chk_mat_b_2",
            document_id=doc_b.id,
            page_number=4,
            section_title="Results",
            subsection=None,
            context_header="[Document: Sparse Transformer Attention] [Section: Results]",
            content_text="The transformer achieves a 78.5% precision score on the benchmark.",
            embedded_text="[Document: Sparse Transformer Attention] [Section: Results]\nThe transformer achieves a 78.5% precision score on the benchmark.",
            token_count=18,
            chunk_index=2,
        ),
    ]
    vector_store.index_chunks(
        tenant_id=test_user.id,
        document_id=doc_b.id,
        document_title="Sparse Transformer Attention Networks",
        chunks=chunks_b,
    )

    # 4. Call Single Document Summary API
    summary_res = client.get(f"/api/v1/analysis/summary/{doc_a.id}", headers=auth_headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert summary_data["document_id"] == doc_a.id
    assert "problem_statement" in summary_data
    assert "methodology" in summary_data
    assert "dataset_used" in summary_data
    assert "key_results" in summary_data
    assert "limitations" in summary_data

    # 5. Call Matrix Comparison API
    matrix_res = client.post(
        "/api/v1/analysis/matrix",
        headers=auth_headers,
        json={"document_ids": [doc_a.id, doc_b.id], "topic_query": "Methodology comparison"}
    )
    assert matrix_res.status_code == 200
    mat_data = matrix_res.json()
    assert mat_data["document_count"] == 2
    assert len(mat_data["columns"]) == 2

    # Verify column fields populated
    col_a = mat_data["columns"][0]
    col_b = mat_data["columns"][1]
    assert len(col_a["methodology"]) > 0
    assert len(col_b["methodology"]) > 0

    # Verify divergence / contradiction detected (Graph vs Transformer and 94.2% vs 78.5%)
    assert len(mat_data["contradictions_and_divergences"]) >= 1
    divergence_aspects = [c["aspect"] for c in mat_data["contradictions_and_divergences"]]
    assert any("Methodological" in asp or "Metric" in asp for asp in divergence_aspects)
