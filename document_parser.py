import io
from typing import List


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
        return uploaded_file.read().decode("utf-8", errors="ignore")

    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(uploaded_file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(uploaded_file.read()))
        return "\n".join(p.text for p in doc.paragraphs)

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
