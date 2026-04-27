import os
import streamlit as st

from document_parser import extract_text, chunk_text
from rag_engine import build_index, retrieve
from question_generator import generate_questions, build_query_for_difficulty
from quiz_logic import get_question_count_for_difficulty, parse_answer, check_answer, update_score

st.set_page_config(page_title="Class Quiz", page_icon="📚")
st.title("📚 Class Quiz")

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
num_questions = get_question_count_for_difficulty(difficulty)
st.sidebar.caption(f"Questions: {num_questions}")

api_key = st.sidebar.text_input(
    "Anthropic API Key",
    type="password",
    value=os.environ.get("ANTHROPIC_API_KEY", ""),
    help="Required for question generation",
)

# ── Session state ──────────────────────────────────────────────────────────────
_defaults = {
    "vector_index": None,
    "questions": [],
    "current_idx": 0,
    "score": 0,
    "status": "idle",       # idle | ready | playing | finished
    "history": [],
    "answer_submitted": False,
    "last_result": None,    # {"outcome": str, "message": str}
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def _reset_to(status: str):
    for k, v in _defaults.items():
        st.session_state[k] = v
    st.session_state.status = status


# ── IDLE: file upload ──────────────────────────────────────────────────────────
if st.session_state.status == "idle":
    st.info("Upload your class material (PDF, TXT, or DOCX) to get started.")
    uploaded_file = st.file_uploader("Upload file", type=["pdf", "txt", "docx"])

    if uploaded_file:
        with st.spinner("Reading and indexing document…"):
            text = extract_text(uploaded_file)
            chunks = chunk_text(text)
            st.session_state.vector_index = build_index(chunks)
            st.session_state.status = "ready"
        st.success(f"Indexed {len(chunks)} chunks. Ready to quiz!")
        st.rerun()

# ── READY: start quiz ──────────────────────────────────────────────────────────
elif st.session_state.status == "ready":
    st.success("Document indexed. Select a difficulty in the sidebar, then start.")

    if st.button("Start Quiz", type="primary"):
        if not api_key:
            st.error("Enter your Anthropic API key in the sidebar.")
            st.stop()

        os.environ["ANTHROPIC_API_KEY"] = api_key

        with st.spinner(f"Generating {num_questions} questions…"):
            query = build_query_for_difficulty(difficulty)
            chunks = retrieve(query, st.session_state.vector_index, top_k=10)
            st.session_state.questions = generate_questions(chunks, num_questions)
            st.session_state.current_idx = 0
            st.session_state.score = 0
            st.session_state.history = []
            st.session_state.answer_submitted = False
            st.session_state.last_result = None
            st.session_state.status = "playing"
        st.rerun()

    if st.button("Upload New Document"):
        _reset_to("idle")
        st.rerun()

# ── PLAYING: one question at a time ───────────────────────────────────────────
elif st.session_state.status == "playing":
    questions = st.session_state.questions
    idx = st.session_state.current_idx

    if idx >= len(questions):
        st.session_state.status = "finished"
        st.rerun()

    q = questions[idx]

    st.progress(idx / len(questions), text=f"Question {idx + 1} of {len(questions)}")
    st.caption(f"Score: {st.session_state.score}")
    st.divider()
    st.subheader(q["question"])

    if not st.session_state.answer_submitted:
        selected = st.radio("Choose your answer:", q["choices"], key=f"q_{idx}", index=None)

        if st.button("Submit Answer", type="primary"):
            ok, letter, err = parse_answer(selected)
            if not ok:
                st.error(err)
            else:
                outcome, message = check_answer(letter, q["answer"])
                st.session_state.score = update_score(st.session_state.score, outcome, idx + 1)
                st.session_state.history.append({
                    "question": q["question"],
                    "selected": letter,
                    "correct": q["answer"],
                    "outcome": outcome,
                })
                st.session_state.last_result = {"outcome": outcome, "message": message}
                st.session_state.answer_submitted = True
                st.rerun()

    else:
        result = st.session_state.last_result
        selected_letter = st.session_state.history[-1]["selected"]

        for choice in q["choices"]:
            letter = choice[0]
            if letter == q["answer"]:
                st.success(f"✅ {choice}")
            elif letter == selected_letter:
                st.error(f"❌ {choice}")
            else:
                st.write(choice)

        if result["outcome"] == "Correct":
            st.success(result["message"])
        else:
            st.error(result["message"])

        is_last = (idx + 1) >= len(questions)
        if st.button("Finish Quiz" if is_last else "Next Question →", type="primary"):
            st.session_state.current_idx += 1
            st.session_state.answer_submitted = False
            st.session_state.last_result = None
            st.rerun()

# ── FINISHED: results ──────────────────────────────────────────────────────────
elif st.session_state.status == "finished":
    st.balloons()
    history = st.session_state.history
    correct_count = sum(1 for h in history if h["outcome"] == "Correct")

    st.header("Quiz Complete!")
    col1, col2 = st.columns(2)
    col1.metric("Final Score", st.session_state.score)
    col2.metric("Correct Answers", f"{correct_count} / {len(history)}")

    st.divider()

    with st.expander("Review Answers"):
        for i, h in enumerate(history, 1):
            icon = "✅" if h["outcome"] == "Correct" else "❌"
            st.write(f"{icon} **Q{i}:** {h['question']}")
            st.caption(f"Your answer: **{h['selected']}** | Correct: **{h['correct']}**")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Play Again", type="primary"):
            st.session_state.status = "ready"
            st.rerun()
    with col_b:
        if st.button("Upload New Document"):
            _reset_to("idle")
            st.rerun()
