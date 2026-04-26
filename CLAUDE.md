# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the Streamlit app:**
```bash
python -m streamlit run app.py
```

**Run all tests:**
```bash
pytest
```

**Run a single test:**
```bash
pytest tests/test_game_logic.py::test_winning_guess
```

## Architecture

This is a Streamlit number-guessing game split into two modules:

- **[app.py](app.py)** — UI layer. Manages `st.session_state` for all persistent game data (`secret`, `attempts`, `score`, `status`, `history`). Handles difficulty selection, user input, and rendering.
- **[logic_utils.py](logic_utils.py)** — Pure game logic with four functions:
  - `get_range_for_difficulty(difficulty)` → `(low, high)` tuple
  - `parse_guess(raw)` → `(ok, value, error)` tuple; validates and converts user input
  - `check_guess(guess, secret)` → `(outcome, message)` where outcome is `"Win"`, `"Too High"`, or `"Too Low"`
  - `update_score(current_score, outcome, attempt_number)` → updated score

**Data flow:** `app.py` calls `parse_guess` → `check_guess` → `update_score` in sequence on each submission, then updates `st.session_state` and Streamlit rerenders.

**Tests** live in [tests/test_game_logic.py](tests/test_game_logic.py). The [tests/conftest.py](tests/conftest.py) adds the project root to `sys.path` so `logic_utils` can be imported.

## Key Behaviors

- **Session state is the source of truth** — the secret number and all game state persist only in `st.session_state`. Do not use local variables for game data in `app.py`.
- **Difficulty ranges:** Easy = 1–20 (6 attempts), Normal = 1–100 (8 attempts), Hard = 1–50 (5 attempts). Note that Hard intentionally has a smaller range than Normal — this is a known quirk documented in [PROBLEMS.md](PROBLEMS.md).
- **Scoring:** Win = `max(10, 100 - 10 * (attempt + 1))`; wrong guess = −5 points.
- Docstrings follow Google style.
