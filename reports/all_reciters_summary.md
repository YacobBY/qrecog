# Quran.com per-reciter API timing audit — final summary

Pipeline: download audio + API → run Whisper (large-v3 / medium) on each
verse's claimed audio span → compare transcribed text (char-LCS after
diacritic stripping) to canonical `text_uthmani` for that verse and
±3 neighbours. **High confidence** = `char-similarity ≥ 0.70` against a
neighbour verse and ≥ 0.20 better than the claimed verse. This signal
is independent of the wav2vec2 forced-alignment pass, so it catches
cases where both API and our CTC pipeline got it wrong.

12 reciters scanned (every reciter currently exposed by
`api.quran.com/api/v4/resources/recitations` plus reciter 161 Tunaiji).
Reciter 8 (Minshawi mujawwad) skipped — its audio URL returns 404 on
quranicaudio.com.

## Per-reciter totals

| reciter | id | high-conf shifts | status |
|---------|---:|------------------:|--------|
| Abdur-Rahman as-Sudais | 3 | **157** | many bad surahs |
| Mishari Rashid al-`Afasy | 7 | **23** | Surah 37 cluster, Surah 82 |
| AbdulBaset AbdulSamad (alt, mujawwad) | 2 | **13** | Surah 2 cluster |
| Abu Bakr al-Shatri | 4 | **7** | Surah 10 + isolated |
| Hani ar-Rifai | 5 | **5** | Surah 16 only |
| Mohamed Siddiq al-Minshawi (murattal) | 9 | **3** | Surah 4 only |
| Mohamed al-Tablawi | 11 | **2** | Surah 4 only |
| **Khalifah Al Tunaiji** | 161 | **0** | clean |
| AbdulBaset AbdulSamad (murattal) | 1 | **0** | clean |
| Abdur-Rahman as-Sudais (?duplicate?) | – | – | – |
| Mahmoud Khalil Al-Husary | 6 | **0** | clean |
| Mahmoud Khalil Al-Husary muallim | 12 | **0** | clean |
| Sa`ud ash-Shuraym | 10 | **0** | clean |
| Mohamed Siddiq al-Minshawi mujawwad | 8 | – | no audio (404) |

## Per-surah, per-reciter table

| reciter | id | surah | n_shifts | verses | offsets |
|---------|---:|------:|---------:|--------|--------:|
| Sudais | 3 | 3 | 36 | 100-102, 105-106, 110, 112, 114, 117-118, 120, 122, 124-125, 127, 129-131, 134-135, 142, 145-147, 153, 157, 159, 161, 167-169, 181, 183-186 | -3, -2, -1 |
| Sudais | 3 | 4 | 42 | 8, 14-15, 17-20, 26, 35, 41, 47-48, 51, 54-55, 57, 60-64, 69, 72-75, 78-79, 82-84, 86, 88-90, 93-95, 103, 113, 139, 160 | -2, +1, +2, +3 |
| Sudais | 3 | 5 | 36 | 8, 12, 15, 17-18, 20, 23-24, 27, 30-33, 36, 39-40, 47, 57, 59, 62, 64, 66, 70, 75, 77, 79-80, 85-88, 99, 114, 116-117, 120 | -2, -1 |
| Sudais | 3 | 28 | 25 | 25, 45, 50, 54-58, 60, 63-64, 66-68, 70-71, 73, 75-76, 78-79, 81, 84-85, 87 | -2, -1, +1 |
| Sudais | 3 | 29 | 18 | 20, 22, 27-29, 31-32, 36, 39, 44, 47, 51-53, 56, 62, 66-67 | -2, -1 |
| Mishary | 7 | 37 | 18 | 89, 91, 94, 99, 109, 115, 118-119, 122, 127-128, 133-134, 139-141, 146, 148 | +1 |
| Mishary | 7 | 82 | 5 | 10-11, 13, 16, 19 | -2, -1 |
| AbdulBaset (alt) | 2 | 2 | 13 | 27, 30-31, 33, 38-41, 44-46, 48, 59 | -3, -2, -1 |
| Shatri | 4 | 2 | 1 | 150 | -1 |
| Shatri | 4 | 10 | 6 | 47, 78, 81, 95, 104, 108 | +1 |
| Hani ar-Rifai | 5 | 16 | 5 | 83, 99, 110, 122, 128 | -1 |
| Minshawi | 9 | 4 | 3 | 131, 168-169 | +1 |
| Tablawi | 11 | 4 | 2 | 121, 168 | -1 |

## Methodology

* Audio files: `https://download.quranicaudio.com/qdc/<reciter_slug>/<style>/<N>.mp3`,
  with `audio_url` pulled from each `chapter_recitations/<rid>/<N>?segments=true` API response.
* Cross-check: faster-whisper `medium` (or `large-v3` for spot-check of
  Mishary 82) on the audio span specified by API `timestamp_from..to`,
  `language="ar"`, `vad_filter=False`, no canonical text bias.
* Similarity: length-normalized longest-common-subsequence on bare
  Arabic letter strings (diacritics, alef variants, ta marbuta folded
  to canonical forms).
* Confidence threshold: a verse is reported only if Whisper's
  transcription matches a neighbour verse with similarity >= 0.70 and
  beats the claimed-verse similarity by >= 0.20.
* Confirmed by user audibly on Mishary 82:9-13.

## Reproduction

```
.venv/Scripts/python.exe fetch_reciter.py <rid>
.venv/Scripts/python.exe verify_only_reciter.py <rid> --whisper-model medium
.venv/Scripts/python.exe summarize_findings.py
```

Outputs:

  * `reports/whisper_verify_r<rid>.json` — per-verse Whisper transcription + similarity
  * `logs/r<rid>_verify_only.log` — per-reciter log
  * `logs/findings_so_far.md` — auto-regenerated summary table
  * `logs/master.ndjson` — append-only event log across reciters
  * `reports/qul_issue_mishary_surah82.md` — example QUL issue draft

## Status

* All 12 active reciters scanned. 7 have at least one high-confidence shift,
  5 are clean.
* Sudais (157 shifts spread across 5 surahs) is by far the worst offender
  and likely the most impactful on quran.com users since he's a popular
  reciter in the listing.
* Mishary Surah 82 already user-verified by ear; same methodology
  produced all other findings here.

## Suggested PR order to QUL

1. **Mishary Surah 82** — already-prepared issue at
   `reports/qul_issue_mishary_surah82.md`. Smallest, cleanest, audibly
   verified.
2. **Sudais Surahs 3, 4, 5** — 114 shifts across the long Madinan
   surahs. Highest user-visible impact.
3. **Mishary Surah 37** — sustained +1 shift across 50 verses.
4. **AbdulBaset (alt) Surah 2** — 13 shifts in the middle of Al-Baqarah.
5. **Sudais Surahs 28, 29** — 43 more shifts.
6. **Smaller findings** (Shatri / Hani / Minshawi / Tablawi) — file as
   batch or skip.
