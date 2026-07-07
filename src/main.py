"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs


USER_PROFILES = [
    # Distinct, internally-consistent taste profiles.
    ("High-Energy Pop", {"genre": "pop", "mood": "happy", "energy": 0.85}),
    ("Chill Lofi", {"genre": "lofi", "mood": "chill", "energy": 0.35}),
    ("Deep Intense Rock", {"genre": "rock", "mood": "intense", "energy": 0.9}),

    # Adversarial / edge-case profiles meant to stress the scoring logic.
    ("Conflicting Energy/Mood", {"genre": "rock", "mood": "sad", "energy": 0.9}),
    ("Out-of-Range Energy", {"genre": "pop", "mood": "happy", "energy": 1.5}),
    ("Unknown Genre", {"genre": "dubstep", "mood": "happy", "energy": 0.7}),
    ("Empty Preferences", {}),
    (
        "Acoustic-Loving Metalhead",
        {
            "favorite_genre": "metal",
            "favorite_mood": "angry",
            "target_energy": 0.95,
            "likes_acoustic": True,
        },
    ),
]


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs from data/songs.csv")

    for name, user_prefs in USER_PROFILES:
        print(f"\n=== Profile: {name} ({user_prefs}) ===")

        recommendations = recommend_songs(user_prefs, songs, k=5)

        print("Top recommendations:\n")
        for rec in recommendations:
            # You decide the structure of each returned item.
            # A common pattern is: (song, score, explanation)
            song, score, explanation = rec
            print(f"{song['title']} - Score: {score:.2f}")
            print(f"Because: {explanation}")
            print()


if __name__ == "__main__":
    main()
