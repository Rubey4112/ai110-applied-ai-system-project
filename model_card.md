# Model Card: QuizFoundary

## 1. Model Name  

**QuizFoundary** — an AI-powered quiz generation system that converts uploaded study documents into playable multiple-choice quizzes.

---

## 2. Intended Use  

QuizFoundary is designed for students and learners who want to self-test on material they have already studied. A user uploads a PDF, TXT, or DOCX document (e.g., lecture notes, a textbook chapter, or a study guide), selects a difficulty level (Easy / Normal / Hard), and the system automatically generates a multiple-choice quiz grounded in that document. It is not intended for high-stakes assessment or as a substitute for instructor-authored exams.

---

## 3. How the Model Works  

QuizFoundary uses a Retrieval-Augmented Generation (RAG) pipeline:

1. **Document parsing** — the uploaded file is extracted and cleaned, then split into overlapping 500-word chunks (50-word overlap) to preserve context across boundaries.
2. **Embedding and retrieval** — each chunk is encoded with `all-MiniLM-L6-v2` (sentence-transformers) and stored in a FAISS inner-product index. At quiz time, a difficulty-specific query retrieves the top-10 most relevant chunks.
3. **Question generation** — the retrieved chunks are assembled into a prompt and sent to an LLM (Claude `claude-sonnet-4-6` or Gemini `gemini-2.5-flash`). The prompt instructs the model to produce only questions directly supported by the provided text, formatted as a JSON array of 4-choice questions.
4. **Validation and relevance filtering** — generated questions are checked for structural completeness (required fields, exactly 4 choices, valid answer key) and then filtered for on-topic relevance using cosine similarity between the question embedding and the context embedding (`all-MiniLM-L6-v2`, threshold 0.35). The system over-fetches by 50% to absorb questions lost to filtering.
5. **Scoring** — answers are scored with a diminishing-returns formula: correct answer on question *n* awards `max(10, 100 − 10 × n)` points; each wrong answer deducts 10 points.

---

## 4. Data  

The system uses no fixed training dataset. Instead, it operates entirely over user-supplied documents at inference time. The underlying LLM (Claude or Gemini) was pre-trained on large web-scale corpora by Anthropic and Google respectively — those training sets are not disclosed by their providers. The embedding model (`all-MiniLM-L6-v2`) was trained by the sentence-transformers project on a mix of NLI and semantic similarity datasets.

---

## 5. Strengths  

- **Grounded generation**: the prompt explicitly constrains the LLM to only use facts present in the uploaded material, reducing hallucinated or out-of-scope questions.
- **Relevance filtering**: a cosine similarity guard removes questions that stray from the source document even when the LLM ignores the constraint.
- **Flexible content**: supports PDF, TXT, and DOCX inputs across any academic subject, including STEM content with LaTeX rendering.
- **Difficulty differentiation**: retrieval queries and question counts are tuned per difficulty level (Easy: 5 Qs on basic definitions; Hard: 15 Qs on nuanced mechanisms and exceptions).
- **Provider flexibility**: works with either Claude (Anthropic) or Gemini (Google), with automatic retry on Gemini rate limits.

---

## 6. Limitations and Bias  

- **LLM hallucination**: despite the grounding constraint, the underlying LLM can still generate plausible-sounding but incorrect distractors or subtly wrong correct answers.
- **Relevance threshold is heuristic**: the 0.35 cosine similarity cutoff may incorrectly drop valid questions on highly technical or domain-specific vocabulary that diverges from general embedding space.
- **No persistent storage**: all quiz state lives in the browser session; there is no history, progress tracking, or adaptive difficulty across sessions.
- **Single-document scope**: the RAG index is rebuilt fresh each session from one document; the system cannot draw connections across multiple sources.
- **Embedding model bias**: `all-MiniLM-L6-v2` may underperform on non-English text or highly specialized technical notation.
- **LLM provider bias**: question style and difficulty calibration will differ between Claude and Gemini responses, and both models carry the biases of their respective pre-training corpora.
- **Chunk boundary effects**: questions may occasionally be incoherent when key context spans a chunk boundary.

---

## 7. Evaluation  

The system is evaluated through a combination of automated unit tests and manual spot-checks:

- **Unit tests** (`tests/`) cover `DocumentParser` (chunking, cleaning), `RAGEngine` (build and retrieve), `QuestionGenerator` (JSON parsing, validation, relevance filtering), and `QuizSession` (scoring, answer checking). All LLM and embedding calls are mocked with `unittest.mock` so tests run without API keys.
- **Structural validation**: `_validate_questions` enforces required fields, 4-choice constraint, and valid answer keys on every LLM response before questions reach the user.
- **Relevance guard**: `_check_relevance` uses embedding similarity to catch off-topic questions; the threshold (0.35) was chosen empirically to balance precision and recall.
- No formal held-out evaluation set or human-rater study has been conducted at this time.

---

## 8. Future Work  

- **Adaptive difficulty**: track per-user performance across sessions and dynamically adjust question difficulty.
- **Multi-document support**: allow the RAG index to span multiple uploaded files for broader coverage.
- **Human evaluation**: conduct a structured user study to measure question quality, relevance, and difficulty calibration.
- **Distractor quality scoring**: add a secondary check to ensure wrong answer choices are plausible but unambiguously incorrect.
- **Explanation mode**: after each question, show a highlighted excerpt from the source document that supports the correct answer.
- **Persistent sessions**: add optional account/session storage so users can resume quizzes or review past scores.
