import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.chunk import SemanticChunk
from app.models.document import Document, DocumentMetadata, DocumentStatus
from app.models.graph import GraphEdge, GraphNode
from app.models.user import User
from app.models.workspace import Workspace
from app.services.knowledge_graph import knowledge_graph_service


def test_entity_and_edge_extraction_models(db: Session):
    """
    Verifies that scientific entities (Nodes) and semantic relations (Edges)
    are accurately extracted, mapped to proper types, and linked with chunk provenance.
    """
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"

    # Create test document
    doc = Document(
        id=str(uuid.uuid4()),
        user_id="user_test_1",
        workspace_id=tenant_id,
        filename="sparse_transformer.pdf",
        storage_path="/tmp/sparse_transformer.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256="hash_kg_123",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Generating Long Sequences with Sparse Transformers",
        authors=["Rewon Child", "Scott Gray", "Alec Radford"],
        abstract="We introduce Sparse Attention which reduces attention complexity from O(N^2) to O(N sqrt(N)). Evaluated on ImageNet and CIFAR-10.",
    )
    db.add(meta)

    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=doc.user_id,
        chunk_index=0,
        content_text="We introduce Sparse Attention to benchmark image density modeling on ImageNet and measure bits per dimension with BLEU.",
        embedded_text="We introduce Sparse Attention to benchmark image density modeling on ImageNet and measure bits per dimension with BLEU.",
        context_header="[Document: ...] [Section: Introduction]",
        token_count=35,
        page_number=1,
        section_title="Introduction",
    )
    db.add(chunk)
    db.commit()

    nodes_count, edges_count = knowledge_graph_service.extract_entities_for_document(
        document_id=doc.id,
        tenant_id=tenant_id,
        db=db,
    )

    assert nodes_count > 0
    assert edges_count > 0

    # Verify nodes in database
    nodes = db.query(GraphNode).filter(GraphNode.tenant_id == tenant_id).all()
    node_types = {n.type for n in nodes}
    node_labels = {n.label.lower() for n in nodes}

    assert "Paper" in node_types
    assert "Author" in node_types
    assert "Dataset" in node_types

    assert "generating long sequences with sparse transformers" in node_labels
    assert "imagenet" in node_labels

    # Verify edges and provenance
    edges = db.query(GraphEdge).filter(GraphEdge.tenant_id == tenant_id).all()
    assert len(edges) >= 2
    rel_types = {e.relationship_type for e in edges}
    assert "AUTHORS" in rel_types

    # Ensure provenance chunk was linked
    dataset_edge = next((e for e in edges if e.relationship_type in ("EVALUATES", "USES", "BENCHMARKS_ON")), None)
    assert dataset_edge is not None
    assert dataset_edge.provenance_chunk_id == chunk.id


def test_knowledge_graph_tenant_isolation(
    client: TestClient,
    auth_headers: dict,
    auth_headers_2: dict,
    test_user: User,
    test_user_2: User,
    db: Session,
):
    """
    Verifies strict multi-tenant boundary isolation:
    User A's workspace graph queries return zero nodes from User B's workspace,
    and identical entities in separate workspaces create independent, isolated GraphNodes.
    """
    # 1. Create Workspace A and entities for User A
    tenant_a = test_user.id

    node_a1 = knowledge_graph_service.get_or_create_node(
        tenant_id=tenant_a,
        node_type="Dataset",
        label="ImageNet",
        db=db,
        description="User A's benchmark dataset",
    )
    node_a2 = knowledge_graph_service.get_or_create_node(
        tenant_id=tenant_a,
        node_type="Algorithm",
        label="Vision Transformer",
        db=db,
    )
    knowledge_graph_service.get_or_create_edge(
        tenant_id=tenant_a,
        source_node_id=node_a2.id,
        target_node_id=node_a1.id,
        relationship_type="EVALUATES",
        db=db,
        source_excerpt="ViT evaluates on ImageNet",
    )

    # 2. Create Workspace B and entities for User B (including identical entity name "ImageNet")
    tenant_b = test_user_2.id

    node_b1 = knowledge_graph_service.get_or_create_node(
        tenant_id=tenant_b,
        node_type="Dataset",
        label="ImageNet",
        db=db,
        description="User B's private dataset instance",
    )
    node_b2 = knowledge_graph_service.get_or_create_node(
        tenant_id=tenant_b,
        node_type="Algorithm",
        label="ResNet-50",
        db=db,
    )
    knowledge_graph_service.get_or_create_edge(
        tenant_id=tenant_b,
        source_node_id=node_b2.id,
        target_node_id=node_b1.id,
        relationship_type="BENCHMARKS_ON",
        db=db,
        source_excerpt="ResNet evaluated on ImageNet",
    )

    # Prove distinct IDs for identical label in different tenants
    assert node_a1.id != node_b1.id
    assert node_a1.tenant_id == tenant_a
    assert node_b1.tenant_id == tenant_b

    # 3. Query API as User A
    res_a = client.get("/api/v1/graph/workspace", headers=auth_headers)
    assert res_a.status_code == 200
    graph_a = res_a.json()

    a_labels = {n["label"] for n in graph_a["nodes"]}
    assert "Vision Transformer" in a_labels
    assert "ResNet-50" not in a_labels  # User B's entity must NOT leak into User A

    # 4. Query API as User B
    res_b = client.get("/api/v1/graph/workspace", headers=auth_headers_2)
    assert res_b.status_code == 200
    graph_b = res_b.json()

    b_labels = {n["label"] for n in graph_b["nodes"]}
    assert "ResNet-50" in b_labels
    assert "Vision Transformer" not in b_labels  # User A's entity must NOT leak into User B


def test_graph_upsert_deduplication(db: Session):
    """
    Verifies that inserting the same entity multiple times in the same tenant
    safely deduplicates and reuses the existing node without raising constraint errors.
    """
    tenant_id = f"tenant_{uuid.uuid4().hex[:8]}"

    node1 = knowledge_graph_service.get_or_create_node(
        tenant_id=tenant_id,
        node_type="Algorithm",
        label="Transformer",
        db=db,
    )

    node2 = knowledge_graph_service.get_or_create_node(
        tenant_id=tenant_id,
        node_type="Algorithm",
        label="transformer",  # Case-insensitive check
        db=db,
    )

    assert node1.id == node2.id

    total_nodes = db.query(GraphNode).filter(GraphNode.tenant_id == tenant_id).count()
    assert total_nodes == 1


def test_cross_tenant_extract_rejection(client: TestClient, auth_headers_2: dict, test_user: User, db: Session):
    """
    Verifies that User B cannot trigger entity extraction on User A's private document.
    """
    doc_a = Document(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        workspace_id=test_user.id,
        filename="user_a_private.pdf",
        storage_path="/tmp/user_a_private.pdf",
        file_size_bytes=512,
        mime_type="application/pdf",
        file_hash_sha256=f"hash_{uuid.uuid4().hex}",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc_a)
    db.commit()

    # User B (auth_headers_2) attempts to trigger extraction on doc_a
    res = client.post(f"/api/v1/graph/extract/{doc_a.id}", headers=auth_headers_2)
    assert res.status_code in (403, 404)
