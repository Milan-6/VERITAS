import uuid
from qdrant_client import QdrantClient
from app.services.vector_store import QdrantVectorStore
from app.services.chunker import SemanticChunkData


def test_qdrant_vector_store_indexing_and_deletion():
    # Use dedicated in-memory Qdrant client for isolated test
    test_client = QdrantClient(":memory:")
    collection_name = f"test_coll_{uuid.uuid4().hex[:8]}"

    vs = QdrantVectorStore(collection_name=collection_name, client=test_client)

    # Verify collection exists with dense and sparse configs
    collections = [c.name for c in test_client.get_collections().collections]
    assert collection_name in collections

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    chunks = [
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_1",
            document_id=doc_id,
            page_number=1,
            section_title="1 Introduction",
            subsection=None,
            context_header="[Document: AI Safety] [Section: 1 Introduction]",
            content_text="Prompt injection remains an adversarial threat vector in RAG pipelines.",
            embedded_text="[Document: AI Safety] [Section: 1 Introduction]\nPrompt injection remains an adversarial threat vector in RAG pipelines.",
            token_count=18,
            chunk_index=1,
        ),
        SemanticChunkData(
            chunk_id=f"chk_{doc_id}_2",
            document_id=doc_id,
            page_number=2,
            section_title="2 Mitigations",
            subsection=None,
            context_header="[Document: AI Safety] [Section: 2 Mitigations]",
            content_text="Deterministic citation grounding eliminates fabricated hallucinated context.",
            embedded_text="[Document: AI Safety] [Section: 2 Mitigations]\nDeterministic citation grounding eliminates fabricated hallucinated context.",
            token_count=16,
            chunk_index=2,
        ),
    ]

    # Index chunks
    point_ids = vs.index_chunks(
        tenant_id="tenant_alpha",
        document_id=doc_id,
        document_title="AI Safety in Academic Literature",
        chunks=chunks,
    )

    assert len(point_ids) == 2

    # Verify points exist in Qdrant
    points_info = test_client.retrieve(collection_name=collection_name, ids=point_ids)
    assert len(points_info) == 2
    assert points_info[0].payload["tenant_id"] == "tenant_alpha"
    assert points_info[0].payload["document_id"] == doc_id

    # Test Deletion: When document is deleted, vectors must be physically deleted
    vs.delete_document_vectors(doc_id)

    # Verify points are deleted
    remaining_points = test_client.retrieve(collection_name=collection_name, ids=point_ids)
    assert len(remaining_points) == 0
