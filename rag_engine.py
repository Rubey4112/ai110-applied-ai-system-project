import numpy as np
from dataclasses import dataclass
from typing import List

import faiss
from sentence_transformers import SentenceTransformer


_model: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


@dataclass
class VectorIndex:
    """Holds a FAISS index paired with the original text chunks."""
    index: faiss.Index
    chunks: List[str]


def build_index(chunks: List[str]) -> VectorIndex:
    """Embed chunks and build a FAISS index for cosine similarity search.

    Args:
        chunks (List[str]): Text chunks to embed and index.

    Returns:
        VectorIndex: The built index paired with the original chunks.
    """
    model = _get_model()
    embeddings = model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
    dim = embeddings.shape[1]
    # IndexFlatIP on L2-normalized vectors gives cosine similarity
    idx = faiss.IndexFlatIP(dim)
    idx.add(embeddings.astype(np.float32))
    return VectorIndex(index=idx, chunks=chunks)


def retrieve(query: str, vector_index: VectorIndex, top_k: int = 10) -> List[str]:
    """Retrieve the top-k most semantically similar chunks for a query.

    Args:
        query (str): The search query string.
        vector_index (VectorIndex): A built VectorIndex.
        top_k (int): Maximum number of chunks to return.

    Returns:
        List[str]: The most relevant text chunks, in descending similarity order.
    """
    model = _get_model()
    q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    k = min(top_k, len(vector_index.chunks))
    _, indices = vector_index.index.search(q_emb.astype(np.float32), k)
    return [vector_index.chunks[i] for i in indices[0] if i < len(vector_index.chunks)]
