import json
import logging
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from .llm_client import LLMClient

logger = logging.getLogger(__name__)

_VALID_ANSWERS = {"A", "B", "C", "D"}
_OVERFETCH_RATIO = 0.5  # request 50% extra questions to absorb relevance filtering


def _validate_questions(questions: list, expected_count: int) -> list:
    """Filters structurally malformed questions. Raises if fewer than expected_count survive."""
    valid = []
    for q in questions:
        if not all(k in q for k in ("question", "choices", "answer")):
            continue
        if not q["question"].strip():
            continue
        if len(q["choices"]) != 4:
            continue
        if str(q["answer"]).upper() not in _VALID_ANSWERS:
            continue
        valid.append(q)

    if len(valid) < expected_count:
        raise ValueError(
            f"Only {len(valid)}/{expected_count} valid questions returned by LLM"
        )
    return valid


def _check_relevance(questions: list, context_chunks: list, threshold: float = 0.35) -> dict:
    """Returns a dict mapping flagged question text to its cosine similarity score."""
    if not questions:
        return {}

    model = SentenceTransformer("all-MiniLM-L6-v2")
    context_embedding = model.encode(" ".join(context_chunks))

    flagged = {}
    for q in questions:
        q_embedding = model.encode(q["question"])
        similarity = float(
            np.dot(q_embedding, context_embedding)
            / (np.linalg.norm(q_embedding) * np.linalg.norm(context_embedding))
        )
        if similarity < threshold:
            flagged[q["question"]] = similarity
    return flagged


class QuestionGenerator:
    _QUERIES = {
        "Easy": "key terms, basic definitions, and fundamental concepts",
        "Normal": "important concepts, processes, and factual information",
        "Hard": "detailed mechanisms, comparisons, exceptions, and nuanced relationships",
    }

    def __init__(self, client: Optional[LLMClient] = None, provider: str = "claude", model: Optional[str] = None):
        self._client = client or LLMClient(provider=provider, model=model)

    @classmethod
    def query_for_difficulty(cls, difficulty: str) -> str:
        return cls._QUERIES.get(difficulty, cls._QUERIES["Normal"])

    def generate(self, context_chunks: List[str], num_questions: int) -> List[dict]:
        request_count = num_questions + max(2, int(num_questions * _OVERFETCH_RATIO))
        context = "\n\n---\n\n".join(context_chunks)
        prompt = (
            f"You are a quiz generator. Based on the following study material, "
            f"generate exactly {request_count} multiple-choice questions.\n\n"
            f"STUDY MATERIAL:\n{context}\n\n"
            f"CRITICAL CONSTRAINTS:\n"
            f"- Every question and its correct answer MUST be directly supported by the study material above.\n"
            f"- Do NOT introduce facts, definitions, or knowledge from outside the provided text.\n"
            f"OUTPUT FORMAT: Return only a JSON array with no surrounding text or markdown fences. "
            f"Each element must have:\n"
            f'- "question": the question text\n'
            f'- "choices": array of exactly 4 strings, each prefixed with "A. ", "B. ", "C. ", "D. "\n'
            f'- "answer": one of "A", "B", "C", or "D"\n\n'
            f"Make wrong answers plausible. Questions should test understanding, not trivial recall.\n"
            f"For math or engineering content, use LaTeX notation where appropriate: "
            f"inline math with $...$ and display math with $$...$$."
        )

        raw = self._client.complete(prompt).strip()
        if raw.startswith("```"):
            parts = raw.split("```", 2)
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            questions = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}") from e
        if not isinstance(questions, list) or not questions:
            raise ValueError("LLM returned unexpected format — expected a non-empty JSON array")

        questions = _validate_questions(questions, expected_count=num_questions)

        flagged = _check_relevance(questions, context_chunks)
        relevant = [q for q in questions if q["question"] not in flagged]
        dropped = len(questions) - len(relevant)

        if dropped:
            for i, (text, score) in enumerate(flagged.items(), 1):
                logger.warning(
                    "Dropped question %d (similarity=%.3f < threshold=0.35): %s",
                    i, score, text,
                )
            logger.warning(
                "%d question(s) dropped as potentially irrelevant; %d of %d requested remain.",
                dropped, len(relevant), num_questions,
            )
        else:
            logger.info("Relevance check passed: all %d questions are on-topic.", len(questions))

        if len(relevant) >= num_questions:
            return relevant[:num_questions]

        logger.warning(
            "Only %d relevant question(s) available after filtering; needed %d.",
            len(relevant), num_questions,
        )
        return relevant
