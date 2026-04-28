import json
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from quiz.questions import QuestionGenerator, _validate_questions, _check_relevance


# --- QuestionGenerator.query_for_difficulty ---

def test_build_query_easy_returns_nonempty_string():
    result = QuestionGenerator.query_for_difficulty("Easy")
    assert isinstance(result, str) and len(result) > 0


def test_build_query_normal_returns_nonempty_string():
    result = QuestionGenerator.query_for_difficulty("Normal")
    assert isinstance(result, str) and len(result) > 0


def test_build_query_hard_returns_nonempty_string():
    result = QuestionGenerator.query_for_difficulty("Hard")
    assert isinstance(result, str) and len(result) > 0


def test_build_query_all_difficulties_are_distinct():
    results = {QuestionGenerator.query_for_difficulty(d) for d in ["Easy", "Normal", "Hard"]}
    assert len(results) == 3


def test_build_query_unknown_difficulty_falls_back_to_normal():
    assert QuestionGenerator.query_for_difficulty("Unknown") == QuestionGenerator.query_for_difficulty("Normal")


def test_build_query_easy_mentions_basic_concepts():
    result = QuestionGenerator.query_for_difficulty("Easy").lower()
    assert "basic" in result or "fundamental" in result


def test_build_query_hard_mentions_nuanced_concepts():
    result = QuestionGenerator.query_for_difficulty("Hard").lower()
    assert "detailed" in result or "nuanced" in result or "mechanism" in result


# --- QuestionGenerator.generate helpers ---

def _make_questions(n=2):
    return [
        {
            "question": f"What is concept {i}?",
            "choices": [f"A. Option A{i}", f"B. Option B{i}", f"C. Option C{i}", f"D. Option D{i}"],
            "answer": "A",
        }
        for i in range(n)
    ]


def _mock_client(raw_text):
    mock_client = MagicMock()
    mock_client.complete.return_value = raw_text
    return mock_client


# --- QuestionGenerator.generate ---

def test_generate_questions_returns_list():
    questions = _make_questions(3)
    gen = QuestionGenerator(client=_mock_client(json.dumps(questions)))
    result = gen.generate(["context chunk"], num_questions=3)
    assert isinstance(result, list)
    assert len(result) == 3


def test_generate_questions_each_item_has_required_keys():
    questions = _make_questions(2)
    gen = QuestionGenerator(client=_mock_client(json.dumps(questions)))
    result = gen.generate(["context"], num_questions=2)
    for q in result:
        assert "question" in q
        assert "choices" in q
        assert "answer" in q


def test_generate_questions_strips_json_code_fence():
    questions = _make_questions(1)
    raw = "```json\n" + json.dumps(questions) + "\n```"
    gen = QuestionGenerator(client=_mock_client(raw))
    result = gen.generate(["context"], num_questions=1)
    assert len(result) == 1


def test_generate_questions_strips_plain_code_fence():
    questions = _make_questions(1)
    raw = "```\n" + json.dumps(questions) + "\n```"
    gen = QuestionGenerator(client=_mock_client(raw))
    result = gen.generate(["context"], num_questions=1)
    assert len(result) == 1


def test_generate_questions_invalid_json_raises_value_error():
    gen = QuestionGenerator(client=_mock_client("not valid json"))
    with pytest.raises(ValueError):
        gen.generate(["context"], num_questions=3)


def test_generate_questions_empty_array_raises_value_error():
    gen = QuestionGenerator(client=_mock_client("[]"))
    with pytest.raises(ValueError):
        gen.generate(["context"], num_questions=3)


def test_generate_questions_non_list_response_raises_value_error():
    gen = QuestionGenerator(client=_mock_client('{"key": "value"}'))
    with pytest.raises(ValueError):
        gen.generate(["context"], num_questions=3)


def test_generate_questions_multiple_chunks_joined_in_prompt():
    questions = _make_questions(1)
    mock = _mock_client(json.dumps(questions))
    gen = QuestionGenerator(client=mock)
    gen.generate(["chunk one", "chunk two", "chunk three"], num_questions=1)
    prompt = mock.complete.call_args[0][0]
    assert "---" in prompt


def test_generate_questions_passes_correct_model():
    from unittest.mock import patch
    questions = _make_questions(1)
    with patch("quiz.questions.LLMClient") as MockLLMClient:
        mock_instance = _mock_client(json.dumps(questions))
        MockLLMClient.return_value = mock_instance
        gen = QuestionGenerator()
        gen.generate(["context"], num_questions=1)
        MockLLMClient.assert_called_once_with(provider="claude", model=None)


# ---------------------------------------------------------------------------
# _validate_questions
# ---------------------------------------------------------------------------

def _make_valid_q(idx=0):
    return {
        "question": f"What is concept {idx}?",
        "choices": [f"A. Alpha{idx}", f"B. Beta{idx}", f"C. Gamma{idx}", f"D. Delta{idx}"],
        "answer": "A",
    }


def test_validate_questions_accepts_well_formed_input():
    questions = [_make_valid_q(i) for i in range(3)]
    result = _validate_questions(questions, expected_count=3)
    assert len(result) == 3


def test_validate_questions_filters_missing_question_key():
    bad = {"choices": ["A. a", "B. b", "C. c", "D. d"], "answer": "A"}
    good = _make_valid_q(1)
    result = _validate_questions([bad, good], expected_count=1)
    assert len(result) == 1
    assert "question" in result[0]


def test_validate_questions_filters_missing_choices_key():
    bad = {"question": "What?", "answer": "A"}
    good = _make_valid_q(1)
    result = _validate_questions([bad, good], expected_count=1)
    assert len(result) == 1


def test_validate_questions_filters_missing_answer_key():
    bad = {"question": "What?", "choices": ["A. a", "B. b", "C. c", "D. d"]}
    good = _make_valid_q(1)
    result = _validate_questions([bad, good], expected_count=1)
    assert len(result) == 1


def test_validate_questions_filters_wrong_number_of_choices():
    bad = _make_valid_q(0)
    bad["choices"] = ["A. a", "B. b", "C. c"]  # only 3
    good = _make_valid_q(1)
    result = _validate_questions([bad, good], expected_count=1)
    assert len(result) == 1
    assert result[0] is good


def test_validate_questions_filters_invalid_answer_letter():
    bad = _make_valid_q(0)
    bad["answer"] = "E"
    good = _make_valid_q(1)
    result = _validate_questions([bad, good], expected_count=1)
    assert len(result) == 1
    assert result[0] is good


def test_validate_questions_filters_blank_question_text():
    bad = _make_valid_q(0)
    bad["question"] = "   "
    good = _make_valid_q(1)
    result = _validate_questions([bad, good], expected_count=1)
    assert len(result) == 1
    assert result[0] is good


def test_validate_questions_raises_when_too_few_valid():
    # Only 1 valid question but 3 expected — should raise
    with pytest.raises(ValueError, match="valid questions"):
        _validate_questions([_make_valid_q()], expected_count=3)


def test_validate_questions_raises_when_all_invalid():
    bad1 = {"question": "Q?", "choices": ["A. a"], "answer": "A"}          # wrong num choices
    bad2 = {"question": "  ", "choices": ["A. a", "B. b", "C. c", "D. d"], "answer": "A"}  # blank
    with pytest.raises(ValueError):
        _validate_questions([bad1, bad2], expected_count=1)


def test_validate_questions_returns_all_valid_above_expected_count():
    # _validate_questions returns every structurally valid question; the caller slices
    questions = [_make_valid_q(i) for i in range(5)]
    result = _validate_questions(questions, expected_count=3)
    assert len(result) == 5


def test_validate_questions_accepts_lowercase_answer():
    q = _make_valid_q(0)
    q["answer"] = "b"
    result = _validate_questions([q], expected_count=1)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# _check_relevance
# The implementation uses SentenceTransformer; we mock it to control similarity
# values precisely.  Call order into model.encode():
#   [0]  = " ".join(context_chunks)   → context embedding
#   [1…] = each q["question"]          → question embeddings
# ---------------------------------------------------------------------------

_ST_PATCH = "quiz.questions.SentenceTransformer"


@pytest.fixture(autouse=True)
def _auto_mock_sentence_transformer():
    """Prevent the real SentenceTransformer from loading in every test.
    Tests that need specific similarity values override this with their own patch."""
    vec = np.array([1.0, 0.0, 0.0])
    with patch(_ST_PATCH) as MockST:
        MockST.return_value.encode.return_value = vec
        yield MockST


def test_check_relevance_returns_empty_list_for_high_similarity():
    # Identical unit vectors → cosine similarity = 1.0 → not flagged
    vec = np.array([1.0, 0.0, 0.0])
    with patch(_ST_PATCH) as MockST:
        MockST.return_value.encode.return_value = vec
        flagged = _check_relevance(
            [{"question": "What is photosynthesis?"}],
            ["Photosynthesis converts sunlight into chemical energy."],
            threshold=0.35,
        )
    assert flagged == []


def test_check_relevance_flags_orthogonal_question():
    # Orthogonal vectors → cosine similarity = 0.0 → flagged
    ctx_vec = np.array([1.0, 0.0, 0.0])
    q_vec = np.array([0.0, 1.0, 0.0])
    with patch(_ST_PATCH) as MockST:
        mock_model = MagicMock()
        mock_model.encode.side_effect = [ctx_vec, q_vec]
        MockST.return_value = mock_model
        flagged = _check_relevance(
            [{"question": "Who is the president of France?"}],
            ["Photosynthesis converts sunlight into chemical energy."],
            threshold=0.35,
        )
    assert "Who is the president of France?" in flagged


def test_check_relevance_only_flags_low_similarity_questions():
    # 2 questions: one relevant (high similarity), one irrelevant (orthogonal)
    ctx_vec = np.array([1.0, 0.0, 0.0])
    relevant_vec = np.array([0.95, 0.31, 0.0])   # cos ≈ 0.95 → not flagged
    irrelevant_vec = np.array([0.0, 1.0, 0.0])   # cos = 0.0  → flagged
    with patch(_ST_PATCH) as MockST:
        mock_model = MagicMock()
        mock_model.encode.side_effect = [ctx_vec, relevant_vec, irrelevant_vec]
        MockST.return_value = mock_model
        flagged = _check_relevance(
            [
                {"question": "What does photosynthesis produce?"},
                {"question": "What is the capital of France?"},
            ],
            ["Photosynthesis converts sunlight into chemical energy."],
            threshold=0.35,
        )
    assert len(flagged) == 1
    assert "What is the capital of France?" in flagged
    assert "What does photosynthesis produce?" not in flagged


def test_check_relevance_boundary_at_threshold_is_not_flagged():
    # cos similarity exactly == threshold (0.35) → should NOT be flagged
    ctx_vec = np.array([1.0, 0.0, 0.0])
    # Unit vector whose dot with ctx_vec equals exactly 0.35
    at_threshold_vec = np.array([0.35, np.sqrt(1 - 0.35 ** 2), 0.0])
    with patch(_ST_PATCH) as MockST:
        mock_model = MagicMock()
        mock_model.encode.side_effect = [ctx_vec, at_threshold_vec]
        MockST.return_value = mock_model
        flagged = _check_relevance(
            [{"question": "Some borderline question."}],
            ["Some context."],
            threshold=0.35,
        )
    assert flagged == []


def test_check_relevance_empty_questions_returns_empty_list():
    with patch(_ST_PATCH) as MockST:
        MockST.return_value.encode.return_value = np.array([1.0, 0.0])
        flagged = _check_relevance([], ["Any context."], threshold=0.35)
    assert flagged == []


# ---------------------------------------------------------------------------
# generate() — buffer / overfetch behaviour
# ---------------------------------------------------------------------------

def test_generate_returns_exactly_num_questions_when_buffer_covers_flagged():
    # num_questions=3 → request_count=5; 2 flagged → 3 relevant returned
    num_q = 3
    request_count = num_q + max(2, int(num_q * 0.5))  # 5
    questions = _make_questions(request_count)

    # Relevance: context vec + relevant vecs all identical, last 2 orthogonal (flagged)
    ctx_vec = np.array([1.0, 0.0, 0.0])
    high_vec = np.array([1.0, 0.0, 0.0])
    low_vec = np.array([0.0, 1.0, 0.0])
    encode_returns = [ctx_vec] + [high_vec] * (request_count - 2) + [low_vec, low_vec]

    with patch(_ST_PATCH) as MockST:
        mock_model = MagicMock()
        mock_model.encode.side_effect = encode_returns
        MockST.return_value = mock_model
        gen = QuestionGenerator(client=_mock_client(json.dumps(questions)))
        result = gen.generate(["context"], num_questions=num_q)

    assert len(result) == num_q


def test_generate_returns_fewer_when_not_enough_relevant_questions(caplog):
    # num_questions=3 → request_count=5; 4 flagged → only 1 relevant returned + warning logged
    import logging
    num_q = 3
    request_count = num_q + max(2, int(num_q * 0.5))  # 5
    questions = _make_questions(request_count)

    ctx_vec = np.array([1.0, 0.0, 0.0])
    high_vec = np.array([1.0, 0.0, 0.0])
    low_vec = np.array([0.0, 1.0, 0.0])
    encode_returns = [ctx_vec, high_vec] + [low_vec] * (request_count - 1)

    with patch(_ST_PATCH) as MockST:
        mock_model = MagicMock()
        mock_model.encode.side_effect = encode_returns
        MockST.return_value = mock_model
        gen = QuestionGenerator(client=_mock_client(json.dumps(questions)))
        with caplog.at_level(logging.WARNING, logger="quiz.questions"):
            result = gen.generate(["context"], num_questions=num_q)

    assert len(result) < num_q
    assert any("relevant" in rec.message for rec in caplog.records)
