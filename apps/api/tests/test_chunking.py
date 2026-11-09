from dataclasses import dataclass
from app.services.chunker import SectionAwareChunker


@dataclass
class MockContentNode:
    page_number: int
    section: str
    subsection: str | None
    source_text: str
    content_type: str = "paragraph"


def test_section_aware_chunking_preserves_context_and_provenance():
    chunker = SectionAwareChunker(target_tokens=50, overlap_tokens=15)

    nodes = [
        MockContentNode(
            page_number=1,
            section="1 Introduction",
            subsection=None,
            source_text="Scientific literature synthesis requires verifiable evidence grounded in source texts. Naive chunking destroys citation links."
        ),
        MockContentNode(
            page_number=1,
            section="1 Introduction",
            subsection="1.1 Prior Work",
            source_text="Prior work focused on character count splitting. This severed tables and mathematical formulas without provenance."
        ),
        MockContentNode(
            page_number=2,
            section="2 Methodology",
            subsection=None,
            source_text="Our neural graph architecture defines embeddings over the document graph G = (V, E). Formula: \\sum_{i=1}^n w_i h_i = \\sigma(W x + b)."
        ),
    ]

    chunks = chunker.chunk_extracted_nodes(
        document_id="doc_test_123",
        document_title="VERITAS Neural Architecture",
        extracted_contents=nodes,
    )

    assert len(chunks) >= 3

    # Verify provenance on all chunks
    for idx, chunk in enumerate(chunks, start=1):
        assert chunk.document_id == "doc_test_123"
        assert chunk.chunk_id.startswith("chk_doc_test_123_")
        assert chunk.page_number in [1, 2]
        assert chunk.section_title in ["1 Introduction", "2 Methodology"]
        assert chunk.chunk_index == idx
        # Context breadcrumb must be prepended
        assert "[Document: VERITAS Neural Architecture]" in chunk.embedded_text
        assert "[Section:" in chunk.embedded_text


def test_chunking_overlap_and_sentence_integrity():
    chunker = SectionAwareChunker(target_tokens=15, overlap_tokens=5)

    # Multi-sentence paragraph
    text = (
        "First sentence establishes the research premise. "
        "Second sentence introduces the novel formulation. "
        "Third sentence demonstrates experimental superiority. "
        "Fourth sentence discusses asymptotic complexity."
    )

    nodes = [
        MockContentNode(
            page_number=1,
            section="Abstract",
            subsection=None,
            source_text=text
        )
    ]

    chunks = chunker.chunk_extracted_nodes(
        document_id="doc_overlap_test",
        document_title="Overlapping Paper",
        extracted_contents=nodes,
    )

    assert len(chunks) >= 2
    # Verify no sentence is sliced mid-word
    for chunk in chunks:
        assert not chunk.content_text.endswith(" estab")
        assert not chunk.content_text.startswith("nce introduces")
