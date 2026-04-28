import logging
import os
import pathlib
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
    force=True,
)

from sentence_transformers import SentenceTransformer
from quiz import DocumentParser, RAGEngine, QuestionGenerator, QuizSession, LLMClient


@st.cache_resource
def _get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    return SentenceTransformer(model_name)

# Must run after the import — transformers resets its logger level during first import
logging.getLogger("transformers").setLevel(logging.ERROR)

st.set_page_config(page_title="Class Quiz", page_icon="📚")
st.title("📚 Class Quiz")

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.header("Settings")

provider = st.sidebar.selectbox("AI Provider", LLMClient.PROVIDERS, index=0)
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Normal", "Hard"], index=1)
num_questions = QuizSession(difficulty).question_count
st.sidebar.caption(f"Questions: {num_questions}")
dry_run = st.sidebar.checkbox("Dry Run (no real API calls)", value=False)
st.sidebar.metric("API Calls This Session", LLMClient.total_calls())


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


_SAMPLE_DIR = pathlib.Path(__file__).parent / "sample_materials"
_SAMPLE_FILES = sorted(_SAMPLE_DIR.glob("*.txt"))


def _load_text_and_index(text: str):
    parser = DocumentParser()
    chunks = parser.chunk(parser._clean(text))
    st.session_state.vector_index = RAGEngine(_model=_get_embedding_model()).build(chunks)
    st.session_state.status = "ready"
    return chunks


# ── IDLE: file upload ──────────────────────────────────────────────────────────
if st.session_state.status == "idle":
    st.info("Upload your class material (PDF, TXT, or DOCX) to get started.")
    uploaded_file = st.file_uploader("Upload file", type=["pdf", "txt", "docx"])

    if uploaded_file:
        with st.spinner("Reading and indexing document…"):
            parser = DocumentParser()
            text = parser.extract(uploaded_file)
            chunks = parser.chunk(text)
            st.session_state.vector_index = RAGEngine(_model=_get_embedding_model()).build(chunks)
            st.session_state.status = "ready"
        st.success(f"Indexed {len(chunks)} chunks. Ready to quiz!")
        st.rerun()

    if _SAMPLE_FILES:
        st.divider()
        st.subheader("Or try a sample")
        sample_names = [f.stem.replace("_", " ").title() for f in _SAMPLE_FILES]
        chosen = st.selectbox("Sample material", sample_names)
        if st.button("Load Sample", type="secondary"):
            sample_path = _SAMPLE_FILES[sample_names.index(chosen)]
            with st.spinner(f'Loading "{chosen}"…'):
                raw = sample_path.read_text(encoding="utf-8")
                chunks = _load_text_and_index(raw)
            st.success(f"Indexed {len(chunks)} chunks from sample. Ready to quiz!")
            st.rerun()

# ── READY: start quiz ──────────────────────────────────────────────────────────
elif st.session_state.status == "ready":
    st.success("Document indexed. Select a difficulty in the sidebar, then start.")

    if st.button("Start Quiz", type="primary"):
        _env_keys = {"claude": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}
        required_key = _env_keys[provider]
        if not dry_run and not os.environ.get(required_key):
            st.error(f"{required_key} not found. Add it to your .env file and restart the app.")
            st.stop()

        with st.spinner(f"Generating {num_questions} questions with {provider.title()}…"):
            query = QuestionGenerator.query_for_difficulty(difficulty)
            chunks = st.session_state.vector_index.retrieve(query, top_k=10)
            client = LLMClient(provider=provider, dry_run=dry_run)
            st.session_state.questions = QuestionGenerator(client=client).generate(chunks, num_questions)
            st.session_state.current_idx = 0
            st.session_state.score = 0
            st.session_state.history = []
            st.session_state.answer_submitted = False
            st.session_state.last_result = None
            st.session_state.status = "playing"
            for k in list(st.session_state.keys()):
                if isinstance(k, str) and k.startswith("radio_"):
                    del st.session_state[k]
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
    st.markdown(
        "<style>"
        # Scale down the question heading and improve line-height for readability
        ".stMarkdown h4{font-size:1.1rem;font-weight:600;line-height:1.7;margin-bottom:0.25rem}"
        # Let wide display-math blocks scroll horizontally rather than wrap mid-equation
        ".katex-display{overflow-x:auto;overflow-y:hidden;padding-bottom:2px}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(f"#### {q['question']}")

    if not st.session_state.answer_submitted:
        _sel_key = f"radio_{idx}"
        if _sel_key not in st.session_state:
            st.session_state[_sel_key] = None

        st.write("**Choose your answer:**")
        for choice in q["choices"]:
            opt_letter = choice[0]
            opt_text = choice[3:]  # strip "A. " prefix
            col_btn, col_text = st.columns([0.06, 0.94])
            with col_btn:
                btn_type = "primary" if st.session_state[_sel_key] == opt_letter else "secondary"
                if st.button(opt_letter, key=f"opt_{idx}_{opt_letter}", type=btn_type):
                    st.session_state[_sel_key] = opt_letter
                    st.rerun()
            with col_text:
                st.markdown(opt_text)

        selected = st.session_state[_sel_key]

        if st.button("Submit Answer", type="primary"):
            ok, letter, err = QuizSession.parse_answer(selected)
            if not ok:
                st.error(err)
            else:
                outcome, message = QuizSession.check_answer(letter, q["answer"])
                st.session_state.score = QuizSession.update_score(st.session_state.score, outcome, idx + 1)
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
