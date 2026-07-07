# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**TuneMatch 1.0**

---

## 2. Intended Use  

TuneMatch ranks a small, fixed song catalog against a single user's stated taste profile and returns the top-k best-matching songs with a plain-language explanation for each. It assumes the user can explicitly state their preferences up front — a favorite genre, a favorite mood, a target energy level, and whether they lean acoustic or non-acoustic — rather than inferring taste from listening history. There's no login, no population of users, and no behavioral data; it's a classroom exploration of how a content-based scoring rule turns stated preferences into a ranked list, not a system built for real listeners.

---

## 3. How the Model Works  

Every song carries a handful of tags: a genre, a mood, an energy level from 0 to 1, a tempo, and a few extra attributes (valence, danceability, acousticness). A user describes their taste the same way — a favorite genre, a favorite mood, a target energy, and whether they like acoustic music.

To score a song, the model checks four things and blends them into one number:

- **How close the song's energy is to the user's target energy** — the closer, the better. This carries the most weight (40%).
- **Whether the song's acousticness matches the user's stated acoustic preference** — nearly as important (30%).
- **Whether the song's genre exactly matches the user's favorite genre** — a flat bonus (20%).
- **Whether the song's mood exactly matches the user's favorite mood** — a smaller flat bonus (10%).

Those four pieces are added together into a single score, every song in the catalog gets one, and the app sorts the list from highest to lowest and hands back the top 5 along with a sentence explaining why each song scored the way it did.

The starter code shipped with these functions as empty TODOs (the class-based `Recommender.recommend()` just returned the first k songs unsorted, and `explain_recommendation()` returned a placeholder string). I implemented the actual `score_song`/`recommend_songs` scoring and ranking logic, the CSV loader, and — as an experiment — tried doubling the energy weight and halving the genre weight to see how that shifts which songs win (see the README's Experiments section).

---

## 4. Data  

The catalog is 20 hand-authored songs in `data/songs.csv`, each with an id, title, artist, genre, mood, energy, tempo (bpm), valence, danceability, and acousticness. It spans 17 different genres (pop, lofi, rock, ambient, jazz, synthwave, indie pop, classical, hip hop, country, reggae, metal, folk, edm, blues, latin, punk), but the distribution is lopsided — lofi has 3 songs, pop has 2, and every other genre has exactly 1. Moods are almost all unique single-word labels (happy, chill, intense, relaxed, moody, focused, wistful, proud, longing, playful, angry, hopeful, elated, sad, sensual, defiant), so mood-matching is really "does this one song happen to share your exact word."

I didn't add or remove any songs — this is the starter catalog as given. Because it's this small and evenly-labeled-but-unevenly-populated, a lot of musical taste is missing: there's no representation of intensity within a genre (only one metal song, one classical song), no vocal/instrumental distinction, no lyrical content or language, and no notion of subgenre or influence between genres that are musically close (indie pop vs. pop, synthwave vs. edm).

---

## 5. Strengths  

The model works best when a user's stated preferences line up tightly with a song that exists in the catalog — for example, a "Deep Intense Rock" profile (genre=rock, mood=intense, energy=0.9) scores "Storm Runner" a 0.97, because it hits genre, mood, and energy all at once. In general, the energy-proximity and acoustic-direction pieces behave predictably and are easy to sanity-check by hand.

It also holds up well under stress: profiles with missing preferences, an out-of-range energy value, or a genre that doesn't exist in the catalog all still return a plausible top-5 without crashing, just leaning more heavily on whichever signals are actually available (see the stress test in the README).

Its biggest strength relative to a black-box recommender is interpretability — every recommendation comes with a plain-English explanation of exactly which preferences it matched and by how much, so it's easy to audit whether a score makes sense.

---

## 6. Limitations and Bias 

(Full detail in the README's [Limitations and Risks](README.md#limitations-and-risks) section.)

- It doesn't consider tempo, valence, or danceability at all, even though they're loaded from the CSV — so a mislabeled or contradictory mood tag (e.g., "sad" with high valence) can't be caught.
- Genre and mood matching is exact-string, not semantic — "pop" gets no credit for "indie pop," so once a favorite genre is set, the system only ever reinforces that one label and never surfaces musically adjacent songs.
- Genres are unevenly represented in the catalog: someone whose favorite genre is metal or folk (1 song each) gets far less genre-matched variety than someone who likes lofi (3 songs) — the catalog itself, not just the algorithm, favors certain tastes.
- `likes_acoustic` is a binary switch rather than a target, so users with a moderate acoustic preference get pushed to one extreme instead of matched nuance.
- The four weights (0.4/0.3/0.2/0.1) were hand-picked based on which features "seemed" to have the most spread, not validated against any real listener feedback — they encode one designer's assumption about what matters, applied identically to everyone.
- Missing profile fields silently default to values (energy → 0.5, likes_acoustic → False) that quietly favor mid-tempo, non-acoustic songs rather than treating incomplete profiles neutrally.
- There's no diversity-aware re-ranking, so an artist with multiple catalog entries can occupy several of the top-5 slots at once.

---

## 7. Evaluation  

I tested 8 profiles total: 3 "clean" ones designed to align well with the catalog (High-Energy Pop, Chill Lofi, Deep Intense Rock) and 5 adversarial/edge-case ones designed to probe the scoring logic (Conflicting Energy/Mood, Out-of-Range Energy, Unknown Genre, Empty Preferences, and an Acoustic-Loving Metalhead with self-contradictory preferences). For each, I checked whether the app crashed, whether the top pick matched intuition, and whether the explanation text actually matched the score.

Nothing crashed, including on an energy value outside the expected [0, 1] range and a genre that doesn't exist in the catalog — the model just degrades gracefully by leaning on whatever signals remain valid.

The most surprising result came from the weight-shift experiment (doubling energy's weight, halving genre's): for the clean profiles, the top recommendation didn't change at all — only 4th/5th place shuffled. But for the self-contradictory Acoustic-Loving Metalhead profile, the ranking flipped entirely, from favoring acoustic songs with poor energy match to favoring high-energy songs with poor acoustic match. That showed me the weights aren't just a "quality dial" — they're actually deciding which of two conflicting user signals to believe, which isn't something I expected going in.

---

## 8. Future Work  

- Replace exact-string genre matching with a similarity measure (a hand-built adjacency table, or embeddings) so related genres get partial credit instead of zero.
- Add diversity-aware re-ranking (e.g., cap songs per artist, or an MMR-style penalty for near-duplicate picks) so the top-5 isn't dominated by one artist or one genre.
- Turn `likes_acoustic` into a continuous target (like energy) instead of a binary switch, so moderate preferences are represented.
- Validate/clamp input ranges (e.g., reject or clamp energy values outside [0, 1]) instead of silently producing a distorted score.
- Put the unused features (tempo, valence, danceability) to work, either as extra scoring terms or as a way to catch contradictory mood labels.
- Learn or A/B-test the weights against real listener feedback instead of hand-picking them from intuition.
- Add a lightweight feedback loop (skip/like signals) so the system can adjust future scores instead of recommending the same slice of the catalog forever.
- Grow the catalog so niche genres aren't starved of matches relative to well-represented ones.

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
