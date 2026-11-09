import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.document import Document, DocumentMetadata, DocumentStatus
from app.models.chunk import SemanticChunk
from app.models.graph import GraphNode, GraphEdge
from app.core.security import hash_password, create_access_token


@pytest.fixture
def secondary_user(db: Session) -> User:
    """Creates a second active user for collaboration tests."""
    user = User(
        id=str(uuid.uuid4()),
        email="collab_editor@veritas.ai",
        full_name="Collaborator Editor",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def secondary_headers(secondary_user: User) -> dict:
    token = create_access_token({"sub": secondary_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_user(db: Session) -> User:
    """Creates a third active user for viewer RBAC tests."""
    user = User(
        id=str(uuid.uuid4()),
        email="collab_viewer@veritas.ai",
        full_name="Collaborator Viewer",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def viewer_headers(viewer_user: User) -> dict:
    token = create_access_token({"sub": viewer_user.id})
    return {"Authorization": f"Bearer {token}"}


def test_workspace_creation_and_member_invitation_flow(
    client: TestClient,
    test_user: User,
    auth_headers: dict,
    secondary_user: User,
):
    """
    Verifies workspace creation, listing, member invitation with role assignment,
    and workspace detail retrieval with member rosters.
    """
    # 1. Create Workspace
    create_res = client.post(
        "/api/v1/workspaces",
        json={"name": "Quantum NLP Lab"},
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    ws_data = create_res.json()
    assert ws_data["name"] == "Quantum NLP Lab"
    assert ws_data["owner_id"] == test_user.id
    assert ws_data["role"] == "OWNER"
    ws_id = ws_data["id"]

    # 2. List Workspaces for Owner
    list_res = client.get("/api/v1/workspaces", headers=auth_headers)
    assert list_res.status_code == 200
    workspaces = list_res.json()
    assert any(w["id"] == ws_id and w["role"] == "OWNER" for w in workspaces)

    # 3. Invite secondary user as EDITOR
    invite_res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": secondary_user.email, "role": "EDITOR"},
        headers=auth_headers,
    )
    assert invite_res.status_code == 201
    member_data = invite_res.json()
    assert member_data["workspace_id"] == ws_id
    assert member_data["user_id"] == secondary_user.id
    assert member_data["email"] == secondary_user.email
    assert member_data["role"] == "EDITOR"

    # 4. Get Workspace Detail
    detail_res = client.get(f"/api/v1/workspaces/{ws_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == ws_id
    assert detail["name"] == "Quantum NLP Lab"
    assert len(detail["members"]) >= 2
    assert any(m["user_id"] == secondary_user.id and m["role"] == "EDITOR" for m in detail["members"])


def test_rbac_authorization_viewer_cannot_invite_or_delete(
    client: TestClient,
    test_user: User,
    auth_headers: dict,
    viewer_user: User,
    viewer_headers: dict,
    secondary_user: User,
):
    """
    Enforces strict RBAC:
    - OWNER can invite VIEWER.
    - VIEWER attempting to invite members receives 403 Forbidden.
    - VIEWER attempting to remove members receives 403 Forbidden.
    """
    # 1. Owner creates workspace
    create_res = client.post(
        "/api/v1/workspaces",
        json={"name": "Restricted Research Workspace"},
        headers=auth_headers,
    )
    assert create_res.status_code == 201
    ws_id = create_res.json()["id"]

    # 2. Owner invites viewer_user with VIEWER role
    invite_res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": viewer_user.email, "role": "VIEWER"},
        headers=auth_headers,
    )
    assert invite_res.status_code == 201
    assert invite_res.json()["role"] == "VIEWER"

    # 3. Viewer attempts to invite another user -> 403 Forbidden
    forbidden_invite = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": secondary_user.email, "role": "EDITOR"},
        headers=viewer_headers,
    )
    assert forbidden_invite.status_code == 403
    assert "Viewers are not permitted" in forbidden_invite.json()["detail"]

    # 4. Viewer attempts to remove another member -> 403 Forbidden
    forbidden_delete = client.delete(
        f"/api/v1/workspaces/{ws_id}/members/{test_user.id}",
        headers=viewer_headers,
    )
    assert forbidden_delete.status_code == 403
    assert "Only workspace owners can remove members" in forbidden_delete.json()["detail"]


def test_shared_workspace_collaboration_document_access(
    client: TestClient,
    db: Session,
    test_user: User,
    auth_headers: dict,
    secondary_user: User,
    secondary_headers: dict,
    viewer_user: User,
    viewer_headers: dict,
):
    """
    Verifies that when User A uploads a document to Workspace W and adds User B
    as a member, User B can access User A's document.
    An uninvited third user (User C) receives 404 (IDOR prevention).
    """
    # 1. User A creates Workspace
    create_res = client.post(
        "/api/v1/workspaces",
        json={"name": "Collaborative Neural Lab"},
        headers=auth_headers,
    )
    ws_id = create_res.json()["id"]

    # 2. User A creates a Document assigned to ws_id
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        workspace_id=ws_id,
        filename="shared_quantum_paper.pdf",
        storage_path="/tmp/shared_quantum_paper.pdf",
        file_size_bytes=4096,
        mime_type="application/pdf",
        file_hash_sha256="collab_hash_999",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Shared Quantum Computing Advances",
        authors=["Alice", "Bob"],
        abstract="Advances in quantum coherence and neural compilation.",
    )
    db.add(meta)
    db.commit()

    # 3. Uninvited User B attempts to access document -> 404
    unauth_res = client.get(f"/api/v1/documents/{doc.id}", headers=secondary_headers)
    assert unauth_res.status_code == 404

    # 4. User A invites User B to ws_id as EDITOR
    invite_res = client.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": secondary_user.email, "role": "EDITOR"},
        headers=auth_headers,
    )
    assert invite_res.status_code == 201

    # 5. User B can now successfully access User A's document
    collab_res = client.get(f"/api/v1/documents/{doc.id}", headers=secondary_headers)
    assert collab_res.status_code == 200
    doc_data = collab_res.json()
    assert doc_data["id"] == doc.id
    assert doc_data["filename"] == "shared_quantum_paper.pdf"

    # 6. User C (uninvited) is still denied access (404)
    c_res = client.get(f"/api/v1/documents/{doc.id}", headers=viewer_headers)
    assert c_res.status_code == 404


def test_pdf_dossier_export_integrity(
    client: TestClient,
    db: Session,
    test_user: User,
    auth_headers: dict,
    secondary_headers: dict,
):
    """
    Verifies that GET /api/v1/export/dossier/{document_id} generates a valid,
    publication-grade PDF document starting with '%PDF-' and containing
    proper headers and metadata.
    """
    # 1. Create document
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=test_user.id,
        workspace_id=f"workspace_{test_user.id}",
        filename="sparse_transformer_analysis.pdf",
        storage_path="/tmp/sparse_transformer_analysis.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        file_hash_sha256="dossier_hash_001",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Generating Long Sequences with Sparse Transformers",
        authors=["Child et al."],
        abstract="Deep neural networks with factorized self-attention scale to sequence lengths of thousands.",
        total_pages=12,
        journal_or_conference="NeurIPS",
        doi="10.48550/arXiv.1904.10509",
    )
    db.add(meta)

    # 2. Add sample semantic chunks
    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=test_user.id,
        chunk_index=0,
        content_text="Sparse Transformers introduce factorized self-attention patterns that reduce attention matrix memory from quadratic to sub-quadratic.",
        embedded_text="Sparse Transformers factorized self-attention...",
        context_header="[Document: Sparse Transformer] [Section: Introduction]",
        token_count=22,
        page_number=1,
        section_title="Introduction",
    )
    db.add(chunk)

    # 3. Add Knowledge Graph entities
    node1 = GraphNode(
        id=str(uuid.uuid4()),
        tenant_id=test_user.id,
        type="Algorithm",
        label="Sparse Attention",
        description="Factorized sparse attention pattern",
        document_id=doc.id,
    )
    node2 = GraphNode(
        id=str(uuid.uuid4()),
        tenant_id=test_user.id,
        type="Dataset",
        label="Enwik8",
        description="Byte-level language modeling benchmark",
        document_id=doc.id,
    )
    db.add_all([node1, node2])
    db.flush()

    edge = GraphEdge(
        id=str(uuid.uuid4()),
        tenant_id=test_user.id,
        source_node_id=node1.id,
        target_node_id=node2.id,
        relationship_type="BENCHMARKS_ON",
        source_excerpt="Evaluated on Enwik8 byte-level language modeling benchmark.",
        document_id=doc.id,
    )
    db.add(edge)
    db.commit()

    # 4. Request PDF Dossier Export
    export_res = client.get(
        f"/api/v1/export/dossier/{doc.id}",
        headers=auth_headers,
    )

    assert export_res.status_code == 200
    assert export_res.headers["content-type"] == "application/pdf"
    assert "attachment" in export_res.headers.get("content-disposition", "")
    assert f"VERITAS_Dossier_{doc.id[:8]}.pdf" in export_res.headers.get("content-disposition", "")

    # 5. Verify PDF byte stream magic bytes
    pdf_bytes = export_res.content
    assert pdf_bytes.startswith(b"%PDF-"), "Exported content must be a valid PDF starting with %PDF-"
    assert len(pdf_bytes) > 2000, "Exported PDF dossier should contain substantial structured content"

    # 6. Unauthorized user cannot export User A's dossier -> 404
    unauth_export = client.get(
        f"/api/v1/export/dossier/{doc.id}",
        headers=secondary_headers,
    )
    assert unauth_export.status_code == 404
