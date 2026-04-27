import json
import os
from typing import List

import anthropic


def build_query_for_difficulty(difficulty: str) -> str:
    """Return a retrieval query tuned to the given difficulty level.

    Args:
        difficulty (str): "Easy", "Normal", or "Hard".

    Returns:
        str: A query string used to drive RAG retrieval.
    """
    queries = {
        "Easy": "key terms, basic definitions, and fundamental concepts",
        "Normal": "important concepts, processes, and factual information",
        "Hard": "detailed mechanisms, comparisons, exceptions, and nuanced relationships",
    }
    return queries.get(difficulty, queries["Normal"])


def generate_questions(context_chunks: List[str], num_questions: int) -> List[dict]:
    """Call the Claude API to generate multiple-choice questions from retrieved chunks.

    Args:
        context_chunks (List[str]): Text chunks retrieved from the RAG index.
        num_questions (int): Number of questions to generate.

    Returns:
        List[dict]: Each dict has keys:
            - "question" (str): The question text.
            - "choices" (List[str]): Exactly 4 strings prefixed "A. ", "B. ", "C. ", "D. ".
            - "answer" (str): One of "A", "B", "C", "D".

    Raises:
        ValueError: If the API response cannot be parsed as a valid question list.
    """
    context = "\n\n---\n\n".join(context_chunks)

    prompt = f"""You are a quiz generator. Based on the following study material, generate exactly {num_questions} multiple-choice questions.

STUDY MATERIAL:
{context}

OUTPUT FORMAT: Return only a JSON array with no surrounding text or markdown fences. Each element must have:
- "question": the question text
- "choices": array of exactly 4 strings, each prefixed with "A. ", "B. ", "C. ", "D. "
- "answer": one of "A", "B", "C", or "D"

Make wrong answers plausible. Questions should test understanding, not trivial recall."""

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if the model wraps its output
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
