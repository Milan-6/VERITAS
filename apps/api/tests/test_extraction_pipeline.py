import os
import tempfile
import fitz
import pytest

from app.services.pdf_parser import pdf_parser_service
from app.services.processing_pipeline import processing_pipeline
from app.models.document import Document, DocumentProcessingJob, DocumentStatus, JobStatus


def generate_rich_academic_pdf(file_path: str):
    """Generate a rich, structured academic PDF using PyMuPDF."""
    doc = fitz.open()

    # Page 1: Title, Authors, Abstract, Introduction
    page1 = doc.new_page(width=612, height=792)
    p1_text = (
        "Neural Graph Reasoning over Academic Citations\n\n"
        "Dr. Jane Doe, Prof. Alan Turing, Dr. Richard Feynman\n\n"
        "DOI: 10.1145/3318464.3389700\n\n"
        "Abstract\n\n"
        "We present a novel neural architecture for reasoning over academic citation graphs. "
        "Our method achieves state-of-the-art results on scientific literature synthesis.\n\n"
        "Keywords: Graph Neural Networks, Citation Graphs, Literature Synthesis\n\n"
        "1 Introduction\n\n"
        "Academic literature is expanding at an exponential rate. Researchers require automated tools "
        "grounded in deterministic evidence.\n\n"
        "1.1 Prior Work\n\n"
        "Previous approaches relied on naive chunking which severed semantic context between citations."
    )
    page1.insert_text((54, 72), p1_text, fontsize=11)

    # Page 2: Methodology, Math, Results, References
    page2 = doc.new_page(width=612, height=792)
    p2_text = (
        "2 Methodology\n\n"
        "Given a document graph G = (V, E), we define node embeddings using the following relation:\n"
        "\\sum_{i=1}^{n} w_i \\cdot h_i = \\sigma(W x + b)\n\n"
        "Figure 1: High-level overview of the VERITAS neural architecture.\n\n"
        "3 Results and Discussion\n\n"
        "Our system yields a 94.2% precision on citation provenance benchmarks.\n\n"
        "References\n\n"
        "[1] Vaswani et al. Attention Is All You Need. NeurIPS, 2017.\n"
        "[2] Devlin et al. BERT: Pre-training of Deep Bidirectional Transformers. NAACL, 2019."
    )
    page2.insert_text((54, 72), p2_text, fontsize=11)

    doc.save(file_path)
    doc.close()


def test_pdf_parsing_structure_and_metadata():
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        generate_rich_academic_pdf(tmp_path)
        doc_id = "test-doc-uuid-001"
        result = pdf_parser_service.parse_pdf(tmp_path, doc_id)

        assert result.total_pages == 2
        assert len(result.pages) == 2
        assert "Neural Graph" in result.title
        assert result.doi == "10.1145/3318464.3389700"
        assert result.abstract is not None
        assert "novel neural architecture" in result.abstract

        # Verify sections detected
        section_titles = [s.section_title for s in result.sections]
        assert any("Abstract" in s for s in section_titles)
        assert any("Introduction" in s for s in section_titles)
        assert any("Methodology" in s for s in section_titles)
        assert any("Results" in s for s in section_titles)
        assert any("References" in s for s in section_titles)

        # Verify chunks have provenance fields
        assert len(result.contents) > 0
        for chunk in result.contents:
            assert chunk.chunk_id.startswith(f"doc_{doc_id}_")
            assert chunk.page_number in [1, 2]
            assert chunk.extraction_method == "pymupdf_layout"
            assert chunk.bounding_box is not None
            assert len(chunk.source_text) > 0

        # Verify math expression detection
        math_chunks = [c for c in result.contents if c.content_type == "math_expression"]
        assert len(math_chunks) >= 1

        # Verify figure caption detection
        fig_chunks = [c for c in result.contents if c.content_type == "figure_caption"]
        assert len(fig_chunks) >= 1

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_processing_pipeline_execution(db, test_user):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        generate_rich_academic_pdf(tmp_path)

        # Create Document and Job in DB
        doc = Document(
            user_id=test_user.id,
            filename="neural_graph_reasoning.pdf",
            storage_path=tmp_path,
            file_size_bytes=os.path.getsize(tmp_path),
            mime_type="application/pdf",
            file_hash_sha256="test-sha256-hash-val",
            status=DocumentStatus.QUEUED.value,
        )
        db.add(doc)
        db.flush()

        job = DocumentProcessingJob(
            document_id=doc.id,
            status=JobStatus.PENDING.value,
        )
        db.add(job)
        db.commit()

        # Run pipeline
        success = processing_pipeline.process_document_job(job.id, db=db)
        assert success is True

        db.refresh(doc)
        db.refresh(job)

        assert doc.status == DocumentStatus.COMPLETED.value
        assert job.status == JobStatus.COMPLETED.value
        assert job.progress_pct == 100.0

        # Verify metadata persisted in DB
        assert doc.doc_metadata is not None
        assert "Neural Graph" in doc.doc_metadata.title
        assert doc.doc_metadata.total_pages == 2
        assert doc.doc_metadata.doi == "10.1145/3318464.3389700"

        # Verify extracted pages and chunks persisted in DB
        assert len(doc.extracted_pages) == 2
        assert len(doc.extracted_sections) >= 4
        assert len(doc.extracted_contents) > 0

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
