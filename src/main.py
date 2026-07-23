"""
Gradio chat UI for the agentic music recommender (see src/agent.py).

Left panel: chat session list (like a sidebar) with a "+ New chat" button.
Main panel: a conversational chat box. Each user message is a free-text
music request routed through src.agent.recommend_from_text(), which parses
it, runs the existing recommend_songs(), checks whether the results satisfy
the request, and retries with an adjustment if not.

Requires GEMINI_API_KEY to be set (see .env.example). Run with:
    python -m src.main
or directly:
    python src/main.py
"""
import os
import sys
import uuid

import gradio as gr

# Allow running this file directly (python src/main.py), where Python only
# puts src/ itself on sys.path, not the project root that "src.agent" needs
# to resolve. A no-op when run as python -m src.main.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.agent import recommend_from_text
from src.recommender import load_songs

SONGS = load_songs(os.path.join(_PROJECT_ROOT, "data", "songs.csv"))
NEW_CHAT_TITLE = "New chat"


def _new_session():
    session_id = str(uuid.uuid4())
    return session_id, {"title": NEW_CHAT_TITLE, "messages": []}


def _session_choices(sessions, order):
    return [(sessions[sid]["title"], sid) for sid in order]


def _format_reply(recommendations):
    lines = [
        f"**{song['title']}** — score {score:.2f}\n> {explanation}"
        for song, score, explanation in recommendations
    ]
    return "Here's what I found:\n\n" + "\n\n".join(lines)


def _trace_title(step: str) -> str:
    if step.startswith("Parsed intent"):
        return "🔍 Parsed intent"
    if "still unsatisfied" in step:
        return "⚠️ Gave up after max retries"
    if ": satisfied" in step:
        return "✅ Self-check passed"
    if "unsatisfied" in step:
        return "🔁 Retry — adjusting query"
    return "🛠️ Agent step"


def _trace_message(step: str) -> dict:
    """
    Renders one agent.recommend_from_text() trace entry as a Gradio "tool
    usage" bubble: a collapsible message distinct from the final reply,
    via the metadata field Chatbot recognizes (title/status).
    """
    return {
        "role": "assistant",
        "content": step,
        "metadata": {"title": _trace_title(step), "status": "done"},
    }


def send_message(message, current_id, sessions, order):
    if not message.strip():
        return "", sessions[current_id]["messages"], sessions, gr.update()

    recommendations, trace = recommend_from_text(message, SONGS, k=5)

    sessions[current_id]["messages"].append({"role": "user", "content": message})
    sessions[current_id]["messages"].extend(_trace_message(step) for step in trace)
    sessions[current_id]["messages"].append(
        {"role": "assistant", "content": _format_reply(recommendations)}
    )
    if sessions[current_id]["title"] == NEW_CHAT_TITLE:
        title = message.strip()[:40]
        sessions[current_id]["title"] = title + ("…" if len(message.strip()) > 40 else "")

    return (
        "",
        sessions[current_id]["messages"],
        sessions,
        gr.update(choices=_session_choices(sessions, order), value=current_id),
    )


def new_chat(sessions, order):
    session_id, session = _new_session()
    sessions[session_id] = session
    order = [session_id] + order
    return (
        session_id,
        sessions,
        order,
        [],
        gr.update(choices=_session_choices(sessions, order), value=session_id),
    )


def switch_session(session_id, sessions):
    return session_id, sessions[session_id]["messages"]


def build_app() -> gr.Blocks:
    first_id, first_session = _new_session()
    initial_sessions = {first_id: first_session}
    initial_order = [first_id]

    with gr.Blocks(title="Music Recommender Chat") as demo:
        sessions_state = gr.State(initial_sessions)
        order_state = gr.State(initial_order)
        current_session = gr.State(first_id)

        with gr.Row():
            with gr.Column(scale=1, min_width=220):
                gr.Markdown("### Chat sessions")
                new_chat_btn = gr.Button("+ New chat")
                session_list = gr.Radio(
                    choices=_session_choices(initial_sessions, initial_order),
                    value=first_id,
                    show_label=False,
                )

            with gr.Column(scale=4):
                chatbot = gr.Chatbot(label="Music Recommender", height=520)
                msg = gr.Textbox(
                    placeholder=(
                        "Describe what you want to listen to "
                        "(e.g. 'chill lofi for studying, not too sad')"
                    ),
                    show_label=False,
                )

        msg.submit(
            send_message,
            inputs=[msg, current_session, sessions_state, order_state],
            outputs=[msg, chatbot, sessions_state, session_list],
        )
        new_chat_btn.click(
            new_chat,
            inputs=[sessions_state, order_state],
            outputs=[current_session, sessions_state, order_state, chatbot, session_list],
        )
        session_list.change(
            switch_session,
            inputs=[session_list, sessions_state],
            outputs=[current_session, chatbot],
        )

    return demo


def main() -> None:
    demo = build_app()
    demo.launch()


if __name__ == "__main__":
    main()
