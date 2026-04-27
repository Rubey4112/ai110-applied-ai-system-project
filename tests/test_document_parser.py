import io
import pytest
from unittest.mock import MagicMock
from document_parser import clean_text, extract_text, chunk_text


# --- clean_text ---

def test_clean_text_replaces_fi_ligature():
    assert clean_text("ﬁle") == "file"


def test_clean_text_replaces_fl_ligature():
    assert clean_text("ﬂoor") == "floor"


def test_clean_text_replaces_ff_ligature():
    assert clean_text("diﬀerence") == "difference"


def test_clean_text_removes_null_bytes():
    assert "\x00" not in clean_text("hel\x00lo")


def test_clean_text_removes_control_characters():
    assert "\x08" not in clean_text("back\x08space")


def test_clean_text_removes_standalone_page_numbers():
    result = clean_text("Introduction\n42\nConclusion")
    assert "42" not in result.split()


def test_clean_text_does_not_remove_inline_numbers():
    result = clean_text("There are 42 species in this genus.")
    assert "42" in result


def test_clean_text_collapses_excessive_newlines():
    result = clean_text("line1\n\n\n\n\nline2")
    assert "\n\n\n" not in result


def test_clean_text_preserves_normal_sentence():
    text = "The mitochondria is the powerhouse of the cell."
    assert clean_text(text) == text


def test_clean_text_strips_leading_and_trailing_whitespace():
    assert clean_text("  hello world  ") == "hello world"


# --- chunk_text ---

def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("") == []


def test_chunk_text_short_text_produces_single_chunk():
    text = "short text with just a few words"
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_produces_correct_count():
    # 100 words, chunk_size=50, overlap=10 → step=40
    # range(0, 100, 40) = [0, 40, 80] → 3 chunks
    words = " ".join(f"word{i}" for i in range(100))
    chunks = chunk_text(words, chunk_size=50, overlap=10)
    assert len(chunks) == 3


def test_chunk_text_each_chunk_respects_max_size():
    words = " ".join(f"word{i}" for i in range(1000))
    chunks = chunk_text(words, chunk_size=100, overlap=10)
    for chunk in chunks:
        assert len(chunk.split()) <= 100


def test_chunk_text_overlap_between_consecutive_chunks():
    # chunk_size=100, overlap=20, step=80
    # chunk[0] = words[0:100], chunk[1] = words[80:180]
    # last 20 of chunk[0] and first 20 of chunk[1] must match
    words = [f"word{i}" for i in range(200)]
    chunks = chunk_text(" ".join(words), chunk_size=100, overlap=20)
    tail = chunks[0].split()[-20:]
    head = chunks[1].split()[:20]
    assert tail == head


def test_chunk_text_default_params_produce_multiple_chunks():
    # 600 words, default chunk_size=500, overlap=50 → step=450 → 2 chunks
    words = " ".join(f"word{i}" for i in range(600))
    chunks = chunk_text(words)
    assert len(chunks) == 2


# --- extract_text ---

def test_extract_text_txt_returns_content():
    mock_file = MagicMock()
    mock_file.name = "notes.txt"
    mock_file.read.return_value = b"Hello world"
    assert "Hello world" in extract_text(mock_file)


def test_extract_text_txt_applies_clean_text():
    mock_file = MagicMock()
    mock_file.name = "notes.txt"
    mock_file.read.return_value = "ﬁle content\n99\nmore text".encode("utf-8")
    result = extract_text(mock_file)
    assert "fi" in result
    assert "99" not in result.split()


def test_extract_text_unsupported_format_raises():
    mock_file = MagicMock()
    mock_file.name = "document.xyz"
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(mock_file)


def test_extract_text_csv_raises():
    mock_file = MagicMock()
    mock_file.name = "data.csv"
    with pytest.raises(ValueError):
        extract_text(mock_file)
