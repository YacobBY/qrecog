# qrfix — Project Summary

## What this project is

A pipeline that detects and corrects **verse-level timestamp drift** in Quran
recitation audio as published on quran.com. The same recitation segmented by
two different sources (the reciter audio + the canonical Uthmani text) can
drift by a few hundred milliseconds, which causes the on-screen subtitle to
appear too early or stay too late versus what the listener is hearing.

The pipeline:

1. Downloads audio + canonical text + the currently-published per-verse
   timestamps from `api.quran.com` for a reciter.
2. Runs **WhisperX forced alignment** of the canonical text against the audio
   on a wav2vec2 CTC Arabic acoustic model to get reliable per-word
   `[start, end, score]`.
3. Compares the aligned verse boundaries to the API-published boundaries.
4. Emits corrected timestamps in the **QUL CSV format** consumed by
   TarteelAI's `quranic-universal-library` so the fix can be PR'd upstream.

The reciter that drove the work is **Khalifah Al Tunaiji** (`reciter_id 161`).
The user-reported symptom was Surah 1, verses 4–6 lagging 100–300 ms late.

## Codebase layout

| Path | Purpose |
|------|---------|
| `force_align.py` | Per-surah forced alignment using chunked whisperx.align |
| `whisperx_align.py` | Single-file transcribe+align utility |
| `generate_fix_whisperx.py` | Reads aligned JSON + API JSON, emits corrected CSV/JSON |
| `reciter_paths.py` | Per-reciter path layout (audio, data, outputs) |
| `fetch_all.py`, `fetch_reciter.py` | Download audio + API timestamps + canonical text |
| `batch_align.py`, `process_reciter.py`, `run_all_reciters.py` | Orchestration over multiple surahs/reciters |
| `detect_shifts.py`, `verify_with_whisper.py`, `analyze_tunaiji.py` | Legacy/diagnostic drift analysis |
| `build_demo.py`, `serve.py`, `web/` | Local A/B audio demo (compare old vs corrected timestamps) |
| `experiments/` | Model A/B comparisons, side analyses |
| `legacy/` | Older approaches kept for reference (silencedetect-based fix, etc.) |
| `reports/` | Curated findings markdown |
| `docs/` | install / manual / methodology / findings |

Heavy artifacts (`audio/`, `data/`, `repos/`, `.venv/`, `logs/`, `demo/`,
`reciters/`) are gitignored.

## Pipeline detail

### Alignment model (decided this session)

**Use `jonatasgrosman/wav2vec2-large-xlsr-53-arabic`** as the CTC alignment
model.

- Previously used `elgeish/wav2vec2-large-xlsr-53-arabic`. Its vocab is
  **Buckwalter Latin transliteration**, so feeding it raw Arabic produced an
  all-`<unk>` trellis that collapsed the alignment.
- `jonatasgrosman`'s vocab is native Arabic: 28 letters + hamza variants
  (ء آ أ ؤ إ ئ) + ta marbuta + alif maqsura + all 8 harakat + tatweel
  (51 tokens total — see `data/jonatasgrosman_vocab.json`). This is also
  WhisperX's documented default Arabic alignment model.
- This switch removed the transliteration round-trip entirely.

### Text normalization fed to the aligner

The model was trained on undiacriticized text, so **`normalize()` strips
diacritics** before alignment. It also strips tatweel and folds:

- `ٱ → ا`, `آ → ا`, `أ → ا`, `إ → ا`
- `ى → ي`
- `ة → ه`

Quranic pause marks (`ۖ ۚ ۛ ۜ ۗ ۘ ۙ` etc., U+06D6–U+06ED) are non-spoken
tokens and are filtered out at the word level.

### Chunked alignment

Earlier attempts fed the entire surah audio + text into one
`whisperx.align()` call. Two problems:

1. **CUDA OOM** on long surahs — Surah 2 attempted a 44 GB allocation on a
   24 GB GPU.
2. **Trellis collapse** on long input — WhisperX would jam many verses into
   the front of the chunk and leave the tail unaccounted for.

Solution: chunk the audio using the API-published timestamps as approximate
cut points, targeting ~30 s per chunk with 500 ms pad on each side, then run
a single batched `whisperx.align()` over all chunks. Each chunk gets the
concatenated normalized text of its constituent verses. Word counts are
preserved so we can re-group by canonical word count after alignment.

Constants in `force_align.py`:

```
CHUNK_TARGET_S = 30.0    # close a chunk when accumulated audio exceeds this
CHUNK_PAD_MS = 500       # pad each chunk on both sides so we don't clip a word
```

The legacy per-verse `silencedetect` windowing approach (using ffmpeg
`silencedetect` to bracket each verse) was removed — it was brittle on
liaison-heavy recitation.

### Fix generation (`generate_fix_whisperx.py`)

For each adjacent verse pair `N, N+1`:

1. **Silence span** = `[verse_N.last_word.end, verse_N+1.first_word.start]`
   from the aligned JSON.
2. **API boundary** = the timestamp where the published API splits the two
   verses.
3. **Imperceptible zone** = `[silence_start - EARLY_PAD_MS,
   silence_end + LATE_PAD_MS]`. Asymmetric on purpose:
   - Subtitle popping in **early** is more tolerable (user just sees text a
     bit ahead of the reciter).
   - Subtitle **lingering late** or cutting in late is more disruptive.
4. If the API boundary already sits inside the imperceptible zone → leave
   alone.
5. Otherwise:
   - **LATE drift** (API boundary > silence_end): snap to
     `silence_end - SAFETY_MS`.
   - **EARLY drift** (API boundary < silence_start): snap to
     `silence_start + SAFETY_MS`.
6. The **last verse's right edge stays at the API value** — the final
   subtitle should remain on screen, not cut off when the reciter trails off.

Confidence guards:

```
SAFETY_MS = 50
MIN_FIX_DRIFT_MS = 150       # don't bother correcting drifts below this
LEAD_MS = 50
MAX_TRUST_DELTA_MS = 1500    # if alignment disagrees w/ API by >this, distrust it
MIN_WORD_SCORE = 0.20        # ignore verses whose boundary words scored below this
EARLY_PAD_MS = 250
LATE_PAD_MS = 50
```

`MAX_TRUST_DELTA_MS` was added after Surah 2 verse 2:17 showed a 6348 ms
delta — `silencedetect` on the raw audio confirmed the API was actually
correct and WhisperX had collapsed two verses into the front of a chunk.

### Outputs

For each surah `N`:

- `data/whisperx/surah_<N>_force_v2.json` — per-verse word timings from
  forced alignment.
- `data/corrected_v2/surah_<N>_corrected.json` — corrected per-verse
  timestamps.
- `data/corrected_v2/surah_<N>_diff.json` — per-boundary diff vs API.
- `data/corrected_v2/surah_<N>_qul.csv` — QUL upstream-ready CSV.

QUL CSV columns: `chapter, ayah, timestamp_from_ms, timestamp_to_ms,
duration_ms, segments_json`.

## What got done this session

1. Reconsidered the model and **dropped Buckwalter transliteration entirely**
   in favor of native-Arabic `jonatasgrosman` (resolved the original blocker
   in `project_plan.txt`).
2. Rewrote `force_align.py` to use chunked full-audio alignment; removed the
   `silencedetect`-based per-verse windowing.
3. Updated `whisperx_align.py` to the same model.
4. Wrote `generate_fix_whisperx.py` from scratch with asymmetric pads and
   confidence guards.
5. Ran the pipeline end-to-end on 10 surahs: **1, 2, 18, 36, 55, 67, 78,
   100, 112, 114**. Surah 2 (~2 hr audio) completed in ~49 s wall time.
6. **Verified Surah 1 corrections match the user-reported drift**:
   - 1:5 → 1:6 boundary: −334 ms (LATE)
   - 1:6 → 1:7 boundary: −330 ms (LATE)
   - 1:4 → 1:5 boundary: −197 ms (LATE)
   - 1:2 → 1:3 boundary: +427 ms (EARLY, also caught)
7. Saved `data/jonatasgrosman_vocab.json` for reference.
8. Updated `project_plan.txt` with all decisions taken.

## Errors hit + how they were resolved

| Symptom | Root cause | Fix |
|--------|------------|-----|
| All-`<unk>` trellis on raw Arabic | elgeish model uses Buckwalter vocab | Switched model |
| `UnicodeEncodeError` printing Arabic on Windows | cp1252 default codepage | `PYTHONIOENCODING=utf-8` |
| `NameError: flat_norm` | Leftover ref after chunking refactor | Replaced with `n_words_total` |
| `CUDA OOM` on Surah 2 | Single-pass alignment of whole audio | 30 s chunked alignment |
| Surah 2:17 had 6348 ms delta | WhisperX trellis collapse, API actually correct | Added `MAX_TRUST_DELTA_MS=1500` |
| PAD=200 over-corrected (199/286 verses) | WhisperX word "end" fires before audio truly goes quiet (CTC posterior decay) | Asymmetric `EARLY_PAD_MS=250 / LATE_PAD_MS=50` |
| PAD=300 missed reported Surah 1 drifts | Pad swallowed the real LATE drifts | Same — asymmetric pads |

## Open work

- Rebuild the A/B audio demo (`build_demo.py`) against `data/corrected_v2/`
  (currently points at `data/corrected/`).
- Audibly verify Surah 1 fix in the browser demo.
- Download the remaining 104 surah audio files for Tunaiji.
- Run forced alignment + fix generation across all 114 surahs.
- Open an issue at `TarteelAI/quranic-universal-library` describing the drift
  and proposing the corrected CSVs.
- PR the corrected CSVs through QUL's `merge_ayah_segment.rb` path.

## Pre-existing context worth carrying over

- The previous broader investigation across 12 reciters lives in
  `reports/all_reciters_summary.md` and `logs/findings_so_far.md`.
- Tunaiji is one of multiple reciters whose published timestamps drift; the
  pipeline is reciter-agnostic via `reciter_paths.py`, gated on availability
  of audio + canonical text + API timestamps for that reciter.
- The current repo had been prepared for publication as a single
  `Initial commit: qrfix pipeline + docs` (`abfcbe3`) with a strict
  `.gitignore` excluding all heavy artifacts.
