import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    numeric_fields = {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            song = {}
            for key, value in row.items():
                key = key.strip()
                value = value.strip() if isinstance(value, str) else value
                if key == "id":
                    song[key] = int(value)
                elif key in numeric_fields:
                    song[key] = float(value)
                else:
                    song[key] = value
            songs.append(song)
    return songs

# Weights for score_song. w1 (energy) and w2 (acoustic) are largest because
# those features have the most spread across the catalog and map most
# directly to explicit user intent (target_energy, likes_acoustic).
W_ENERGY = 0.4
W_ACOUSTIC = 0.3
W_GENRE = 0.2
W_MOOD = 0.1

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    score = w1*(1 - |energy_diff|) + w2*acoustic_match + w3*genre_bonus + w4*mood_bonus

    Args:
        user_prefs: User taste preferences. Accepts either the simple keys
            used in src/main.py (genre, mood, energy) or the UserProfile-style
            keys (favorite_genre, favorite_mood, target_energy, likes_acoustic).
        song: A song dict as produced by load_songs(), with at least
            genre, mood, energy, and acousticness keys.

    Returns:
        A tuple of (score, reasons) where score is a float in roughly [0, 1]
        and reasons is a list of plain-language strings explaining the score.
    """
    target_energy = user_prefs.get("energy", user_prefs.get("target_energy", 0.5))
    favorite_genre = user_prefs.get("genre", user_prefs.get("favorite_genre"))
    favorite_mood = user_prefs.get("mood", user_prefs.get("favorite_mood"))
    likes_acoustic = user_prefs.get("likes_acoustic", False)

    energy_diff = abs(song["energy"] - target_energy)
    energy_score = 1 - energy_diff

    acoustic_match = song["acousticness"] if likes_acoustic else 1 - song["acousticness"]

    genre_bonus = 1.0 if song["genre"] == favorite_genre else 0.0
    mood_bonus = 1.0 if song["mood"] == favorite_mood else 0.0

    score = (
        W_ENERGY * energy_score
        + W_ACOUSTIC * acoustic_match
        + W_GENRE * genre_bonus
        + W_MOOD * mood_bonus
    )

    reasons = []
    if genre_bonus:
        reasons.append(f"matches your favorite genre ({favorite_genre})")
    if mood_bonus:
        reasons.append(f"matches your favorite mood ({favorite_mood})")
    reasons.append(f"energy {song['energy']:.2f} is {energy_diff:.2f} away from your target {target_energy:.2f}")
    reasons.append(
        f"{'acoustic' if likes_acoustic else 'non-acoustic'} preference "
        f"{'matches' if acoustic_match >= 0.5 else 'does not match'} this song's acousticness ({song['acousticness']:.2f})"
    )

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py

    Scores every song against user_prefs using score_song(), then returns
    the top k songs sorted by score in descending order.

    Args:
        user_prefs: User taste preferences, see score_song() for accepted keys.
        songs: The full song catalog to rank, as produced by load_songs().
        k: The number of top recommendations to return.

    Returns:
        A list of up to k (song, score, explanation) tuples, sorted by score
        descending, where explanation is score_song()'s reasons joined into
        a single string.
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons)
        scored.append((song, score, explanation))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]
