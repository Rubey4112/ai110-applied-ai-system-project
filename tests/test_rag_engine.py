import numpy as np
import pytest
from unittest.mock import MagicMock
from quiz.pipeline import RAGEngine


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


# --- RAGEngine.build ---

def test_build_returns_rag_engine():
    result = RAGEngine(_model=_make_mock_model()).build(["a", "b", "c"])
    assert isinstance(result, RAGEngine)


def test_build_preserves_chunks():
    chunks = ["alpha", "beta", "gamma"]
    engine = RAGEngine(_model=_make_mock_model()).build(chunks)
    assert engine._chunks == chunks


def test_build_faiss_total_matches_chunk_count():
    chunks = [f"chunk {i}" for i in range(7)]
    engine = RAGEngine(_model=_make_mock_model()).build(chunks)
    assert engine._index.ntotal == 7


def test_build_single_chunk():
    engine = RAGEngine(_model=_make_mock_model()).build(["only one"])
    assert engine._index.ntotal == 1
    assert len(engine._chunks) == 1


# --- RAGEngine.retrieve ---

def test_retrieve_returns_list_of_strings():
    engine = RAGEngine(_model=_make_mock_model()).build(["a", "b", "c"])
    results = engine.retrieve("query", top_k=2)
    assert isinstance(results, list)
    assert all(isinstance(r, str) for r in results)


def test_retrieve_respects_top_k():
    engine = RAGEngine(_model=_make_mock_model()).build([f"chunk {i}" for i in range(10)])
    results = engine.retrieve("query", top_k=3)
    assert len(results) == 3


def test_retrieve_caps_at_available_chunks():
    engine = RAGEngine(_model=_make_mock_model()).build(["only", "two"])
    results = engine.retrieve("query", top_k=100)
    assert len(results) == 2


def test_retrieve_results_are_subset_of_original_chunks():
    chunks = [f"chunk {i}" for i in range(5)]
    engine = RAGEngine(_model=_make_mock_model()).build(chunks)
    results = engine.retrieve("query", top_k=3)
    for r in results:
        assert r in chunks


def test_retrieve_returns_single_result_for_top_k_one():
    engine = RAGEngine(_model=_make_mock_model()).build(["x", "y", "z"])
    results = engine.retrieve("query", top_k=1)
    assert len(results) == 1


def test_retrieve_no_duplicates():
    engine = RAGEngine(_model=_make_mock_model()).build([f"chunk {i}" for i in range(8)])
    results = engine.retrieve("query", top_k=5)
    assert len(results) == len(set(results))
