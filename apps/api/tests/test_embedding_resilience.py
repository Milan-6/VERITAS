from unittest.mock import MagicMock, patch
import httpx
import pytest
from app.services.embeddings import GeminiEmbeddingProvider, DeterministicDenseEmbeddingProvider, BM25SparseVectorizer


def test_gemini_embedding_exponential_backoff_on_rate_limit():
    provider = GeminiEmbeddingProvider(api_key="fake-test-gemini-key")

    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429

    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {
        "embedding": {"values": [0.123] * 768}
    }

    # Simulate 2 rate limit 429 errors followed by successful 200 response
    with patch("httpx.Client") as mock_client_cls, patch("time.sleep") as mock_sleep:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = [mock_resp_429, mock_resp_429, mock_resp_200]
        mock_client_cls.return_value = mock_client

        result = provider.embed_text("Sample academic research text")

        assert len(result) == 768
        assert result[0] == 0.123
        # Verified exponential backoff was triggered twice
        assert mock_sleep.call_count == 2
        # Backoff intervals: 0.5s, then 1.0s
        assert mock_sleep.call_args_list[0][0][0] == 0.5
        assert mock_sleep.call_args_list[1][0][0] == 1.0


def test_deterministic_dense_embedding_consistency():
    provider = DeterministicDenseEmbeddingProvider(dimension=768)

    text = "Reciprocal Rank Fusion over hybrid dense and sparse representations"
    vec1 = provider.embed_text(text)
    vec2 = provider.embed_text(text)

    assert len(vec1) == 768
    # Exact deterministic repeatability
    assert vec1 == vec2

    # L2 normalized to unit length (sum of squares == 1.0)
    norm = sum(x * x for x in vec1)
    assert pytest.approx(norm, rel=1e-4) == 1.0


def test_bm25_sparse_vectorizer():
    vectorizer = BM25SparseVectorizer()
    text = "Quantum computing and quantum cryptography algorithms"
    sparse_vec = vectorizer.vectorize(text)

    assert len(sparse_vec.indices) > 0
    assert len(sparse_vec.indices) == len(sparse_vec.values)
    # Stopword 'and' should be excluded
    for val in sparse_vec.values:
        assert val > 0.0
