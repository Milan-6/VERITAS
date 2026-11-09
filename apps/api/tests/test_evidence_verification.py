import uuid
import pytest
from app.core.config import settings
from app.services.verification import ClaimExtractor, EvidenceVerifier
from app.services.chunker import SemanticChunkData
from app.services.retrieval import RetrievedChunk
from app.services.vector_store import vector_store


def test_atomic_claim_extraction_decomposition():
    extractor = ClaimExtractor()

    # Test 1: Complex paragraph with contrastive conjunction
    text = "The model achieved 95% accuracy on dataset X, but struggled with noisy data."
    claims = extractor.extract_claims(text)
    assert len(claims) == 2
    assert "95% accuracy on dataset X" in claims[0]
    assert "Struggled with noisy data" in claims[1] or "struggled with noisy data" in claims[1].lower()

    # Test 2: Text containing inline citations [Document: X, Page: Y]
    cited_text = (
        "Neural citation networks achieve 94.2% precision on benchmark datasets [Document: Neural Graph Reasoning, Page: 2]. "
        "The relational graph embedding preserves citation provenance across multi-hop reasoning [Document: Neural Graph Reasoning, Page: 1]."
    )
    extracted_cited = extractor.extract_claims(cited_text)
    assert len(extracted_cited) == 2
    # Ensure citation markers are stripped from the atomic claims themselves
    assert "[Document:" not in extracted_cited[0]
    assert "[Document:" not in extracted_cited[1]
    assert "94.2% precision" in extracted_cited[0]

    # Test 3: Bypass for strict abstention fallback string
    abstain_text = settings.STRICT_ABSTENTION_MESSAGE
    abstain_claims = extractor.extract_claims(abstain_text)
    assert abstain_claims == []


def test_evidence_verifier_entailment_classification():
    verifier = EvidenceVerifier()

    test_chunk = RetrievedChunk(
        chunk_id="chk_test_101",
        document_id="doc_transformer_01",
        document_title="Sparse Attention Mechanisms",
        page_number=4,
        section_title="4 Empirical Results",
        subsection="Perplexity Benchmarks",
        content_text="The sparse transformer architecture achieves an optimal perplexity score of 14.8 on the benchmark corpus, representing a state-of-the-art precision improvement.",
        score=0.92,
        dense_score=0.95,
        sparse_score=0.88,
    )
    chunks = [test_chunk]

    # 1. Test SUPPORTED claim
    supported_claim = "The sparse transformer architecture achieves an optimal perplexity score of 14.8."
    res_sup = verifier.verify_claim(supported_claim, chunks)
    assert res_sup.status == "SUPPORTED"
    assert res_sup.document_title == "Sparse Attention Mechanisms"
    assert res_sup.page_number == 4
    assert res_sup.chunk_id == "chk_test_101"
    assert "optimal perplexity score of 14.8" in res_sup.source_excerpt

    # 2. Test CONTRADICTED claim
    contradicted_claim = "The sparse transformer architecture failed and struggled with benchmark corpus."
    res_con = verifier.verify_claim(contradicted_claim, chunks)
    assert res_con.status == "CONTRADICTED"
    assert "contradict" in res_con.reasoning.lower()

    # 3. Test MISSING claim (out-of-scope / ungrounded assertion)
    missing_claim = "The solar irradiance of perovskite cells degrades rapidly under ultraviolet exposure."
    res_mis = verifier.verify_claim(missing_claim, chunks)
    assert res_mis.status == "MISSING"


def test_verification_report_end_to_end_generation():
    verifier = EvidenceVerifier()

    test_chunk = RetrievedChunk(
        chunk_id="chk_test_202",
        document_id="doc_bio_02",
        document_title="CRISPR Off-Target Analysis",
        page_number=2,
        section_title="Methodology",
        subsection=None,
        content_text="High-fidelity Cas9 variants demonstrate an 87% reduction in off-target genomic cleavage events.",
        score=0.89,
        dense_score=0.91,
        sparse_score=0.85,
    )

    # Generated response containing 1 supported claim and 1 ungrounded missing claim
    response_text = (
        "High-fidelity Cas9 variants demonstrate an 87% reduction in off-target cleavage [Document: CRISPR Off-Target Analysis, Page: 2]. "
        "The treatment also guarantees 100% cure rates in human clinical trials."
    )

    report = verifier.generate_report(response_text, [test_chunk])
    assert report.overall_status in ["PARTIALLY_VERIFIED", "VERIFIED"]
    assert report.supported_count >= 1
    assert len(report.claims) == 2

    # Verify abstention produces ABSTAINED report
    abstain_report = verifier.generate_report(settings.STRICT_ABSTENTION_MESSAGE, [test_chunk])
    assert abstain_report.overall_status == "ABSTAINED"
    assert len(abstain_report.claims) == 0


def test_chat_api_returns_verification_report(client, auth_headers, test_user):
    """
    Integration test proving that POST /api/v1/chat/sessions/{id}/messages
    persists and returns the structured VerificationReport in the HTTP response.
    """
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    chunks = [
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_1",
            document_id=doc_id,
            page_number=1,
            section_title="1 Introduction",
            subsection=None,
            context_header="[Document: Quantum Algorithms] [Section: 1 Introduction]",
            content_text="Shor's algorithm factors integers in polynomial time using quantum Fourier transform.",
            embedded_text="[Document: Quantum Algorithms] [Section: 1 Introduction]\nShor's algorithm factors integers in polynomial time using quantum Fourier transform.",
            token_count=18,
            chunk_index=1,
        )
    ]
    vector_store.index_chunks(
        tenant_id=test_user.id,
        document_id=doc_id,
        document_title="Quantum Algorithms",
        chunks=chunks,
    )

    # Create session
    sess_res = client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Quantum Study"})
    assert sess_res.status_code == 201
    session_id = sess_res.json()["id"]

    # Send message
    msg_res = client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        headers=auth_headers,
        json={"content": "How does Shor's algorithm factor integers?"}
    )
    assert msg_res.status_code == 201
    data = msg_res.json()

    # Assert VerificationReport structure is populated
    assert "verification_report" in data
    v_report = data["verification_report"]
    assert v_report is not None
    assert v_report["overall_status"] in ["VERIFIED", "PARTIALLY_VERIFIED"]
    assert len(v_report["claims"]) >= 1
    assert v_report["claims"][0]["status"] == "SUPPORTED"
    assert v_report["claims"][0]["document_title"] == "Quantum Algorithms"
