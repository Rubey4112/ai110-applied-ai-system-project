class QuizSession:
    _QUESTION_COUNTS = {"Easy": 5, "Normal": 10, "Hard": 15}

    def __init__(self, difficulty: str = "Normal"):
        self.difficulty = difficulty
        self.score = 0

    @property
    def question_count(self) -> int:
        return self._QUESTION_COUNTS.get(self.difficulty, 10)

    @staticmethod
    def parse_answer(raw) -> tuple:
        if not raw:
            return False, None, "Select an answer."
        letter = str(raw)[0].upper()
        if letter not in ("A", "B", "C", "D"):
            return False, None, "Invalid selection."
        return True, letter, None

    @staticmethod
    def check_answer(selected: str, correct: str) -> tuple:
        if selected == correct:
            return "Correct", "Correct!"
        return "Wrong", f"Wrong! The correct answer was {correct}."

    @staticmethod
    def update_score(current_score: int, outcome: str, question_number: int) -> int:
        if outcome == "Correct":
            return current_score + max(10, 100 - 10 * question_number)
        if outcome == "Wrong":
            return current_score - 10
        return current_score
