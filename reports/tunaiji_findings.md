# Tunaiji (reciter 161) — mistiming findings
_Generated 2026-05-19T23:15:29_

## Whole-verse shifts (Whisper-verify, sim ≥ 0.70)

| surah | name | n_shifts | verses | offsets |
|------:|:-----|---------:|--------|--------:|
| 2 | Al-Baqarah | 1 | 150 | -1 |
| 5 | Al-Maidah | 1 | 44 | +3 |
| 10 | Yunus | 29 | 28, 31-32, 43, 46-47, 51-52, 57, 64, 69, 72, 74-77, 80-81, 83-84, 88, 95, 98-99, 101-103, 107-108 | +1, +2 |
| 13 | Ar-Rad | 4 | 2-5 | -1 |
| 14 | Ibrahim | 2 | 5, 36 | +1 |
| 34 | Saba | 2 | 48-49 | +1 |

## Boundary drift (hybrid fix, ≥ 150 ms)

| surah | name | n_boundaries | verses (left of boundary) | max |Δ| (ms) | direction |
|------:|:-----|-------------:|---------------------------|-------------:|:----------|
| 1 | Al-Fatihah | 2 | 4, 6 | 430 | LATE (api flips after voice) |
| 2 | Al-Baqarah | 1 | 242 | 394 | LATE (api flips after voice) |
| 4 | An-Nisa | 1 | 58 | 339 | EARLY (api flips before voice) |
| 10 | Yunus | 42 | 1-11, 29, 34-35, 38-42, 57, 61-65, 67, 69, 72, 76, 79, 82-83, 87-88, 90-92, 94-95, 98, 101, 106 | 2365 | mixed |
| 13 | Ar-Rad | 24 | 13-33, 39, 41-42 | 2491 | mixed |
| 14 | Ibrahim | 23 | 2, 8-10, 14-16, 18, 20-21, 23, 25, 27-29, 34, 39-40, 42-43, 45, 48-49 | 2468 | mixed |
| 21 | Al-Anbiya | 1 | 62 | 196 | LATE (api flips after voice) |
| 25 | Al-Furqan | 1 | 10 | 150 | EARLY (api flips before voice) |
| 72 | Al-Jinn | 19 | 1-2, 4, 6, 9, 11-18, 20-25 | 2277 | mixed |

## Aggregate

- Surahs with confirmed whole-verse shift(s): **6**
- Total confirmed whole-verse shifts: **39**
- Surahs with boundary drift: **9**
- Total boundary drifts >= 150 ms: **114**
