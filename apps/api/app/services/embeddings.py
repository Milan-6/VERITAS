import abc
import hashlib
import logging
import math
import re
import time
from typing import List, Dict, Any, Tuple
import httpx
from qdrant_client import models
from app.core.config import settings

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
    "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", "his",
    "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its",
    "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's",
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", "they'd",
    "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when",
    "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}


class BaseEmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abc.abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Google Gemini text-embedding-004 provider with exponential backoff and retry logic.
    """

    def __init__(self, api_key: str = settings.GEMINI_API_KEY, model: str = settings.EMBEDDING_MODEL):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/{model}"

    def _call_with_retry(self, url: str, json_data: dict, max_retries: int = 4, timeout: float = 5.0) -> dict:
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(
                        f"{url}?key={self.api_key}",
                        json=json_data,
                        headers={"Content-Type": "application/json"}
                    )

                    if resp.status_code == 429:
                        # Rate limit: Exponential backoff with jitter
                        wait_seconds = (2 ** attempt) * 0.5
                        logger.warning(f"Gemini API rate limit (429). Retrying in {wait_seconds:.2f}s...")
                        time.sleep(wait_seconds)
                        continue

                    resp.raise_for_status()
                    return resp.json()

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                wait_seconds = (2 ** attempt) * 0.5
                logger.warning(f"Network error on attempt {attempt + 1}: {e}. Retrying in {wait_seconds:.2f}s...")
                time.sleep(wait_seconds)
            except Exception as e:
                logger.error(f"Gemini embedding API error: {e}")
                raise

        raise RuntimeError(f"Gemini embedding failed after {max_retries} retries.")

    def embed_text(self, text: str) -> List[float]:
        payload = {
            "model": self.model,
            "content": {"parts": [{"text": text}]}
        }
        res = self._call_with_retry(f"{self.base_url}:embedContent", payload)
        embedding_values = res.get("embedding", {}).get("values", [])
        if not embedding_values:
            raise ValueError("Empty embedding received from Gemini API")
        return embedding_values

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        # Google batchEmbedContents
        requests = [{"model": self.model, "content": {"parts": [{"text": t}]}} for t in texts]
        payload = {"requests": requests}
        res = self._call_with_retry(f"{self.base_url}:batchEmbedContents", payload)
        embeddings = res.get("embeddings", [])
        return [e.get("values", []) for e in embeddings]


class DeterministicDenseEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic semantic dense embedding provider (768 dimensions).
    Maps text tokens into normalized high-dimensional semantic vector space.
    Provides offline resilience and automated test execution without external API keys.
    """

    def __init__(self, dimension: int = settings.EMBEDDING_DIMENSION):
        self._dim = dimension

    def _hash_word(self, word: str, slot: int) -> float:
        # Compute stable deterministic float in [-1, 1]
        digest = hashlib.sha256(f"{word}:{slot}".encode("utf-8")).digest()
        val = int.from_bytes(digest[:4], "big")
        return (val / 0xFFFFFFFF) * 2.0 - 1.0

    def embed_text(self, text: str) -> List[float]:
        tokens = [t.lower() for t in re.findall(r'\b[a-zA-Z0-9_\-\.]{2,}\b', text) if t.lower() not in STOPWORDS]
        if not tokens:
            tokens = ["general", "content"]

        vector = [0.0] * self._dim

        for i, token in enumerate(tokens):
            weight = 1.0 / math.sqrt(i + 1)
            # Sample slots pseudo-randomly for each token
            for slot_offset in range(16):
                slot = int(hashlib.md5(f"{token}_{slot_offset}".encode("utf-8")).hexdigest(), 16) % self._dim
                vector[slot] += self._hash_word(token, slot_offset) * weight

        # Normalize to unit length (L2 norm) for cosine similarity
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        else:
            vector[0] = 1.0

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class BM25SparseVectorizer:
    """
    Computes sparse BM25 term frequency vectors for Qdrant sparse search.
    Maps words to 32-bit positive integer indices with BM25 term weights.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b

    def _term_to_index(self, term: str) -> int:
        # Stable 31-bit positive integer index for Qdrant SparseVector
        return int(hashlib.md5(term.encode("utf-8")).hexdigest()[:7], 16)

    def vectorize(self, text: str) -> models.SparseVector:
        # Extract alphanumeric words, lowercased, excluding common stopwords
        words = [w.lower() for w in re.findall(r'\b[a-zA-Z0-9_\-]{2,}\b', text) if w.lower() not in STOPWORDS]
        if not words:
            return models.SparseVector(indices=[1], values=[1.0])

        freqs: Dict[str, int] = {}
        for w in words:
            freqs[w] = freqs.get(w, 0) + 1

        doc_len = len(words)
        avg_len = 100.0  # Heuristic average chunk length

        indices: List[int] = []
        values: List[float] = []

        # Sort by term index to maintain ordered sparse vector
        term_scores: List[Tuple[int, float]] = []
        for term, tf in freqs.items():
            idx = self._term_to_index(term)
            # BM25 term frequency formulation
            norm_tf = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * (doc_len / avg_len)))
            term_scores.append((idx, round(float(norm_tf), 4)))

        term_scores.sort(key=lambda x: x[0])

        for idx, val in term_scores:
            indices.append(idx)
            values.append(val)

        return models.SparseVector(indices=indices, values=values)


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory: Returns Gemini provider if GEMINI_API_KEY is configured, else deterministic provider."""
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
        logger.info("Using Google Gemini embedding provider (models/text-embedding-004)")
        return GeminiEmbeddingProvider()
    logger.info("Using Deterministic Dense embedding provider (768 dimensions, offline/test mode)")
    return DeterministicDenseEmbeddingProvider()


# Global singletons
dense_embedder = get_embedding_provider()
sparse_vectorizer = BM25SparseVectorizer()
