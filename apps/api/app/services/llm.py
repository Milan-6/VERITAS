import abc
import logging
import re
import time
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings
from app.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""You are the VERITAS Research Intelligence Assistant.
Product: {settings.PROJECT_NAME}
Tagline: {settings.TAGLINE}

You are a precise, objective, evidence-grounded academic research assistant.
Your answers must be STRICTLY grounded in the provided context chunks.

CORE OPERATING DIRECTIVES:
1. STRICT GROUNDING & ZERO HALLUCINATION:
   - Answer the question solely and exclusively using information explicitly stated in the CONTEXT CHUNKS.
   - Do NOT speculate, generalize, or introduce outside world knowledge.
2. STRICT ABSTENTION MANDATE:
   - If the provided CONTEXT CHUNKS do not contain sufficient evidence to answer the user's question, you MUST output EXACTLY:
     "{settings.STRICT_ABSTENTION_MESSAGE}"
   - Do NOT add apologies, preambles, greetings, or explanations. Only output the exact mandatory string.
3. INLINE CITATION PROVENANCE:
   - Every factual assertion, finding, number, or methodology cited MUST be followed immediately by its source provenance marker:
     [Document: <Document Title>, Page: <Page Number>]
   - Example: "Neural citation networks achieve 94.2% precision on benchmark datasets [Document: Neural Graph Reasoning, Page: 2]."
4. TONE:
   - Rigorous, scholarly, and concise.
"""


def format_context_block(chunks: List[RetrievedChunk]) -> str:
    """Formats retrieved chunks into an unambiguous context block for LLM synthesis."""
    if not chunks:
        return "NO CONTEXT AVAILABLE."

    blocks = []
    for idx, chunk in enumerate(chunks, 1):
        header = f"--- CONTEXT CHUNK {idx} [Document: {chunk.document_title}, Page: {chunk.page_number}, Section: {chunk.section_title}] ---"
        body = chunk.content_text.strip()
        blocks.append(f"{header}\n{body}")

    return "\n\n".join(blocks)


class BaseLLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate_response(
        self,
        query: str,
        context_chunks: List[RetrievedChunk],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Generates a grounded academic response using the query, context, and conversation history."""
        pass


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini LLM provider targeting gemini-2.0-flash / gemini-2.5-flash
    with temperature=0.0 for greedy deterministic decoding and exponential backoff retry.
    """

    def __init__(
        self,
        api_key: str = settings.GEMINI_API_KEY,
        model: str = settings.LLM_MODEL,
        temperature: float = settings.LLM_TEMPERATURE,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}"

    def _call_with_retry(self, url: str, json_data: dict, max_retries: int = 3, timeout: float = 15.0) -> dict:
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(
                        f"{url}?key={self.api_key}",
                        json=json_data,
                        headers={"Content-Type": "application/json"}
                    )

                    if resp.status_code == 429:
                        wait_seconds = (2 ** attempt) * 0.5
                        logger.warning(f"Gemini API 429 rate limit. Retrying in {wait_seconds:.2f}s...")
                        time.sleep(wait_seconds)
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                wait_seconds = (2 ** attempt) * 0.5
                logger.warning(f"Gemini network error on attempt {attempt + 1}: {e}. Retrying in {wait_seconds:.2f}s...")
                time.sleep(wait_seconds)
            except Exception as e:
                logger.error(f"Gemini LLM API error: {e}")
                raise

        raise RuntimeError(f"Gemini LLM call failed after {max_retries} attempts.")

    def generate_response(
        self,
        query: str,
        context_chunks: List[RetrievedChunk],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        context_block = format_context_block(context_chunks)

        user_content = (
            f"CONTEXT CHUNKS:\n{context_block}\n\n"
            f"USER QUERY: {query}\n\n"
            "REMINDER: Answer strictly using the context above with inline [Document: X, Page: Y] citations. "
            f"If the context does not answer the question, output EXACTLY: {settings.STRICT_ABSTENTION_MESSAGE}"
        )

        # Assemble conversation turns
        contents = []
        if chat_history:
            for turn in chat_history[-6:]:  # Keep recent history
                role = "user" if turn.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": turn.get("content", "")}]})

        contents.append({"role": "user", "parts": [{"text": user_content}]})

        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "topP": 0.0,
                "topK": 1,
            },
        }

        url = f"{self.base_url}:generateContent"
        data = self._call_with_retry(url, payload)

        candidates = data.get("candidates", [])
        if not candidates:
            return settings.STRICT_ABSTENTION_MESSAGE

        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts:
            return settings.STRICT_ABSTENTION_MESSAGE

        answer = content_parts[0].get("text", "").strip()
        return answer or settings.STRICT_ABSTENTION_MESSAGE


class DeterministicChatProvider(BaseLLMProvider):
    """
    Deterministic academic chat provider for local testing and offline execution.
    Inspects retrieved chunks for direct semantic grounding and enforces strict abstention.
    """

    def generate_response(
        self,
        query: str,
        context_chunks: List[RetrievedChunk],
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if not context_chunks:
            return settings.STRICT_ABSTENTION_MESSAGE

        query_terms = set(re.findall(r'\b[a-zA-Z0-9_\-\.]{3,}\b', query.lower()))
        # Remove common question words
        stopwords = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "does", "explain", "describe", "tell", "show"}
        keywords = query_terms - stopwords

        if not keywords:
            keywords = query_terms

        matched_sentences = []

        for chunk in context_chunks:
            sentences = re.split(r'(?<=[.!?])\s+', chunk.content_text)
            for s in sentences:
                s_lower = s.lower()
                matches = sum(1 for kw in keywords if kw in s_lower)
                if matches > 0:
                    matched_sentences.append((matches, s.strip(), chunk))

        if not matched_sentences:
            return settings.STRICT_ABSTENTION_MESSAGE

        # Sort by keyword match density
        matched_sentences.sort(key=lambda x: x[0], reverse=True)
        best_matches = matched_sentences[:2]

        response_parts = []
        for _, sentence, chunk in best_matches:
            citation = f"[Document: {chunk.document_title}, Page: {chunk.page_number}]"
            # Ensure proper punctuation before citation
            s_clean = sentence.rstrip(".")
            response_parts.append(f"{s_clean} {citation}.")

        return " ".join(response_parts)


def get_llm_provider() -> BaseLLMProvider:
    """Factory: returns Gemini provider if GEMINI_API_KEY is configured, else deterministic provider."""
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
        logger.info(f"Using Gemini LLM Provider ({settings.LLM_MODEL}, temp={settings.LLM_TEMPERATURE})")
        return GeminiLLMProvider()
    logger.info("Using Deterministic Academic Chat Provider (offline/test mode)")
    return DeterministicChatProvider()


llm_service = get_llm_provider()
