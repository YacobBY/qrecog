# Quran.com translation/audio subtitle drift — findings & fix plan

**Reciter under investigation:** Khalifah Al Tunaiji (`khalifah_taniji`), reciter ID **161** on quran.com.
**Bug as reported by user:** *"audio and English translation subtitles sometimes don't line up on the timestamp."*

This document is the result of a proof-of-concept investigation. **No upstream changes were submitted.** All artifacts are local to `C:\programming\qrfix\`.

---

## 1. Architecture (verified)

```
quran.com frontend (Next.js)            github.com/quran/quran.com-frontend-next
        │ fetches per-reciter timestamps from
        ▼
Quran Foundation API (Rails)            github.com/quran/quran-api-rails        (DB private)
        │ DB rows are populated/edited via
        ▼
QUL — Quranic Universal Library         github.com/TarteelAI/quranic-universal-library
        │ original timing data sources:
        ▼
Forced-alignment pipelines              github.com/cpfair/quran-align (CMU Sphinx)
                                        + GreenTech Foundation contributions
```

The data we need to fix lives in **QUL**, not the frontend.

---

## 2. How the frontend uses the timestamps

Confirmed by reading `repos/frontend/`:

- **Translation subtitles are 100% verse-level** — never use word segments.
  - `src/components/QuranReader/TranslationView/TranslationViewCell.tsx:48-55`
- Active verse is computed every audio `timeupdate`:
  - `src/xstate/actors/audioPlayer/audioPlayerMachineHelper.ts:31-64` (`getActiveVerseTiming`)
  - `src/xstate/actors/audioPlayer/isCurrentTimeInRange.ts:14-15` — `currentTime >= timestamp_from && currentTime < timestamp_to`.
- **No per-reciter offset, no calibration.** Only a 200ms Safari tolerance.
- Word-level segments only drive Arabic word-by-word highlight, never English translation.

**Implication:** the bug, if any, is strictly in `timestamp_from`/`timestamp_to` for the reciter in QUL.

---

## 3. The right way to measure user-perceptible drift

A naive comparison of "API boundary vs silence midpoint" is misleading. Reciters pause for ~300-700ms between verses. The translation flip happens during that silence, and the user **does not perceive** any drift as long as the flip lands somewhere in the silence interval.

Correct test: classify each API boundary against the inter-verse silence:

| API position | User perception |
|---|---|
| API ∈ [silence_start, silence_end] | **fine** — flip happens during silence |
| API > silence_end | **LATE** — translation lags into the next verse's audio |
| API < silence_start | **EARLY** — translation flips while previous verse still being recited |

This is what `analyze_drift_v2.py` does.

### Cross-validation

Whisper-small (`align_whisper.py`) was run on Surah 1 (47 s) and Surah 78 (252 s) for cross-validation:
- For Surah 1, Whisper produced exactly 7 segments matching 7 verses; the start of each segment's first **Arabic** word agrees with `silence_end` to within ~50 ms, confirming the silence-detection signal.
- For longer surahs, Whisper-small **merges multiple ayat into a single segment** (Surah 78: 10 segments for 40 verses), so it cannot be used directly as a per-verse boundary signal without true forced alignment to the known text. silencedetect remains the practical signal.

---

## 4. The bug, in concrete numbers

10 sampled surahs (1, 2, 18, 36, 55, 67, 78, 100, 112, 114), 645 verse boundaries total. Re-run with `python analyze_drift_v2.py`.

| | LATE | EARLY |
|---|---|---|
| count | 5 / 645 | 9 / 645 |
| max magnitude | **269 ms** (Surah 1:5) | 166 ms (Surah 78:29) |
| median | 136 ms | 72 ms |

Almost all boundaries (97.8%) are fine. The clearly broken set is **Surah 1, verses 4-6**:

| boundary | API claims | inter-verse silence | classification |
|---|---|---|---|
| 1:4 → 1:5 | 21 420 ms | [20 744, 21 284] | LATE by **136 ms** |
| 1:5 → 1:6 | 27 720 ms | [26 769, 27 451] | LATE by **269 ms** |
| 1:6 → 1:7 | 33 000 ms | [32 006, 32 766] | LATE by **234 ms** |

When verse 6 ends and verse 7 begins, the audio plays verse 7 for 234 ms before the English column flips. **That's the user-visible bug.** It's specific to Al-Fatihah for this reciter; other surahs are mostly clean. That matches the user's report ("sometimes don't line up").

Smaller perceptible-but-marginal cases:

- Surah 55: 7 EARLY (max 132 ms) + 1 LATE (75 ms). Mostly under perceptual threshold (~150 ms).
- Surah 78: 1 EARLY by 166 ms (verse 29).
- Surah 100: 1 EARLY by 74 ms.
- Surah 18: 1 LATE by 63 ms.

(Re-run `python compare_silence.py` for the older "midpoint vs API" view; that's a noisier metric but still useful for finding candidate problem surahs.)

---

## 5. Where the fix lands — QUL data model

Verified in `repos/qul/`.

- Model: `Audio::Segment` (table `audio_segments`), one row per (recitation, verse).
  - `app/models/audio/segment.rb` lines 64–114.
  - Columns: `timestamp_from`, `timestamp_to`, `duration_ms`, `verse_key`, `audio_file_id`, `audio_recitation_id`, `chapter_id`, `verse_id`, **`segments` (JSONB array of `[word_index, start_ms, end_ms]`)**.
- Reciter row: `Audio::Recitation.find_by(reciter_id: 161)`.
- Edit paths:
  - **Programmatic**: `segment.set_segments!(triples, current_user)` and `segment.update_time_and_offset_segments(from_ms, to_ms, verse_key)`.
  - **Bulk import (CSV)**: `lib/utils/merge_ayah_segment.rb` lines 65-98 reads `data/raw_segments/{recitation_id}/timing/{chapter}.csv`.
  - **Web UI**: `/surah_audio_files/:audio_recitation_id/segment_builder?chapter_id=N` (`app/controllers/surah_audio_files_controller.rb` lines 44-79).
- A `segment_locked` flag on `Audio::Recitation` blocks edits — must be unlocked before any contribution lands.

---

## 6. The candidate fix in this repo

For each sampled surah:

- `data/surah_<N>_tunaiji.json` — raw API response (`segments=true`)
- `data/corrected/surah_<N>_corrected.json` — corrected verse boundaries; word segments rescaled proportionally
- `data/corrected/surah_<N>_diff.json` — per-verse `(old_from, old_to, new_from, new_to, delta_to)`
- `data/corrected/surah_<N>_qul.csv` — QUL-style CSV ready to drop into `data/raw_segments/161/timing/<N>.csv`

### How the corrected boundary is chosen

For each API boundary that falls outside its inter-verse silence:

- If API is LATE (past `silence_end`): set new boundary = `silence_end - 50 ms`.
- If API is EARLY (before `silence_start`): set new boundary = `silence_start + 50 ms`.
- Skip if drift < 150 ms (under perceptual threshold).
- Skip if no silence within 1500 ms or silence shorter than 200 ms.

This is conservative — it only touches boundaries that are demonstrably perceptible, and it places them *just inside* the silence at the appropriate side. Inter-verse gap is preserved at 0 (verse N+1's `from` snaps to verse N's new `to`). Word segments inside an adjusted verse are linearly rescaled to fit the new span.

Re-run with: `python generate_fix.py`.

### Surah 1 corrected output

```
ayah,timestamp_from_ms,timestamp_to_ms,duration_ms
1,0,5620,5620
2,5620,11650,6030
3,11650,16510,4860
4,16510,21234,4724        # was 21420 -- pulled in by 186 ms
5,21234,27401,6167        # was 21420->27720 -- pulled in by 319 ms cumulatively
6,27401,32716,5315        # was 27720->33000 -- pulled in by 284 ms cumulatively
7,32716,47050,14334
```

---

## 7. Visual A/B verification

`demo/surah_1.html`, `demo/surah_55.html`, `demo/surah_78.html` are self-contained HTML pages that play the audio with two parallel highlight tracks: red for current API timestamps, green for corrected timestamps.

To run: `python serve.py`, then `http://127.0.0.1:8765/demo/surah_1.html`.

Press play. On the broken boundaries (1:4 → 1:5, 1:5 → 1:6, 1:6 → 1:7) you can hear the new verse begin reciting while the red row is still highlighting the old verse, and the green row flips at the right time. On the clean boundaries (1:1 → 1:2, 1:2 → 1:3, 1:3 → 1:4) red and green flip at the same instant.

---

## 8. Honest limitations

1. **Silencedetect ≠ true forced alignment.** It infers boundaries from amplitude valleys, which works well when reciters pause but breaks down for tightly-chained verses. About 10-25% of boundaries in some surahs lack a clean silence in the audio (`UNMATCHED` rows in the report) — those would need real forced alignment.
2. **Word-level segments are rescaled proportionally**, not re-aligned. After fixing the verse span, every word inside is mapped linearly. The translation subtitle bug is purely verse-level so this is fine for *that* fix; but a proper QUL contribution should regenerate word segments via real alignment to keep word-by-word highlighting accurate.
3. **Only 10 surahs sampled.** A full pass would download all 114 mp3s and produce a CSV per chapter.
4. **Whisper-small was useful as cross-validation but not as primary signal** — it merges verses on longer surahs. A production pipeline would use Whisper-medium with the known Arabic text as `initial_prompt`, or wav2vec2 + CTC for true forced alignment, or the existing `cpfair/quran-align` CMU Sphinx pipeline.
5. **Nothing was sent upstream.** Concrete corrections only exist as local CSV/JSON.

---

## 9. Recommended path forward

1. **Replace silencedetect with proper forced alignment.** Easiest in 2026: `WhisperX` (Whisper + wav2vec2 for sub-50 ms word boundaries), or `aeneas`, or run the existing `cpfair/quran-align` pipeline with this reciter's audio. The known authoritative Arabic text from QUL is the input.
2. **Run alignment on all 114 surahs of Tunaiji** and produce one CSV per chapter, in `data/raw_segments/161/timing/{N}.csv` format that `lib/utils/merge_ayah_segment.rb` ingests.
3. **Open a GitHub issue on `TarteelAI/quranic-universal-library`** with: this PoC, the worst surahs (Al-Fatihah specifically), and the reproduction script. Reference reciter ID 161 and confirm `segment_locked` status.
4. **Submit a PR** with the corrected CSVs through the existing import pipeline. No new code on QUL's side.
5. The Quran Foundation API picks up corrected segments via QUL's regular export. quran.com frontend reflects the fix automatically. **No frontend changes needed.**

Optional ergonomic add-on for the frontend: a "report this drift" button on the audio player that captures (reciter, surah, currentTime) and links it to a QUL issue.

---

## 10. Reproduce, end to end

```bash
cd C:\programming\qrfix
.venv/Scripts/python.exe -m pip install faster-whisper   # one-time

python compare_silence.py        # naive midpoint-based drift report
python analyze_drift_v2.py       # honest user-perceptible drift report
python generate_fix.py           # corrected JSON + QUL CSVs
PYTHONIOENCODING=utf-8 python build_demo.py 1 55 78
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe align_whisper.py 1 small  # optional cross-check
python serve.py                  # then open the demo URLs in a browser
```

Repos referenced (shallow clones in `repos/`):
- `quran/quran.com-frontend-next` → `repos/frontend`
- `TarteelAI/quranic-universal-library` → `repos/qul`
- `cpfair/quran-align` → `repos/align`
