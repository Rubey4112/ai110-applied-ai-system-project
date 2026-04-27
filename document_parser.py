import io
import re
from typing import List


def clean_text(text: str) -> str:
    """Remove extraction artifacts without stripping meaningful words.

    Targets PDF/DOCX noise: garbled ligatures, null bytes, repeated
    whitespace, and isolated page-number lines. Does NOT remove stop words —
    transformer embeddings rely on full natural language input.

    Args:
        text (str): Raw extracted text.

    Returns:
        str: Cleaned text.
    """
    # Replace common PDF ligature encodings with ASCII equivalents
    ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
    for bad, good in ligatures.items():
        text = text.replace(bad, good)

    # Strip null bytes and other non-printable control characters (keep newlines/tabs)
    text = re.sub(r"[^\S\n\t ]+", " ", text)  # collapse weird whitespace
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Drop lines that are just a number (page numbers)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Collapse 3+ consecutive newlines down to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_text(uploaded_file) -> str:
    """Extract plain text from an uploaded file (PDF, TXT, or DOCX).

    Args:
        uploaded_file: A Streamlit UploadedFile object.

    Returns:
        str: The extracted plain text content.

    Raises:
        ValueError: If the file type is not supported.
    """
    name = uploaded_file.name.lower()

    if name.endswith(".txt"):
        return clean_text(uploaded_file.read().decode("utf-8", errors="ignore"))

    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        raw = "\n".join(page.extract_text() or "" for page in reader.pages)
        return clean_text(raw)

    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(uploaded_file.read()))
        raw = "\n".join(p.text for p in doc.paragraphs)
        return clean_text(raw)

    raise ValueError(f"Unsupported file type: {uploaded_file.name}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks by word count.

    Args:
        text (str): The full document text.
        chunk_size (int): Number of words per chunk.
        overlap (int): Number of words shared between consecutive chunks.

    Returns:
        List[str]: List of text chunks.
    """
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks
