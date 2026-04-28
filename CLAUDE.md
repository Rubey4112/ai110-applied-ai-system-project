# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
python -m streamlit run app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_question_generator.py

# Run a single test by name
pytest tests/test_question_generator.py::test_generate_questions_returns_list -v
```

Dependencies are managed via `requirements.txt`. Use a virtual environment (`.venv` is present).

API keys go in `.env` (copy `.env.example`):
- `ANTHROPIC_API_KEY` — for the Claude provider
- `GEMINI_API_KEY` — for the Gemini provider

## Architecture

**QuizFoundary** is a Streamlit app that turns uploaded study documents into playable multiple-choice quizzes using a RAG pipeline and an LLM.

### Data flow

```
uploaded file → DocumentParser → RAGEngine (FAISS) → QuestionGenerator → LLMClient → QuizSession
```

1. `DocumentParser` (`quiz/pipeline.py`) extracts text from PDF/TXT/DOCX, cleans it, and splits it into overlapping word-count chunks (default 500 words, 50-word overlap).
2. `RAGEngine` (`quiz/pipeline.py`) encodes chunks with `all-MiniLM-L6-v2` via FAISS `IndexFlatIP` (inner-product search on L2-normalized embeddings). The index lives in Streamlit session state — it is rebuilt from scratch each session.
3. `QuestionGenerator` (`quiz/questions.py`) retrieves the top-k chunks, builds a prompt, calls `LLMClient`, parses the JSON array response, validates structure (`_validate_questions`), and filters off-topic questions via cosine similarity (`_check_relevance`). It over-fetches by 50% to absorb filtering losses.
4. `LLMClient` (`quiz/llm_client.py`) is the single LLM abstraction. It supports `claude` (via `anthropic` SDK) and `gemini` (via `google-genai` SDK) with a `dry_run` mode that returns stub JSON. Gemini calls include exponential-backoff retry on HTTP 429.
5. `QuizSession` (`quiz/session.py`) is a pure logic class — answer validation, score updates, and question counts per difficulty. It holds no Streamlit state.
6. `app.py` owns all `st.session_state` and drives a four-state machine: `idle → ready → playing → finished`.

### State machine (`app.py`)

| State | What's happening |
|-------|-----------------|
| `idle` | File upload or sample material selection |
| `ready` | Document indexed; waiting for user to start quiz |
| `playing` | Showing questions one at a time |
| `finished` | Score summary and answer review |

`_reset_to(status)` wipes all session state and sets a new status.

### Key design constraints

- **LLM providers**: Default models are `claude-sonnet-4-6` and `gemini-2.5-flash`. When updating model IDs, change `_DEFAULT_MODELS` in `quiz/llm_client.py`.
- **Question counts**: Easy=5, Normal=10, Hard=15, defined in `QuizSession._QUESTION_COUNTS`.
- **Scoring**: Correct = `max(10, 100 − 10 × question_number)`; Wrong = −10.
- **LaTeX rendering**: The prompt instructs the LLM to use `$...$` / `$$...$$` notation; Streamlit renders this via KaTeX. CSS overrides in `app.py` handle display-math overflow.
- **No persistent storage**: All quiz state is in `st.session_state` and is lost when the tab closes.

### Testing approach

Tests in `tests/` use `unittest.mock` to avoid real LLM/embedding calls. `SentenceTransformer` is patched at `quiz.questions.SentenceTransformer` in every test via an `autouse` fixture in `test_question_generator.py`. `LLMClient` is replaced with a `MagicMock` whose `.complete()` returns a JSON string.
