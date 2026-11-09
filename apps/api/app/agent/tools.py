import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.chunk import SemanticChunk
from app.models.document import Document, DocumentMetadata, ExtractedSection
from app.services.academic_extraction import academic_extraction_service
from app.services.retrieval import retrieval_service

logger = logging.getLogger(__name__)

# Native Tool Definitions for Google GenAI function calling / ReAct prompt
AGENT_TOOL_DEFINITIONS = [
    {
        "name": "search_workspace",
        "description": "Performs hybrid vector & keyword retrieval across all research documents in the user's workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The semantic search query, research question, or topic to search for.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_document_section",
        "description": "Reads text and detailed evidence from a specific section of a known document in the workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "document_id": {
                    "type": "STRING",
                    "description": "The unique ID of the target document.",
                },
                "section_name": {
                    "type": "STRING",
                    "description": "The name or topic of the section to read (e.g., 'Methodology', 'Results', 'Introduction').",
                },
            },
            "required": ["document_id", "section_name"],
        },
    },
    {
        "name": "extract_document_summary",
        "description": "Extracts the 5-point structured scientific synthesis (Problem, Methodology, Datasets, Results, Limitations) for a specific paper.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "document_id": {
                    "type": "STRING",
                    "description": "The unique ID of the target document.",
                },
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "finish_research",
        "description": "Terminates the research phase when sufficient evidence has been gathered to write the final synthesized report.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "Brief summary of gathered insights before report generation.",
                }
            },
        },
    },
]


class AgentToolRegistry:
    """
    Secure execution wrapper for agent tools with mandatory tenant isolation.
    """

    @staticmethod
    def _verify_document_tenant(document_id: str, tenant_id: str, db: Session) -> Optional[Document]:
        """Ensures the document belongs to the active tenant workspace."""
        doc = (
            db.query(Document)
            .filter(
                Document.id == document_id,
                (Document.workspace_id == tenant_id) | (Document.user_id == tenant_id),
            )
            .first()
        )
        return doc

    @classmethod
    def search_workspace(
        cls,
        query: str,
        tenant_id: str,
        db: Session,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Executes hybrid retrieval strictly filtered by tenant_id.
        """
        try:
            results = retrieval_service.search(
                query=query,
                tenant_id=tenant_id,
                top_k=top_k,
            )

            if not results:
                return {
                    "output": "No relevant document chunks found in your workspace for this query.",
                    "evidence_chunks": [],
                }

            formatted = []
            evidence = []
            for r in results:
                item_str = (
                    f"[{r.document_title} | Page {r.page_number} | Section: {r.section_title}]\n"
                    f"{r.content_text.strip()}\n"
                    f"(Chunk ID: {r.chunk_id}, Doc ID: {r.document_id})"
                )
                formatted.append(item_str)
                evidence.append({
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "page_number": r.page_number,
                    "section_title": r.section_title,
                    "content_text": r.content_text,
                    "score": r.score,
                })

            output_text = f"Found {len(results)} relevant excerpts:\n\n" + "\n\n---\n\n".join(formatted)
            return {
                "output": output_text,
                "evidence_chunks": evidence,
            }
        except Exception as e:
            logger.error(f"Error in search_workspace tool: {str(e)}")
            return {
                "output": f"Tool execution error in search_workspace: {str(e)}",
                "evidence_chunks": [],
            }

    @classmethod
    def read_document_section(
        cls,
        document_id: str,
        section_name: str,
        tenant_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Reads chunks or text matching the requested section within a verified workspace document.
        """
        doc = cls._verify_document_tenant(document_id, tenant_id, db)
        if not doc:
            return {
                "output": f"Access denied or document '{document_id}' not found in workspace.",
                "evidence_chunks": [],
            }

        title = doc.doc_metadata.title if doc.doc_metadata and doc.doc_metadata.title else doc.filename

        # Query semantic chunks matching section
        chunks = (
            db.query(SemanticChunk)
            .filter(
                SemanticChunk.document_id == document_id,
                func.lower(SemanticChunk.section_title).ilike(f"%{section_name.strip().lower()}%"),
            )
            .order_by(SemanticChunk.chunk_index.asc())
            .limit(5)
            .all()
        )

        if not chunks:
            # Fallback to general chunks for this document
            chunks = (
                db.query(SemanticChunk)
                .filter(SemanticChunk.document_id == document_id)
                .order_by(SemanticChunk.chunk_index.asc())
                .limit(3)
                .all()
            )

        if not chunks:
            return {
                "output": f"No parsed sections or text chunks found for document '{title}'.",
                "evidence_chunks": [],
            }

        formatted = []
        evidence = []
        for c in chunks:
            item_str = (
                f"[{title} | Page {c.page_number} | Section: {c.section_title}]\n"
                f"{c.content_text.strip()}\n"
                f"(Chunk ID: {c.chunk_id}, Doc ID: {doc.id})"
            )
            formatted.append(item_str)
            evidence.append({
                "chunk_id": c.chunk_id,
                "document_id": doc.id,
                "document_title": title,
                "page_number": c.page_number,
                "section_title": c.section_title,
                "content_text": c.content_text,
                "score": 1.0,
            })

        output_text = f"Section excerpts for '{title}' (Section: {section_name}):\n\n" + "\n\n---\n\n".join(formatted)
        return {
            "output": output_text,
            "evidence_chunks": evidence,
        }

    @classmethod
    def extract_document_summary(
        cls,
        document_id: str,
        tenant_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Invokes Phase 5 structured synthesis for the target document.
        """
        doc = cls._verify_document_tenant(document_id, tenant_id, db)
        if not doc:
            return {
                "output": f"Access denied or document '{document_id}' not found in workspace.",
                "evidence_chunks": [],
            }

        title = doc.doc_metadata.title if doc.doc_metadata and doc.doc_metadata.title else doc.filename

        try:
            synthesis = academic_extraction_service.synthesize_paper(
                document_id=doc.id,
                tenant_id=tenant_id,
                document_title=title,
            )

            text_parts = [
                f"Structured Scientific Synthesis for '{title}':",
                f"• Problem Statement (p.{synthesis.problem_statement.page_number}): {synthesis.problem_statement.summary}",
                f"• Methodology (p.{synthesis.methodology.page_number}): {synthesis.methodology.summary}",
                f"• Dataset Used (p.{synthesis.dataset_used.page_number}): {synthesis.dataset_used.summary}",
                f"• Key Results (p.{synthesis.key_results.page_number}): {synthesis.key_results.summary}",
                f"• Limitations (p.{synthesis.limitations.page_number}): {synthesis.limitations.summary}",
            ]

            evidence = []
            for pt in [
                synthesis.problem_statement,
                synthesis.methodology,
                synthesis.dataset_used,
                synthesis.key_results,
                synthesis.limitations,
            ]:
                if pt.source_excerpt:
                    evidence.append({
                        "chunk_id": pt.chunk_id or f"{doc.id}_synthesis",
                        "document_id": doc.id,
                        "document_title": title,
                        "page_number": pt.page_number or 1,
                        "section_title": pt.section_title or pt.topic,
                        "content_text": pt.source_excerpt,
                        "score": 1.0,
                    })

            return {
                "output": "\n\n".join(text_parts),
                "evidence_chunks": evidence,
            }
        except Exception as e:
            logger.error(f"Error in extract_document_summary tool: {str(e)}")
            return {
                "output": f"Tool error extracting summary for '{title}': {str(e)}",
                "evidence_chunks": [],
            }

    @classmethod
    def execute_tool(
        cls,
        tool_name: str,
        tool_args: Dict[str, Any],
        tenant_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Dispatches tool call with tenant injection and error boundary.
        """
        name = tool_name.strip()
        args = tool_args or {}

        if name == "search_workspace":
            query = args.get("query", "")
            return cls.search_workspace(query=query, tenant_id=tenant_id, db=db)

        elif name == "read_document_section":
            doc_id = args.get("document_id", "")
            sec = args.get("section_name", "")
            return cls.read_document_section(document_id=doc_id, section_name=sec, tenant_id=tenant_id, db=db)

        elif name == "extract_document_summary":
            doc_id = args.get("document_id", "")
            return cls.extract_document_summary(document_id=doc_id, tenant_id=tenant_id, db=db)

        elif name == "finish_research":
            return {
                "output": "Research phase completed. Proceeding to final report synthesis.",
                "evidence_chunks": [],
            }

        else:
            return {
                "output": f"Unknown tool '{name}'. Available tools: search_workspace, read_document_section, extract_document_summary, finish_research.",
                "evidence_chunks": [],
            }


# Convenient instance / alias
agent_tools = AgentToolRegistry

