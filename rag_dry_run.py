"""Dry-run script for the RAG pipeline.

Tests document parsing, chunking, indexing, and retrieval without calling the
Claude API. Run with a file argument or use the built-in sample text.

Usage:
    python rag_dry_run.py                    # uses built-in sample text
    python rag_dry_run.py myfile.pdf         # uses a real file
    python rag_dry_run.py myfile.pdf --query "photosynthesis"
"""

import argparse
import sys

from document_parser import chunk_text
from question_generator import build_query_for_difficulty
from rag_engine import build_index, retrieve

SAMPLE_TEXT = """
Photosynthesis is the process by which plants, algae, and some bacteria convert
light energy into chemical energy stored as glucose. It occurs in the chloroplasts
and involves two main stages: the light-dependent reactions and the Calvin cycle.

In the light-dependent reactions, chlorophyll absorbs sunlight and uses that energy
to split water molecules, releasing oxygen as a byproduct and producing ATP and NADPH.

The Calvin cycle (light-independent reactions) uses the ATP and NADPH produced in the
first stage to fix carbon dioxide from the air into glucose molecules. This process
is also called carbon fixation.

Cellular respiration is the reverse process. Cells break down glucose in the presence
of oxygen to release energy in the form of ATP. The byproducts are carbon dioxide
and water. Respiration occurs in the mitochondria.

Mitosis is cell division that produces two identical daughter cells. It has four
phases: prophase, metaphase, anaphase, and telophase. It is used for growth and
tissue repair. Meiosis, by contrast, produces four genetically unique cells and is
used for sexual reproduction.

DNA carries genetic information in sequences of four bases: adenine, thymine, guanine,
and cytosine. Adenine pairs with thymine; guanine pairs with cytosine. During DNA
replication, the double helix unwinds and each strand serves as a template for a
new complementary strand.
"""


def main():
    parser = argparse.ArgumentParser(description="RAG pipeline dry run")
    parser.add_argument("file", nargs="?", help="Path to a PDF, TXT, or DOCX file")
    parser.add_argument("--query", default=None, help="Custom retrieval query")
    parser.add_argument("--difficulty", default="Normal", choices=["Easy", "Normal", "Hard"])
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    # ── Step 1: get text ───────────────────────────────────────────────────────
    if args.file:
        print(f"Reading file: {args.file}")
        import io
        with open(args.file, "rb") as f:
            class _FakeUpload:
                name = args.file
                def read(self): return f.read()
            from document_parser import extract_text
            text = extract_text(_FakeUpload())
    else:
        print("No file provided — using built-in sample text.")
        text = SAMPLE_TEXT

    print(f"\n[1] Text length: {len(text.split())} words\n")

    # ── Step 2: chunk ──────────────────────────────────────────────────────────
    chunks = chunk_text(text)
    print(f"[2] Chunks created: {len(chunks)}")
    for i, c in enumerate(chunks):
        print(f"    Chunk {i}: {len(c.split())} words — \"{c[:60].strip()}…\"")

    # ── Step 3: build index ────────────────────────────────────────────────────
    print("\n[3] Building FAISS index (this downloads the model on first run)…")
    index = build_index(chunks)
    print(f"    Index built with {index.index.ntotal} vectors.")

    # ── Step 4: retrieve ───────────────────────────────────────────────────────
    query = args.query or build_query_for_difficulty(args.difficulty)
    print(f"\n[4] Retrieval query ({args.difficulty}): \"{query}\"")
    results = retrieve(query, index, top_k=args.top_k)

    print(f"\n[5] Top {len(results)} retrieved chunks (this is what would be sent to Claude):\n")
    print("=" * 70)
    for i, chunk in enumerate(results, 1):
        print(f"\n--- Chunk {i} ---")
        print(chunk)
    print("\n" + "=" * 70)
    print("\nDry run complete. No API call was made.")


if __name__ == "__main__":
    main()
