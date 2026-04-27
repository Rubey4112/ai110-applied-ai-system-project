import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from rag_engine import build_index, retrieve, VectorIndex


DIM = 16  # small embedding dimension for fast mocked tests


def _make_mock_model(dim=DIM):
    """Return a mock SentenceTransformer whose encode() returns random L2-normalized vectors."""
    mock = MagicMock()

    def _encode(texts, convert_to_numpy=True, normalize_embeddings=True):
        n = len(texts)
        vecs = np.random.rand(n, dim).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / (norms + 1e-9)

    mock.encode.side_effect = _encode
    return mock


# --- build_index ---

def test_build_index_returns_vector_index():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        result = build_index(["a", "b", "c"])
    assert isinstance(result, VectorIndex)


def test_build_index_preserves_chunks():
    chunks = ["alpha", "beta", "gamma"]
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        result = build_index(chunks)
    assert result.chunks == chunks


def test_build_index_faiss_total_matches_chunk_count():
    chunks = [f"chunk {i}" for i in range(7)]
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        result = build_index(chunks)
    assert result.index.ntotal == 7


def test_build_index_single_chunk():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        result = build_index(["only one"])
    assert result.index.ntotal == 1
    assert len(result.chunks) == 1


# --- retrieve ---

def test_retrieve_returns_list_of_strings():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        vi = build_index(["a", "b", "c"])
        results = retrieve("query", vi, top_k=2)
    assert isinstance(results, list)
    assert all(isinstance(r, str) for r in results)


def test_retrieve_respects_top_k():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        vi = build_index([f"chunk {i}" for i in range(10)])
        results = retrieve("query", vi, top_k=3)
    assert len(results) == 3


def test_retrieve_caps_at_available_chunks():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        vi = build_index(["only", "two"])
        results = retrieve("query", vi, top_k=100)
    assert len(results) == 2


def test_retrieve_results_are_subset_of_original_chunks():
    chunks = [f"chunk {i}" for i in range(5)]
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        vi = build_index(chunks)
        results = retrieve("query", vi, top_k=3)
    for r in results:
        assert r in chunks


def test_retrieve_returns_single_result_for_top_k_one():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        vi = build_index(["x", "y", "z"])
        results = retrieve("query", vi, top_k=1)
    assert len(results) == 1


def test_retrieve_no_duplicates():
    with patch("rag_engine._get_model", return_value=_make_mock_model()):
        vi = build_index([f"chunk {i}" for i in range(8)])
        results = retrieve("query", vi, top_k=5)
    assert len(results) == len(set(results))
