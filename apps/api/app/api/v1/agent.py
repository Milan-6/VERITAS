import logging
from typing import Optional
from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from app.agent.workflow import AgentWorkflow
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["Autonomous AI Research Agent"])


class AgentTaskRequest(BaseModel):
    objective: str = Field(
        ...,
        min_length=3,
        description="Complex research objective, benchmark inquiry, or hypothesis to investigate.",
    )
    max_iterations: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Deterministic iteration limit (enforced ceiling: 5 steps).",
    )


@router.post("/task")
def execute_agent_task(
    payload: AgentTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Spawns an autonomous ReAct research agent workflow.
    Streams real-time Server-Sent Events (SSE) detailing every Think, Action,
    and Observation step, ending with a synthesized, verified research report.
    """
    user_ws = db.query(Workspace).filter(Workspace.owner_id == current_user.id).first()
    tenant_id = user_ws.id if user_ws else current_user.id

    workflow = AgentWorkflow(
        objective=payload.objective,
        max_iterations=payload.max_iterations,
    )

    engine_bind = db.get_bind()
    StreamSessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine_bind)

    def sse_event_stream():
        stream_db = StreamSessionFactory()
        try:
            yield from workflow.execute_stream(tenant_id=tenant_id, db=stream_db)
        finally:
            stream_db.close()

    return StreamingResponse(
        sse_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
