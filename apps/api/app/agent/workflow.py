import json
import logging
from typing import Any, Dict, List, Optional, Generator
from sqlalchemy.orm import Session

from app.agent.tools import AGENT_TOOL_DEFINITIONS, AgentToolRegistry
from app.core.config import settings
from app.schemas.chat import VerificationReport
from app.services.retrieval import RetrievedChunk
from app.services.verification import evidence_verifier

logger = logging.getLogger(__name__)


class AgentWorkflow:
    """
    Deterministic ReAct Autonomous Research Agent.
    Operates under a strict max_iterations loop (default: 5 iterations)
    preventing unbounded recursion and excessive LLM costs.
    """

    def __init__(self, objective: str, max_iterations: int = 5):
        self.objective = objective.strip()
        self.max_iterations = min(max(max_iterations, 1), 5)
        self.action_history: List[Dict[str, Any]] = []
        self.gathered_evidence: List[Dict[str, Any]] = []
        self.seen_chunk_ids = set()

    def _decide_next_action_gemini(self) -> Dict[str, Any]:
        """Queries Google Gemini Flash using structured JSON output to select the next action."""
        if not settings.GEMINI_API_KEY:
            return self._decide_next_action_fallback()

        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.LLM_MODEL,
                generation_config={
                    "temperature": 0.0,
                    "response_mime_type": "application/json",
                },
            )

            history_text = "\n".join(
                [
                    f"Step {h['step']}: Thought: {h['thought']}\n"
                    f"Action: {h['action']}({json.dumps(h['args'])})\n"
                    f"Observation: {h['output'][:200]}..."
                    for h in self.action_history
                ]
            ) or "No previous actions taken."

            prompt = f"""You are the VERITAS Autonomous Research Agent.
Your objective is: "{self.objective}"

Current Actions & Observations:
{history_text}

Evidence gathered so far: {len(self.gathered_evidence)} chunks.
Remaining iterations: {self.max_iterations - len(self.action_history)}.

RULES:
1. Available tools:
   - "search_workspace": {{"query": "semantic query string"}}
   - "read_document_section": {{"document_id": "...", "section_name": "Methodology|Results|Introduction"}}
   - "extract_document_summary": {{"document_id": "..."}}
   - "finish_research": {{"summary": "Gathered sufficient evidence to synthesize final report"}}
2. If you already have relevant evidence from previous steps, select "finish_research".
3. Return strictly valid JSON:
{{
  "thought": "Your reasoning about what information is missing and why this tool is needed",
  "action": "search_workspace" | "read_document_section" | "extract_document_summary" | "finish_research",
  "args": {{ ... }}
}}
"""
            response = model.generate_content(prompt)
            data = json.loads(response.text)
            return data
        except Exception as e:
            logger.warning(f"Gemini decision failed: {str(e)}. Using fallback decision.")
            return self._decide_next_action_fallback()

    def _decide_next_action_fallback(self) -> Dict[str, Any]:
        """
        Deterministic, offline decision logic for unit tests and offline environments.
        Simulates: Step 1 -> search_workspace, Step 2 -> read_document_section (if doc found) else finish, Step 3 -> finish.
        """
        step = len(self.action_history) + 1

        if step == 1:
            return {
                "thought": f"I will perform a hybrid search across the workspace for literature regarding '{self.objective}'.",
                "action": "search_workspace",
                "args": {"query": self.objective},
            }

        # If we have evidence from step 1
        if self.gathered_evidence and step == 2:
            first_doc_id = self.gathered_evidence[0].get("document_id")
            if first_doc_id:
                return {
                    "thought": f"I will inspect the detailed methodology section of document {first_doc_id}.",
                    "action": "read_document_section",
                    "args": {"document_id": first_doc_id, "section_name": "Methodology"},
                }

        # Otherwise finish
        return {
            "thought": "I have collected sufficient empirical evidence from the workspace. Ready to synthesize the report.",
            "action": "finish_research",
            "args": {"summary": "Completed workspace investigation."},
        }

    def _generate_report_gemini(self) -> str:
        """Synthesizes the final grounded Markdown report using Gemini Flash."""
        if not settings.GEMINI_API_KEY:
            return self._generate_report_fallback()

        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(
                model_name=settings.LLM_MODEL,
                generation_config={"temperature": 0.0},
            )

            evidence_text = "\n\n---\n\n".join(
                [
                    f"[Document: {e['document_title']}, Page: {e['page_number']}]\n"
                    f"Section: {e['section_title']}\n"
                    f"{e['content_text']}"
                    for e in self.gathered_evidence[:10]
                ]
            )

            prompt = f"""You are the VERITAS Research Intelligence Agent.
Synthesize a comprehensive, rigorous research intelligence report based strictly on the gathered workspace evidence.

Objective: {self.objective}

Gathered Evidence:
{evidence_text}

REQUIREMENTS:
1. Grounded in Truth: Cite every factual claim using inline citations format: [Document: <Exact Title>, Page: <Page Number>].
2. Structure with clear Markdown headers:
   # Executive Summary
   # Empirical Analysis & Findings
   # Methodological & Benchmark Comparisons
   # Limitations & Future Directions
3. If no evidence was found, state strictly: "{settings.STRICT_ABSTENTION_MESSAGE}"
"""
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Report generation with Gemini failed: {str(e)}. Using fallback report generator.")
            return self._generate_report_fallback()

    def _generate_report_fallback(self) -> str:
        """Deterministic Markdown report generator for offline testing."""
        if not self.gathered_evidence:
            return (
                f"# Research Report: {self.objective}\n\n"
                f"**Executive Summary:** {settings.STRICT_ABSTENTION_MESSAGE}\n"
            )

        citations_list = []
        for e in self.gathered_evidence[:5]:
            citations_list.append(
                f"- **{e['document_title']}** (Page {e['page_number']}, Section: {e['section_title']}): "
                f"\"{e['content_text'][:120]}...\" [Document: {e['document_title']}, Page: {e['page_number']}]"
            )

        citations_block = "\n".join(citations_list)

        return f"""# Autonomous Research Intelligence Report: {self.objective}

## 1. Executive Summary
The VERITAS Autonomous Agent executed a targeted multi-step investigation across verified workspace literature to address the objective: *"{self.objective}"*. Empirical findings were derived directly from stored documents without external conjecture.

## 2. Key Scientific Findings & Citations
{citations_block}

## 3. Entailment & Grounding Verification
All claims in this report are tied to indexed workspace chunks. The Evidence Verification Engine has evaluated this text against source text excerpts.
"""

    def execute_stream(
        self,
        tenant_id: str,
        db: Session,
    ) -> Generator[str, None, None]:
        """
        Executes the ReAct loop and streams Server-Sent Events (SSE) in real-time.
        Yields standard SSE formatted strings: `data: {...}\n\n`.
        """
        # Event 1: Initializing
        init_payload = {
            "status": "thinking",
            "message": f"Agent initialized. Beginning autonomous investigation: '{self.objective}'",
            "step": 0,
            "max_iterations": self.max_iterations,
        }
        yield f"data: {json.dumps(init_payload)}\n\n"

        for iteration in range(1, self.max_iterations + 1):
            # 1. THINK: Decide next action
            decision = self._decide_next_action_gemini()
            thought = decision.get("thought", "Evaluating next research step...")
            action = decision.get("action", "search_workspace")
            args = decision.get("args", {})

            think_payload = {
                "status": "thinking",
                "step": iteration,
                "thought": thought,
                "action": action,
                "args": args,
            }
            yield f"data: {json.dumps(think_payload)}\n\n"

            # Check termination condition
            if action == "finish_research":
                finish_payload = {
                    "status": "tool_call",
                    "step": iteration,
                    "tool": "finish_research",
                    "args": args,
                    "output_preview": "Research phase concluded. All required evidence collected.",
                }
                yield f"data: {json.dumps(finish_payload)}\n\n"
                break

            # 2. ACT: Execute Tool with tenant isolation
            tool_result = AgentToolRegistry.execute_tool(
                tool_name=action,
                tool_args=args,
                tenant_id=tenant_id,
                db=db,
            )

            output = tool_result.get("output", "")
            new_evidence = tool_result.get("evidence_chunks", [])

            # Deduplicate and append evidence
            for ev in new_evidence:
                c_id = ev.get("chunk_id")
                if c_id and c_id not in self.seen_chunk_ids:
                    self.seen_chunk_ids.add(c_id)
                    self.gathered_evidence.append(ev)

            # Record in action history
            self.action_history.append({
                "step": iteration,
                "thought": thought,
                "action": action,
                "args": args,
                "output": output,
            })

            preview = output[:180] + ("..." if len(output) > 180 else "")
            act_payload = {
                "status": "tool_call",
                "step": iteration,
                "tool": action,
                "args": args,
                "output_preview": preview,
                "evidence_count": len(self.gathered_evidence),
            }
            yield f"data: {json.dumps(act_payload)}\n\n"

        # 3. GENERATING REPORT
        yield f"data: {json.dumps({'status': 'generating_report', 'message': 'Synthesizing final Markdown research report with academic citations...'})}\n\n"

        final_report = self._generate_report_gemini()

        # 4. VERIFYING REPORT (Phase 4 Evidence Verification Engine)
        yield f"data: {json.dumps({'status': 'verifying', 'message': 'Executing Evidence Verification Engine: extracting atomic claims & testing NLI entailment...'})}\n\n"

        retrieved_chunks = [
            RetrievedChunk(
                chunk_id=ev["chunk_id"],
                document_id=ev["document_id"],
                document_title=ev["document_title"],
                page_number=ev["page_number"],
                section_title=ev["section_title"],
                subsection=None,
                content_text=ev["content_text"],
                score=ev.get("score", 1.0),
                dense_score=None,
                sparse_score=None,
            )
            for ev in self.gathered_evidence
        ]

        verification_report: VerificationReport = evidence_verifier.generate_report(
            response_text=final_report,
            chunks=retrieved_chunks,
        )

        # 5. COMPLETED
        complete_payload = {
            "status": "completed",
            "report": final_report,
            "verification_report": verification_report.model_dump(),
            "steps_taken": len(self.action_history),
            "evidence_count": len(self.gathered_evidence),
        }
        yield f"data: {json.dumps(complete_payload)}\n\n"
