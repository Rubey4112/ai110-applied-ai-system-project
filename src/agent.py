"""
Agentic workflow that wraps the existing rule-based recommender.

Turns a free-text taste description into the recommender's structured
input (plan), runs the existing recommend_songs() unchanged (act), then
asks Gemini to judge whether the results actually satisfy the request
(check) and retries with an adjustment if not (revise).

See diagrams/plan.md for the full design.
"""
import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from src.recommender import recommend_songs

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return json.loads(text)


def _call_gemini_json(prompt: str) -> dict:
    """
    Isolated as its own function so tests can monkeypatch this single
    call site instead of hitting the network.
    """
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    response = _get_client().models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return _extract_json(response.text)


PARSE_INTENT_PROMPT = """You convert a listener's free-text music request into a structured taste profile.

Request: "{text}"

Reply with ONLY a JSON object (no markdown, no commentary) with exactly these keys:
- "genre": string or null - the single favorite genre if stated, else null
- "mood": string or null - the single favorite mood if stated, else null
- "energy": number between 0.0 and 1.0 - your best estimate of the target energy level (0 = very calm, 1 = very high energy); default to 0.5 if there is no signal
- "likes_acoustic": boolean - true if the request implies a preference for acoustic/unplugged sound, false otherwise
- "intent_notes": object with:
  - "exclude_moods": array of mood strings the request explicitly rules out (e.g. "not too sad" -> ["sad"]). Empty array if none.
  - "exclude_genres": array of genre strings the request explicitly rules out. Empty array if none.
  - "summary": one sentence paraphrasing the request in your own words, for a human to sanity-check later.
"""

CHECK_SATISFACTION_PROMPT = """A listener asked for music with this request:

Request: "{text}"

The system parsed that request into these preferences: {prefs}

It then recommended these songs:
{recommendations_block}

Judge whether these recommendations actually satisfy the request, including anything the
request ruled out (e.g. an excluded mood or genre) even if it is not one of the listed
preference keys.

Reply with ONLY a JSON object (no markdown, no commentary) with exactly these keys:
- "satisfied": boolean
- "violated_constraints": array of short strings describing what's wrong, empty if satisfied
- "suggested_adjustment": object with optional keys "exclude_moods" (array of strings),
  "exclude_genres" (array of strings), and "energy_delta" (number between -0.5 and 0.5 to
  nudge the target energy). Include only the keys that would help; empty object if satisfied.
"""


def parse_intent(text: str) -> dict:
    return _call_gemini_json(PARSE_INTENT_PROMPT.format(text=text))


def check_satisfaction(text: str, prefs: dict, recommendations: list) -> dict:
    lines = [
        f"- {song['title']} (genre={song['genre']}, mood={song['mood']}, "
        f"energy={song['energy']:.2f}) score={score:.2f} - {explanation}"
        for song, score, explanation in recommendations
    ]
    prompt = CHECK_SATISFACTION_PROMPT.format(
        text=text,
        prefs=json.dumps(prefs),
        recommendations_block="\n".join(lines),
    )
    return _call_gemini_json(prompt)


def apply_adjustment(songs: list, excluded_moods: set, excluded_genres: set) -> list:
    """
    Filters from the full original catalog, not the previously-filtered
    list, so exclusions accumulate across retries without compounding
    on top of whatever the last attempt happened to return.
    """
    return [
        s
        for s in songs
        if s["mood"] not in excluded_moods and s["genre"] not in excluded_genres
    ]


def recommend_from_text(text: str, songs: list, k: int = 5, max_retries: int = 2):
    """
    Plan -> act -> check -> revise loop around the existing recommend_songs().

    Returns (recommendations, trace) where trace is a list of strings
    describing what the agent did at each attempt.
    """
    parsed = parse_intent(text)
    intent_notes = parsed.get("intent_notes") or {}

    prefs = {
        "genre": parsed.get("genre"),
        "mood": parsed.get("mood"),
        "energy": parsed.get("energy", 0.5),
        "likes_acoustic": parsed.get("likes_acoustic", False),
    }
    excluded_moods = set(intent_notes.get("exclude_moods") or [])
    excluded_genres = set(intent_notes.get("exclude_genres") or [])

    trace = [f"Parsed intent: {intent_notes.get('summary', text)}"]

    attempt = 0
    while True:
        attempt += 1
        candidate_songs = apply_adjustment(songs, excluded_moods, excluded_genres)
        recommendations = recommend_songs(prefs, candidate_songs, k=k)
        verdict = check_satisfaction(text, prefs, recommendations)
        violations = "; ".join(verdict.get("violated_constraints", []))

        if verdict.get("satisfied"):
            trace.append(f"Attempt {attempt}: satisfied")
            return recommendations, trace

        if attempt > max_retries:
            trace.append(
                f"Attempt {attempt}: still unsatisfied after {max_retries} retries "
                f"({violations or 'no reason given'}); returning best effort"
            )
            return recommendations, trace

        suggestion = verdict.get("suggested_adjustment") or {}
        trace.append(f"Attempt {attempt}: unsatisfied ({violations}); adjusting with {suggestion}")

        excluded_moods |= set(suggestion.get("exclude_moods") or [])
        excluded_genres |= set(suggestion.get("exclude_genres") or [])
        energy_delta = suggestion.get("energy_delta")
        if energy_delta:
            prefs["energy"] = max(0.0, min(1.0, prefs.get("energy", 0.5) + energy_delta))
