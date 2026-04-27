import io
import re
from typing import List, Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


class DocumentParser:
    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    @staticmethod
    def _clean(text: str) -> str:
        ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
        for bad, good in ligatures.items():
            text = text.replace(bad, good)
        text = re.sub(r"[^\S\n\t ]+", " ", text)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def extract(self, uploaded_file) -> str:
        name = uploaded_file.name.lower()
        if name.endswith(".txt"):
            return self._clean(uploaded_file.read().decode("utf-8", errors="ignore"))
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            raw = "\n".join(page.extract_text() or "" for page in reader.pages)
            return self._clean(raw)
        if name.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(uploaded_file.read()))
            raw = "\n".join(p.text for p in doc.paragraphs)
            return self._clean(raw)
        raise ValueError(f"Unsupported file type: {uploaded_file.name}")

    def chunk(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        step = self.chunk_size - self.overlap
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        return chunks


class RAGEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", _model=None):
        self._model_name = model_name
        self._model = _model
        self._index: Optional[faiss.Index] = None
        self._chunks: List[str] = []

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def build(self, chunks: List[str]) -> RAGEngine:
        model = self._get_model()
        embeddings = model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
        dim = embeddings.shape[1]
        idx = faiss.IndexFlatIP(dim)
        idx.add(embeddings.astype(np.float32))
        self._index = idx
        self._chunks = list(chunks)
        return self

    def retrieve(self, query: str, top_k: int = 10) -> List[str]:
        if self._index is None:
            raise RuntimeError("Call build() before retrieve().")
        model = self._get_model()
        q_emb = model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        k = min(top_k, len(self._chunks))
        _, indices = self._index.search(q_emb.astype(np.float32), k)
        return [self._chunks[i] for i in indices[0] if i < len(self._chunks)]
