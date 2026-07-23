"""
Command line demo for the agentic workflow in src/agent.py.

Requires GEMINI_API_KEY to be set (see .env.example). Run with:
    python -m src.agent_main
"""
from src.agent import recommend_from_text
from src.recommender import load_songs

REQUESTS = [
    "I want something chill for studying, not too sad.",
    "Give me high energy pop to work out to.",
    "Deep, intense rock, but nothing acoustic.",
]


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs from data/songs.csv")

    for text in REQUESTS:
        print(f"\n=== Request: \"{text}\" ===")

        recommendations, trace = recommend_from_text(text, songs, k=5)

        print("Agent trace:")
        for line in trace:
            print(f"  - {line}")

        print("\nTop recommendations:\n")
        for song, score, explanation in recommendations:
            print(f"{song['title']} - Score: {score:.2f}")
            print(f"Because: {explanation}")
            print()


if __name__ == "__main__":
    main()
