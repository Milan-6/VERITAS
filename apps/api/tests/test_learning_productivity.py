import csv
import io
import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.chunk import SemanticChunk
from app.models.document import Document, DocumentMetadata, DocumentStatus
from app.models.learning import FlashcardDeck, Flashcard, Quiz
from app.models.user import User
from app.services.learning import learning_service


def test_flashcard_generation_and_grounded_provenance(db: Session, test_user: User):
    """
    Verifies that the LearningService generates conceptual flashcards with
    strict page-level citations and saves them into FlashcardDeck and Flashcard tables.
    """
    tenant_id = test_user.id

    # 1. Create document
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_id,
        workspace_id=f"workspace_{tenant_id}",
        filename="neural_attention.pdf",
        storage_path="/tmp/neural_attention.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256="hash_learn_001",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Neural Attention Mechanisms in Deep Learning",
        authors=["Vaswani et al."],
        abstract="We introduce Multi-Head Attention to replace recurrent layers in sequence transduction.",
    )
    db.add(meta)

    # 2. Add chunks with explicit page numbers and definitions
    chunks = [
        SemanticChunk(
            id=str(uuid.uuid4()),
            chunk_id=f"{doc.id}_chunk_0",
            document_id=doc.id,
            user_id=tenant_id,
            chunk_index=0,
            content_text="We introduce Multi-Head Attention, which allows the model to jointly attend to information from different representation subspaces at different positions.",
            embedded_text="We introduce Multi-Head Attention...",
            context_header="[Document: Attention] [Section: 3.2 Multi-Head Attention]",
            token_count=28,
            page_number=4,
            section_title="Multi-Head Attention",
        ),
        SemanticChunk(
            id=str(uuid.uuid4()),
            chunk_id=f"{doc.id}_chunk_1",
            document_id=doc.id,
            user_id=tenant_id,
            chunk_index=1,
            content_text="Positional Encoding is defined as fixed sinusoidal embeddings added to the input representations to inject sequence order.",
            embedded_text="Positional Encoding is defined as...",
            context_header="[Document: Attention] [Section: 3.5 Positional Encoding]",
            token_count=22,
            page_number=6,
            section_title="Positional Encoding",
        ),
        SemanticChunk(
            id=str(uuid.uuid4()),
            chunk_id=f"{doc.id}_chunk_2",
            document_id=doc.id,
            user_id=tenant_id,
            chunk_index=2,
            content_text="On the WMT 2014 English-to-German translation task, the model achieves a BLEU score of 28.4, outperforming existing ensembles.",
            embedded_text="On the WMT 2014 task...",
            context_header="[Document: Attention] [Section: 5 Results]",
            token_count=25,
            page_number=8,
            section_title="Results",
        ),
    ]
    for c in chunks:
        db.add(c)
    db.commit()

    # 3. Generate flashcards
    deck = learning_service.generate_flashcards(doc.id, tenant_id, db)
    assert deck is not None
    assert deck.document_id == doc.id
    assert deck.tenant_id == tenant_id
    assert len(deck.cards) >= 10
    assert deck.card_count == len(deck.cards)

    # 4. Verify provenance
    first_card = deck.cards[0]
    assert first_card.front_concept is not None
    assert len(first_card.front_concept) > 0
    assert first_card.back_definition is not None
    assert first_card.source_citation is not None
    assert "[Document:" in first_card.source_citation
    assert "Page:" in first_card.source_citation
    assert first_card.page_number in [4, 6, 8, 1]


def test_diagnostic_quiz_generation_and_evaluation(db: Session, test_user: User):
    """
    Verifies that LearningService generates a 5-question diagnostic MCQ quiz
    and correctly calculates score, percentage, and explanations during evaluation.
    """
    tenant_id = test_user.id

    # 1. Create document & chunk
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_id,
        workspace_id=f"workspace_{tenant_id}",
        filename="sparse_transformer.pdf",
        storage_path="/tmp/sparse_transformer.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256="hash_learn_002",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Generating Long Sequences with Sparse Transformers",
        authors=["Child et al."],
        abstract="Factorized self-attention reduces complexity from O(N^2) to O(N sqrt(N)).",
    )
    db.add(meta)

    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=tenant_id,
        chunk_index=0,
        content_text="Factorized sparse attention reduces attention computational complexity from quadratic O(N^2) to O(N sqrt(N)).",
        embedded_text="Factorized sparse attention...",
        context_header="[Document: Sparse Transformer] [Section: Complexity]",
        token_count=20,
        page_number=3,
        section_title="Complexity Analysis",
    )
    db.add(chunk)
    db.commit()

    # 2. Generate Quiz
    quiz = learning_service.generate_quiz(doc.id, tenant_id, db)
    assert quiz is not None
    assert quiz.document_id == doc.id
    assert len(quiz.questions) == 5
    assert quiz.total_questions == 5

    # 3. Verify question structure
    q0 = quiz.questions[0]
    assert "question_id" in q0
    assert "question_text" in q0
    assert len(q0["options"]) == 4
    assert q0["correct_answer"] in q0["options"]
    assert "explanation" in q0
    assert q0["page_number"] == 3
    assert "[Document:" in q0["source_citation"]

    # 4. Evaluate Quiz with 100% correct answers
    all_correct_answers = {q["question_id"]: q["correct_answer"] for q in quiz.questions}
    eval_perfect = learning_service.evaluate_quiz(quiz.id, tenant_id, all_correct_answers, db)
    assert eval_perfect.score == 5
    assert eval_perfect.total_questions == 5
    assert eval_perfect.percentage == 100.0
    for r in eval_perfect.results:
        assert r.is_correct is True

    # 5. Evaluate Quiz with 1 wrong answer (4/5 = 80%)
    partial_answers = dict(all_correct_answers)
    first_qid = quiz.questions[0]["question_id"]
    # Provide wrong option
    wrong_opt = next(opt for opt in quiz.questions[0]["options"] if opt != quiz.questions[0]["correct_answer"])
    partial_answers[first_qid] = wrong_opt

    eval_partial = learning_service.evaluate_quiz(quiz.id, tenant_id, partial_answers, db)
    assert eval_partial.score == 4
    assert eval_partial.percentage == 80.0
    r0 = next(r for r in eval_partial.results if r.question_id == first_qid)
    assert r0.is_correct is False
    assert r0.correct_answer == quiz.questions[0]["correct_answer"]


def test_anki_csv_export_format(db: Session, test_user: User):
    """
    Verifies that the Anki export format adheres to standard CSV specifications,
    includes Anki directives (#separator, #html, #tags), and quotes definition content.
    """
    tenant_id = test_user.id

    # Create document & chunk
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_id,
        workspace_id=f"workspace_{tenant_id}",
        filename="flash_attention.pdf",
        storage_path="/tmp/flash_attention.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256="hash_learn_003",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="FlashAttention: Fast and Memory-Efficient Exact Attention",
        authors=["Dao et al."],
        abstract="Tiling and IO-awareness for fast exact attention.",
    )
    db.add(meta)

    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=tenant_id,
        chunk_index=0,
        content_text="FlashAttention is an architecture that uses SRAM tiling to reduce HBM memory access from O(N^2) to O(N).",
        embedded_text="FlashAttention...",
        context_header="[Document: FlashAttention] [Section: Introduction]",
        token_count=24,
        page_number=2,
        section_title="Introduction",
    )
    db.add(chunk)
    db.commit()

    # Generate and export
    learning_service.generate_flashcards(doc.id, tenant_id, db)
    csv_str = learning_service.export_deck_to_anki_csv(doc.id, tenant_id, db)

    assert csv_str is not None
    assert "#separator:Comma" in csv_str
    assert "#html:true" in csv_str
    assert "#tags column:3" in csv_str
    assert "Front,Back,Citation,Page" in csv_str

    # Parse with standard csv.reader to verify RFC compliance
    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    assert len(rows) >= 5  # metadata headers + card rows


def test_tenant_isolation_in_learning_suite(client, auth_headers, auth_headers_2, test_user, test_user_2, db: Session):
    """
    CRITICAL SECURITY TEST (SEC-01):
    Proves User 2 cannot generate, view, export flashcards, or generate/view quizzes
    for a document belonging to User 1.
    """
    tenant_1 = test_user.id
    tenant_2 = test_user_2.id

    # 1. User 1 creates private document
    doc_1 = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_1,
        workspace_id=f"workspace_{tenant_1}",
        filename="confidential_patent_research.pdf",
        storage_path="/tmp/confidential_patent_research.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        file_hash_sha256="hash_learn_sec_01",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc_1)
    db.flush()

    meta_1 = DocumentMetadata(
        document_id=doc_1.id,
        title="Confidential Quantum Encryption",
        authors=["Tenant 1 Principal Investigator"],
        abstract="Proprietary key exchange protocol.",
    )
    db.add(meta_1)

    chunk_1 = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc_1.id}_chunk_0",
        document_id=doc_1.id,
        user_id=tenant_1,
        chunk_index=0,
        content_text="Our quantum key distribution achieves 99.9% entropy under adversarial noise.",
        embedded_text="Our quantum key...",
        context_header="[Document: Confidential] [Section: QKD]",
        token_count=18,
        page_number=1,
        section_title="QKD",
    )
    db.add(chunk_1)
    db.commit()

    # User 1 generates flashcards & quiz
    learning_service.generate_flashcards(doc_1.id, tenant_1, db)
    learning_service.generate_quiz(doc_1.id, tenant_1, db)

    # 2. User 2 attempts to generate flashcards for User 1's doc -> 404
    res_gen_fc = client.post(
        f"/api/v1/learning/flashcards/generate/{doc_1.id}",
        headers=auth_headers_2,
    )
    assert res_gen_fc.status_code == 404

    # 3. User 2 attempts to get flashcards for User 1's doc -> 404
    res_get_fc = client.get(
        f"/api/v1/learning/flashcards/{doc_1.id}",
        headers=auth_headers_2,
    )
    assert res_get_fc.status_code == 404

    # 4. User 2 attempts to export flashcards for User 1's doc -> 404
    res_export = client.get(
        f"/api/v1/learning/flashcards/{doc_1.id}/export",
        headers=auth_headers_2,
    )
    assert res_export.status_code == 404

    # 5. User 2 attempts to generate quiz for User 1's doc -> 404
    res_gen_quiz = client.post(
        f"/api/v1/learning/quiz/generate/{doc_1.id}",
        headers=auth_headers_2,
    )
    assert res_gen_quiz.status_code == 404

    # 6. User 2 attempts to get quiz for User 1's doc -> 404
    res_get_quiz = client.get(
        f"/api/v1/learning/quiz/{doc_1.id}",
        headers=auth_headers_2,
    )
    assert res_get_quiz.status_code == 404


def test_learning_api_endpoints_end_to_end(client, auth_headers, test_user, db: Session):
    """
    Verifies the end-to-end HTTP API routes for flashcards, Anki export,
    and quiz evaluation using TestClient.
    """
    tenant_id = test_user.id

    # Create document
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_id,
        workspace_id=f"workspace_{tenant_id}",
        filename="diffusion_models.pdf",
        storage_path="/tmp/diffusion_models.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256="hash_learn_e2e_01",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Denoising Diffusion Probabilistic Models",
        authors=["Ho et al."],
        abstract="High-quality image generation using diffusion probabilistic models.",
    )
    db.add(meta)

    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=tenant_id,
        chunk_index=0,
        content_text="The forward process is defined as a Markov chain adding Gaussian noise according to variance schedule beta_t.",
        embedded_text="The forward process...",
        context_header="[Document: Diffusion] [Section: Background]",
        token_count=22,
        page_number=2,
        section_title="Background",
    )
    db.add(chunk)
    db.commit()

    # 1. POST generate flashcards
    fc_res = client.post(
        f"/api/v1/learning/flashcards/generate/{doc.id}",
        headers=auth_headers,
    )
    assert fc_res.status_code == 201
    deck_data = fc_res.json()
    assert deck_data["document_id"] == doc.id
    assert len(deck_data["cards"]) >= 10

    # 2. GET flashcards
    get_fc_res = client.get(
        f"/api/v1/learning/flashcards/{doc.id}",
        headers=auth_headers,
    )
    assert get_fc_res.status_code == 200
    assert get_fc_res.json()["id"] == deck_data["id"]

    # 3. GET Anki export
    export_res = client.get(
        f"/api/v1/learning/flashcards/{doc.id}/export",
        headers=auth_headers,
    )
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers["content-type"]
    assert "attachment" in export_res.headers.get("content-disposition", "")
    assert len(export_res.text) > 0

    # 4. POST generate quiz
    quiz_res = client.post(
        f"/api/v1/learning/quiz/generate/{doc.id}",
        headers=auth_headers,
    )
    assert quiz_res.status_code == 201
    quiz_data = quiz_res.json()
    assert quiz_data["document_id"] == doc.id
    assert len(quiz_data["questions"]) == 5
    quiz_id = quiz_data["id"]

    # 5. POST evaluate quiz
    sample_answers = {
        quiz_data["questions"][0]["question_id"]: quiz_data["questions"][0]["correct_answer"]
    }
    eval_res = client.post(
        f"/api/v1/learning/quiz/{quiz_id}/evaluate",
        headers=auth_headers,
        json={"answers": sample_answers},
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["quiz_id"] == quiz_id
    assert eval_data["score"] == 1
    assert eval_data["total_questions"] == 5
    assert eval_data["percentage"] == 20.0
