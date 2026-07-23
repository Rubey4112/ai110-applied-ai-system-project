from src import agent


def make_songs():
    return [
        {"title": "A", "artist": "x", "genre": "lofi", "mood": "sad", "energy": 0.3, "acousticness": 0.5},
        {"title": "B", "artist": "x", "genre": "lofi", "mood": "moody", "energy": 0.3, "acousticness": 0.5},
        {"title": "C", "artist": "x", "genre": "lofi", "mood": "chill", "energy": 0.3, "acousticness": 0.5},
    ]


def test_parse_intent_forwards_to_gemini_call(monkeypatch):
    seen_prompts = []

    def fake_call(prompt):
        seen_prompts.append(prompt)
        return {"genre": "lofi", "mood": "chill", "energy": 0.3, "likes_acoustic": False, "intent_notes": {}}

    monkeypatch.setattr(agent, "_call_gemini_json", fake_call)

    result = agent.parse_intent("chill lofi please")

    assert result["genre"] == "lofi"
    assert "chill lofi please" in seen_prompts[0]


def test_recommend_from_text_retries_until_satisfied(monkeypatch):
    songs = make_songs()
    calls = []

    responses = iter(
        [
            {
                "genre": "lofi",
                "mood": "chill",
                "energy": 0.3,
                "likes_acoustic": False,
                "intent_notes": {"exclude_moods": ["sad"], "exclude_genres": [], "summary": "chill lofi, not sad"},
            },
            {
                "satisfied": False,
                "violated_constraints": ["top result has mood moody, which reads as sad-adjacent"],
                "suggested_adjustment": {"exclude_moods": ["moody"]},
            },
            {"satisfied": True, "violated_constraints": [], "suggested_adjustment": {}},
        ]
    )

    def fake_call(prompt):
        calls.append(prompt)
        return next(responses)

    monkeypatch.setattr(agent, "_call_gemini_json", fake_call)

    recommendations, trace = agent.recommend_from_text("chill lofi, not too sad", songs, k=5, max_retries=2)

    assert len(calls) == 3
    titles = [song["title"] for song, _, _ in recommendations]
    assert titles == ["C"]
    assert "Parsed intent" in trace[0]
    assert "unsatisfied" in trace[1]
    assert trace[2] == "Attempt 2: satisfied"


def test_recommend_from_text_stops_at_max_retries(monkeypatch):
    songs = make_songs()
    call_count = {"n": 0}

    def fake_call(prompt):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"genre": "lofi", "mood": "chill", "energy": 0.3, "likes_acoustic": False, "intent_notes": {}}
        return {
            "satisfied": False,
            "violated_constraints": ["still not right"],
            "suggested_adjustment": {"exclude_moods": ["sad"]},
        }

    monkeypatch.setattr(agent, "_call_gemini_json", fake_call)

    recommendations, trace = agent.recommend_from_text("anything", songs, k=5, max_retries=1)

    # 1 parse call + 2 check calls (attempt 1 fails, attempt 2 fails and exhausts retries)
    assert call_count["n"] == 3
    assert len(recommendations) > 0
    assert "still unsatisfied" in trace[-1]
    assert "returning best effort" in trace[-1]
