import json
import pytest
from unittest.mock import patch, MagicMock
from question_generator import build_query_for_difficulty, generate_questions


# --- build_query_for_difficulty ---

def test_build_query_easy_returns_nonempty_string():
    result = build_query_for_difficulty("Easy")
    assert isinstance(result, str) and len(result) > 0


def test_build_query_normal_returns_nonempty_string():
    result = build_query_for_difficulty("Normal")
    assert isinstance(result, str) and len(result) > 0


def test_build_query_hard_returns_nonempty_string():
    result = build_query_for_difficulty("Hard")
    assert isinstance(result, str) and len(result) > 0


def test_build_query_all_difficulties_are_distinct():
    results = {build_query_for_difficulty(d) for d in ["Easy", "Normal", "Hard"]}
    assert len(results) == 3


def test_build_query_unknown_difficulty_falls_back_to_normal():
    assert build_query_for_difficulty("Unknown") == build_query_for_difficulty("Normal")


def test_build_query_easy_mentions_basic_concepts():
    result = build_query_for_difficulty("Easy").lower()
    assert "basic" in result or "fundamental" in result


def test_build_query_hard_mentions_nuanced_concepts():
    result = build_query_for_difficulty("Hard").lower()
    assert "detailed" in result or "nuanced" in result or "mechanism" in result


# --- generate_questions helpers ---

def _make_questions(n=2):
    return [
        {
            "question": f"What is concept {i}?",
            "choices": [f"A. Option A{i}", f"B. Option B{i}", f"C. Option C{i}", f"D. Option D{i}"],
            "answer": "A",
        }
        for i in range(n)
    ]


def _mock_anthropic(raw_text):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=raw_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_msg
    return mock_client


# --- generate_questions ---

def test_generate_questions_returns_list():
    questions = _make_questions(3)
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic(json.dumps(questions))):
        result = generate_questions(["context chunk"], num_questions=3)
    assert isinstance(result, list)
    assert len(result) == 3


def test_generate_questions_each_item_has_required_keys():
    questions = _make_questions(2)
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic(json.dumps(questions))):
        result = generate_questions(["context"], num_questions=2)
    for q in result:
        assert "question" in q
        assert "choices" in q
        assert "answer" in q


def test_generate_questions_strips_json_code_fence():
    questions = _make_questions(1)
    raw = "```json\n" + json.dumps(questions) + "\n```"
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic(raw)):
        result = generate_questions(["context"], num_questions=1)
    assert len(result) == 1


def test_generate_questions_strips_plain_code_fence():
    questions = _make_questions(1)
    raw = "```\n" + json.dumps(questions) + "\n```"
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic(raw)):
        result = generate_questions(["context"], num_questions=1)
    assert len(result) == 1


def test_generate_questions_invalid_json_raises_value_error():
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic("not valid json")):
        with pytest.raises(ValueError):
            generate_questions(["context"], num_questions=3)


def test_generate_questions_empty_array_raises_value_error():
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic("[]")):
        with pytest.raises(ValueError):
            generate_questions(["context"], num_questions=3)


def test_generate_questions_non_list_response_raises_value_error():
    with patch("question_generator.anthropic.Anthropic", return_value=_mock_anthropic('{"key": "value"}')):
        with pytest.raises(ValueError):
            generate_questions(["context"], num_questions=3)


def test_generate_questions_multiple_chunks_joined_in_prompt():
    questions = _make_questions(1)
    mock_client = _mock_anthropic(json.dumps(questions))
    with patch("question_generator.anthropic.Anthropic", return_value=mock_client):
        generate_questions(["chunk one", "chunk two", "chunk three"], num_questions=1)
    prompt = mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "---" in prompt


def test_generate_questions_passes_correct_model():
    questions = _make_questions(1)
    mock_client = _mock_anthropic(json.dumps(questions))
    with patch("question_generator.anthropic.Anthropic", return_value=mock_client):
        generate_questions(["context"], num_questions=1)
    call_kwargs = mock_client.messages.create.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4-6"
