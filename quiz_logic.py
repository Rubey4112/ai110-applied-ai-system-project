def get_question_count_for_difficulty(difficulty: str) -> int:
    """Return the number of quiz questions for a given difficulty.

    Args:
        difficulty (str): "Easy", "Normal", or "Hard".

    Returns:
        int: Number of questions to generate and ask.
    """
    return {"Easy": 5, "Normal": 10, "Hard": 15}.get(difficulty, 10)


def parse_answer(raw) -> tuple:
    """Validate a user's answer selection from a radio widget.

    Args:
        raw: The raw value from the Streamlit radio widget (str or None).

    Returns:
        tuple[bool, str | None, str | None]: (ok, letter, error_message).
            On success, letter is one of "A", "B", "C", "D".
    """
    if not raw:
        return False, None, "Select an answer."
    letter = str(raw)[0].upper()
    if letter not in ("A", "B", "C", "D"):
        return False, None, "Invalid selection."
    return True, letter, None


def check_answer(selected: str, correct: str) -> tuple:
    """Compare the selected answer letter to the correct answer letter.

    Args:
        selected (str): The player's answer letter (A–D).
        correct (str): The correct answer letter (A–D).

    Returns:
        tuple[str, str]: (outcome, message) where outcome is "Correct" or "Wrong".
    """
    if selected == correct:
        return "Correct", "Correct!"
    return "Wrong", f"Wrong! The correct answer was {correct}."


def update_score(current_score: int, outcome: str, question_number: int) -> int:
    """Calculate the updated score based on the answer outcome.

    Scoring rules:
    - "Correct": Awards ``max(10, 100 - 10 * question_number)`` points.
    - "Wrong": Applies a 10-point penalty.

    Args:
        current_score (int): The player's score before this question.
        outcome (str): "Correct" or "Wrong".
        question_number (int): 1-based question index used to scale win points.

    Returns:
        int: The updated score.
    """
    if outcome == "Correct":
        return current_score + max(10, 100 - 10 * question_number)
    if outcome == "Wrong":
        return current_score - 10
    return current_score
