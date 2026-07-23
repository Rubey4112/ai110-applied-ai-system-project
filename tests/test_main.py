from src import main


def fake_recommend_from_text(text, songs, k=5):
    return (
        [({"title": "Song One", "artist": "x", "genre": "pop", "mood": "happy", "energy": 0.8, "acousticness": 0.1}, 0.9, "matches your taste")],
        ["Parsed intent: fake", "Attempt 1: satisfied"],
    )


def test_send_message_appends_transcript_and_titles_session(monkeypatch):
    monkeypatch.setattr(main, "recommend_from_text", fake_recommend_from_text)

    session_id, session = main._new_session()
    sessions = {session_id: session}
    order = [session_id]

    box, history, sessions, choices_update, panel = main.send_message(
        "chill lofi please", session_id, sessions, order
    )

    assert box == ""
    # user message + 2 trace steps (shown as tool-use bubbles) + final reply
    assert len(history) == 4
    assert history[0] == {"role": "user", "content": "chill lofi please"}
    assert history[1]["metadata"]["title"] == "🔍 Parsed intent"
    assert history[2]["metadata"]["title"] == "✅ Self-check passed"
    assert history[3]["role"] == "assistant"
    assert "metadata" not in history[3]
    assert "Song One" in history[3]["content"]
    assert sessions[session_id]["title"] == "chill lofi please"
    assert "chill lofi please" in panel
    assert "Song One" in panel
    assert sessions[session_id]["request_history"] == [
        {
            "request": "chill lofi please",
            "recommendations": [
                (
                    {"title": "Song One", "artist": "x", "genre": "pop", "mood": "happy", "energy": 0.8, "acousticness": 0.1},
                    0.9,
                    "matches your taste",
                )
            ],
        }
    ]


def test_panel_content_accumulates_history_most_recent_first():
    _, session = main._new_session()

    song_a = {"title": "Song A", "artist": "x", "genre": "pop", "mood": "happy", "energy": 0.8, "acousticness": 0.1}
    song_b = {"title": "Song B", "artist": "y", "genre": "rock", "mood": "intense", "energy": 0.9, "acousticness": 0.0}

    session["request_history"].append({"request": "first request", "recommendations": [(song_a, 0.9, "why a")]})
    session["request_history"].append({"request": "second request", "recommendations": [(song_b, 0.8, "why b")]})

    panel = main._panel_content(session)

    assert panel.index("second request") < panel.index("first request")
    assert "Song A" in panel
    assert "Song B" in panel


def test_panel_content_before_any_request():
    _, session = main._new_session()
    assert main._panel_content(session) == main.NO_REQUEST_TEXT


def test_trace_title_maps_each_step_kind():
    assert main._trace_title("Parsed intent: chill lofi") == "🔍 Parsed intent"
    assert main._trace_title("Attempt 1: satisfied") == "✅ Self-check passed"
    assert main._trace_title("Attempt 1: unsatisfied (bad mood); adjusting with {}") == "🔁 Retry — adjusting query"
    assert (
        main._trace_title("Attempt 2: still unsatisfied after 1 retries (bad mood); returning best effort")
        == "⚠️ Gave up after max retries"
    )


def test_trace_message_carries_done_status():
    msg = main._trace_message("Attempt 1: satisfied")
    assert msg["role"] == "assistant"
    assert msg["content"] == "Attempt 1: satisfied"
    assert msg["metadata"] == {"title": "✅ Self-check passed", "status": "done"}


def test_send_message_ignores_blank_input(monkeypatch):
    called = {"n": 0}

    def should_not_be_called(*args, **kwargs):
        called["n"] += 1
        return fake_recommend_from_text(*args, **kwargs)

    monkeypatch.setattr(main, "recommend_from_text", should_not_be_called)

    session_id, session = main._new_session()
    sessions = {session_id: session}
    order = [session_id]

    box, history, sessions, _, panel = main.send_message("   ", session_id, sessions, order)

    assert called["n"] == 0
    assert history == []
    assert panel == main.NO_REQUEST_TEXT


def test_new_chat_and_switch_session_round_trip(monkeypatch):
    monkeypatch.setattr(main, "recommend_from_text", fake_recommend_from_text)

    first_id, first_session = main._new_session()
    sessions = {first_id: first_session}
    order = [first_id]

    _, history, sessions, _, panel = main.send_message("hype workout mix", first_id, sessions, order)
    assert sessions[first_id]["messages"] == history

    second_id, sessions, order, chatbot_reset, choices_update, new_panel = main.new_chat(sessions, order)

    assert second_id != first_id
    assert chatbot_reset == []
    assert order == [second_id, first_id]
    assert new_panel == main.NO_REQUEST_TEXT

    restored_id, restored_history, restored_panel = main.switch_session(first_id, sessions)
    assert restored_id == first_id
    assert restored_history == history
    assert restored_panel == panel
