import json
import os
from typing import List

import anthropic


class QuestionGenerator:
    _QUERIES = {
        "Easy": "key terms, basic definitions, and fundamental concepts",
        "Normal": "important concepts, processes, and factual information",
        "Hard": "detailed mechanisms, comparisons, exceptions, and nuanced relationships",
    }

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-6", client=None):
        self._model = model
        self._client = client or anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )

    @classmethod
    def query_for_difficulty(cls, difficulty: str) -> str:
        return cls._QUERIES.get(difficulty, cls._QUERIES["Normal"])

    def generate(self, context_chunks: List[str], num_questions: int) -> List[dict]:
        context = "\n\n---\n\n".join(context_chunks)
        prompt = (
            f"You are a quiz generator. Based on the following study material, "
            f"generate exactly {num_questions} multiple-choice questions.\n\n"
            f"STUDY MATERIAL:\n{context}\n\n"
            f"OUTPUT FORMAT: Return only a JSON array with no surrounding text or markdown fences. "
            f"Each element must have:\n"
            f'- "question": the question text\n'
            f'- "choices": array of exactly 4 strings, each prefixed with "A. ", "B. ", "C. ", "D. "\n'
            f'- "answer": one of "A", "B", "C", or "D"\n\n'
            f"Make wrong answers plausible. Questions should test understanding, not trivial recall."
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            parts = raw.split("```", 2)
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        questions = json.loads(raw)
        if not isinstance(questions, list) or not questions:
            raise ValueError("API returned unexpected format — expected a non-empty JSON array")
        return questions
