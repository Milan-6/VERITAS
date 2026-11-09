import json
import uuid
import pytest
from sqlalchemy.orm import Session

from app.agent.tools import agent_tools
from app.agent.workflow import AgentWorkflow
from app.models.chunk import SemanticChunk
from app.models.document import Document, DocumentMetadata, DocumentStatus
from app.models.user import User
from app.services.chunker import SemanticChunkData
from app.services.vector_store import vector_store


def test_agent_tool_tenant_isolation(db: Session, test_user: User, test_user_2: User):
    """
    CRITICAL SECURITY TEST (SEC-01):
    Proves Agent Tool execution strictly enforces tenant isolation.
    An agent running in Tenant 1's context CANNOT access or read Document chunks
    belonging to Tenant 2.
    """
    tenant_1 = test_user.id
    tenant_2 = test_user_2.id

    # Create Document for Tenant 2
    doc_t2 = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_2,
        workspace_id=f"workspace_{tenant_2}",
        filename="classified_tenant_2_research.pdf",
        storage_path="/tmp/classified_tenant_2_research.pdf",
        file_size_bytes=2048,
        mime_type="application/pdf",
        file_hash_sha256="hash_t2_secret",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc_t2)
    db.flush()

    meta_t2 = DocumentMetadata(
        document_id=doc_t2.id,
        title="Classified Synthesis in Tenant 2",
        authors=["Tenant 2 Lead Scientist"],
        abstract="Secret experimental findings not accessible to external tenants.",
    )
    db.add(meta_t2)

    chunk_t2 = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc_t2.id}_chunk_0",
        document_id=doc_t2.id,
        user_id=tenant_2,
        chunk_index=0,
        content_text="Tenant 2 secret formula for zero-shot reasoning is 42.",
        embedded_text="Tenant 2 secret formula for zero-shot reasoning is 42.",
        context_header="[Document: Classified] [Section: Secret]",
        token_count=15,
        page_number=1,
        section_title="Secret",
    )
    db.add(chunk_t2)
    db.commit()

    # Tenant 1 tries to read section from Tenant 2's document
    res_read = agent_tools.execute_tool(
        tool_name="read_document_section",
        tool_args={"document_id": doc_t2.id, "section_name": "Secret"},
        tenant_id=tenant_1,
        db=db,
    )
    assert "access denied" in res_read.get("output", "").lower() or "not found" in res_read.get("output", "").lower()
    assert len(res_read.get("evidence_chunks", [])) == 0

    # Tenant 1 tries to extract summary from Tenant 2's document
    res_sum = agent_tools.execute_tool(
        tool_name="extract_document_summary",
        tool_args={"document_id": doc_t2.id},
        tenant_id=tenant_1,
        db=db,
    )
    assert "access denied" in res_sum.get("output", "").lower() or "not found" in res_sum.get("output", "").lower()
    assert len(res_sum.get("evidence_chunks", [])) == 0


def test_agent_state_machine_max_iterations(db: Session, test_user: User):
    """
    Verifies that the AgentWorkflow state machine adheres to a bounded loop
    (strictly max 5 iterations) and terminates cleanly without an unbounded loop.
    """
    tenant_id = test_user.id

    # Create test document for test_user
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_id,
        workspace_id=f"workspace_{tenant_id}",
        filename="agent_reasoning_test.pdf",
        storage_path="/tmp/agent_reasoning_test.pdf",
        file_size_bytes=1024,
        mime_type="application/pdf",
        file_hash_sha256="hash_agent_test",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="Agent Reasoning Throughput Study",
        authors=["VERITAS Research Group"],
        abstract="Empirical analysis of inference throughput and memory scaling in transformers.",
    )
    db.add(meta)

    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=tenant_id,
        chunk_index=0,
        content_text="Empirical results demonstrate a 25.4% improvement in inference throughput using flash attention.",
        embedded_text="Empirical results demonstrate a 25.4% improvement in inference throughput using flash attention.",
        context_header="[Document: Agent Test] [Section: Results]",
        token_count=20,
        page_number=3,
        section_title="Results",
    )
    db.add(chunk)
    db.commit()

    # Index into vector store
    vector_store.index_chunks(
        tenant_id=tenant_id,
        document_id=doc.id,
        document_title="Agent Reasoning Throughput Study",
        chunks=[
            SemanticChunkData(
                chunk_id=f"chk_{doc.id}_0",
                document_id=doc.id,
                page_number=3,
                section_title="Results",
                subsection="Throughput",
                context_header="[Document: Agent Test] [Section: Results]",
                content_text="Empirical results demonstrate a 25.4% improvement in inference throughput using flash attention.",
                embedded_text="Empirical results demonstrate a 25.4% improvement in inference throughput using flash attention.",
                token_count=20,
                chunk_index=0,
            )
        ],
    )

    workflow = AgentWorkflow(
        objective="Analyze inference throughput improvements and synthesize findings.",
        max_iterations=5,
    )

    events = []
    for chunk_str in workflow.execute_stream(tenant_id=tenant_id, db=db):
        for line in chunk_str.strip().split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))

    assert len(events) > 0

    # Ensure max iteration ceiling is respected
    iteration_events = [e for e in events if e.get("status") == "thinking" and e.get("step", 0) > 0]
    assert len(iteration_events) <= 5

    # Check that a final completion event was yielded
    completed_events = [e for e in events if e.get("status") == "completed"]
    assert len(completed_events) == 1

    final_event = completed_events[0]
    assert "report" in final_event
    assert final_event["report"] is not None
    assert len(final_event["report"]) > 0
    assert "verification_report" in final_event


def test_agent_streaming_endpoint(client, auth_headers, test_user, db: Session):
    """
    Verifies the streaming API endpoint POST /api/v1/agent/task
    emits valid Server-Sent Events (SSE) with thinking, tool_call,
    and completed status.
    """
    tenant_id = test_user.id

    # Create doc
    doc = Document(
        id=str(uuid.uuid4()),
        user_id=tenant_id,
        workspace_id=f"workspace_{tenant_id}",
        filename="benchmark_eval.pdf",
        storage_path="/tmp/benchmark_eval.pdf",
        file_size_bytes=1500,
        mime_type="application/pdf",
        file_hash_sha256="hash_benchmark_eval",
        status=DocumentStatus.COMPLETED.value,
    )
    db.add(doc)
    db.flush()

    meta = DocumentMetadata(
        document_id=doc.id,
        title="HumanEval Benchmark Study",
        authors=["Open Evaluation Team"],
        abstract="Benchmark evaluation comparing baseline and fine-tuned coding models.",
    )
    db.add(meta)

    chunk = SemanticChunk(
        id=str(uuid.uuid4()),
        chunk_id=f"{doc.id}_chunk_0",
        document_id=doc.id,
        user_id=tenant_id,
        chunk_index=0,
        content_text="On HumanEval, the fine-tuned model achieved 78.2% pass@1 accuracy compared to 65.0% for baseline.",
        embedded_text="On HumanEval, the fine-tuned model achieved 78.2% pass@1 accuracy compared to 65.0% for baseline.",
        context_header="[Document: Benchmark Eval] [Section: Experiments]",
        token_count=22,
        page_number=5,
        section_title="Experiments",
    )
    db.add(chunk)
    db.commit()

    # Index into vector store
    vector_store.index_chunks(
        tenant_id=tenant_id,
        document_id=doc.id,
        document_title="HumanEval Benchmark Study",
        chunks=[
            SemanticChunkData(
                chunk_id=f"chk_{doc.id}_0",
                document_id=doc.id,
                page_number=5,
                section_title="Experiments",
                subsection="Pass@1",
                context_header="[Document: Benchmark Eval] [Section: Experiments]",
                content_text="On HumanEval, the fine-tuned model achieved 78.2% pass@1 accuracy compared to 65.0% for baseline.",
                embedded_text="On HumanEval, the fine-tuned model achieved 78.2% pass@1 accuracy compared to 65.0% for baseline.",
                token_count=22,
                chunk_index=0,
            )
        ],
    )

    res = client.post(
        "/api/v1/agent/task",
        headers=auth_headers,
        json={
            "objective": "Compare baseline vs fine-tuned accuracy on HumanEval benchmark.",
            "max_iterations": 3,
        },
    )

    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")

    # Parse SSE stream
    lines = res.text.split("\n")
    data_lines = [l[len("data: "):] for l in lines if l.startswith("data: ")]
    assert len(data_lines) > 0

    parsed_events = [json.loads(dl) for dl in data_lines]
    statuses = [e.get("status") for e in parsed_events]
    assert "thinking" in statuses
    assert "completed" in statuses

    completed_event = next(e for e in parsed_events if e.get("status") == "completed")
    assert "report" in completed_event
    assert len(completed_event["report"]) > 0
    assert "verification_report" in completed_event
