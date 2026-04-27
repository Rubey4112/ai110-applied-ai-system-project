from quiz_logic import parse_answer, check_answer, update_score, get_question_count_for_difficulty


def test_correct_answer():
    outcome, _ = check_answer("B", "B")
    assert outcome == "Correct"


def test_wrong_answer():
    outcome, _ = check_answer("A", "C")
    assert outcome == "Wrong"


def test_wrong_answer_message_includes_correct_letter():
    _, message = check_answer("A", "C")
    assert "C" in message


def test_parse_answer_extracts_letter_from_full_choice():
    ok, letter, err = parse_answer("B. Some answer text")
    assert ok
    assert letter == "B"
    assert err is None


def test_parse_answer_rejects_none():
    ok, letter, err = parse_answer(None)
    assert not ok
    assert letter is None
    assert err is not None


def test_parse_answer_rejects_empty_string():
    ok, letter, err = parse_answer("")
    assert not ok


def test_update_score_correct_early_question():
    # Question 1 correct: 100 - 10*1 = 90 points
    assert update_score(0, "Correct", 1) == 90


def test_update_score_correct_late_question_floors_at_10():
    # Question 10 correct: 100 - 100 = 0, floors to 10
    assert update_score(0, "Correct", 10) == 10


def test_update_score_wrong_applies_penalty():
    assert update_score(50, "Wrong", 1) == 40


def test_update_score_unknown_outcome_unchanged():
    assert update_score(50, "unknown", 1) == 50


def test_question_count_easy():
    assert get_question_count_for_difficulty("Easy") == 5


def test_question_count_normal():
    assert get_question_count_for_difficulty("Normal") == 10


def test_question_count_hard():
    assert get_question_count_for_difficulty("Hard") == 15
