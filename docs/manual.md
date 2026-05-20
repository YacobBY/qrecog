# Manual

This is the user-facing guide to every script in `qrfix`. For
installation see [install.md](install.md). For the reasoning behind the
pipeline design see [methodology.md](methodology.md).

## Tour

```
qrfix/
├── analyze_tunaiji.py       ← single-command entry for one reciter
├── process_reciter.py       ← end-to-end for any reciter id
├── run_all_reciters.py      ← orchestrate every reciter
│
├── fetch_all.py             # download Tunaiji's data
├── fetch_reciter.py         # download any reciter's data
├── batch_align.py           # WhisperX forced alignment
├── force_align.py           # alignment library used by batch_align
├── heal_alignment.py        # chronological-order post-processor
├── generate_fix_whisperx.py # write corrected timestamps
├── detect_shifts.py         # IoU shift detector (CTC-only signal)
├── verify_with_whisper.py   # Whisper-transcription cross-check
├── summarize_findings.py    # aggregate Whisper-verify across reciters
├── status.py                # one-screen pipeline state view
├── build_demo.py            # write A/B HTML player for a surah
├── serve.py                 # localhost static server for demos
├── reciter_paths.py         # per-reciter file layout
├── whisperx_align.py        # standalone WhisperX wrapper (debug aid)
```

Reciter ids come from `https://api.quran.com/api/v4/resources/recitations`.
Tunaiji is a special "legacy" id (161): his outputs land in the
top-level `audio/`, `data/`, etc. instead of `reciters/r161/`.

## The single-file pipeline

```bash
python analyze_tunaiji.py
```

This is the simplest entry point. It runs steps 1–6 below for reciter
161 and writes a final report to `reports/tunaiji_findings.md`. Every
step is idempotent — re-running just re-prints the report.

Useful flags:

```bash
python analyze_tunaiji.py --skip-whisper-verify    # CTC pipeline only
python analyze_tunaiji.py --whisper-model large-v3 # more accurate, slower
python analyze_tunaiji.py --only-step 7            # re-print the report
```

## The full pipeline, step by step

Every script accepts `--reciter-id N` (default 161 = Tunaiji). The
output of each step is the input of the next.

### 1. Fetch — `fetch_reciter.py`

Downloads three things per surah (1..114) of one reciter:

```text
audio/surah_<NNN>.mp3            # MP3 from quranicaudio.com
data/surah_<N>_tunaiji.json      # API timestamps from quran.com
data/surah_<N>_verses.json       # canonical text from quran.com
```

For non-Tunaiji reciters, files land under `reciters/r<id>/audio/` and
`reciters/r<id>/data/` instead. Skips files that already exist.

```bash
python fetch_reciter.py 7        # Mishary
python fetch_all.py              # Tunaiji (legacy alias)
```

### 2. Align — `batch_align.py`

Loads `jonatasgrosman/wav2vec2-large-xlsr-53-arabic` once, then runs
WhisperX forced alignment on every surah. Writes per-verse word
timings to:

```text
data/whisperx/surah_<N>_force_v2.json
```

Each entry has `from_ms`, `to_ms`, `n_aligned`, and a `words[]` list
with `start`, `end`, `score` per word.

```bash
python batch_align.py                          # all 114 surahs
python batch_align.py 1 36 78                  # specific surahs
python batch_align.py --reciter-id 7
python batch_align.py --force                  # re-run skipping cache
```

The chunker breaks long surahs into ≤30 s segments using API timestamps
as approximate cuts. Tune `CHUNK_TARGET_S` in `force_align.py` if you
hit OOM on a smaller GPU.

### 3. Heal — `heal_alignment.py`

Post-processing pass that enforces chronological-order constraints
(words can't overlap, verse N+1 starts after verse N ends, etc.) and
redistributes low-confidence words between high-confidence anchors,
optionally snapping to ffmpeg-detected silences. Writes:

```text
data/whisperx_healed/surah_<N>.json
```

Each word gets a `healed_by` field listing which passes touched it
(`monotonicity`, `interpolate:low_score_or_outlier`,
`silence_snap:fill_ratio_low_conf`, `verse_continuity`, etc.) so you can
audit decisions.

```bash
python heal_alignment.py
python heal_alignment.py --reciter-id 7
```

### 4. Fix — `generate_fix_whisperx.py`

Writes corrected timestamps for every verse boundary that drifts
outside the inter-verse silence per ffmpeg silencedetect, snapping to a
WhisperX-derived target.

```text
data/corrected_v2/surah_<N>_corrected.json   # API-shape, fixed timing
data/corrected_v2/surah_<N>_diff.json        # per-verse diff vs API
data/corrected_v2/surah_<N>_qul.csv          # QUL-style row
data/corrected_v2/summary.json               # aggregate
```

Tunable thresholds at the top of the file:

| Constant | Default | What it does |
|----------|--------:|--------------|
| `MAX_TRUST_DELTA_MS` | 2500 | If WhisperX disagrees with API by more than this, distrust WX (assume CTC failure) |
| `MAX_MATCH_MS` | 2500 | Ignore ffmpeg silences this far from the API boundary |
| `MIN_SILENCE_LEN_MS` | 100 | Discard silences shorter than this (intra-verse breaths) |
| `MIN_SILENCE_DUR_S` | 0.10 | The same threshold passed to ffmpeg silencedetect |
| `EARLY_PAD_MS` | 250 | Tolerate boundary in the vowel-decay zone right after a verse |
| `LATE_PAD_MS` | 50 | LATE drift is acutely perceptible — minimal tolerance |
| `SAFETY_MS` | 50 | Snap to silence end minus this so subtitle flips just before next voice |

### 5. Detect — `detect_shifts.py`

Compares API span vs WhisperX span via IoU. Catches whole-verse shifts
when *both* the WX alignment is reliable (high score) AND it disagrees
with the API. Writes:

```text
reports/verse_shifts.json
```

Three confidence buckets:

- **STRONG**: high WX score on both this verse and its best-matching
  shifted neighbour.
- **WEAK**: at least one side has low WX score.
- **WX_GLITCH**: WX disagrees with API but no neighbour-verse match
  found — most likely our alignment failed, no inference possible.

This signal *misses* shifts in regions where WX itself fails
(self-shadowing). Always cross-check with `verify_with_whisper.py`.

```bash
python detect_shifts.py
python detect_shifts.py 7 13 82             # specific surahs
python detect_shifts.py --reciter-id 7
```

### 6. Whisper-verify — `verify_with_whisper.py`

The most reliable signal. For each verse, transcribe the API span with
Whisper-large-v3 (or medium), normalise the output, and compute character
similarity vs every nearby canonical verse. Flags the verse when the
best match isn't *itself*:

```text
reports/whisper_verify.json
```

Flag types:

- `shift_+1`, `shift_+2`, `shift_-1`, `shift_-2`: the API span actually
  contains the audio of a different verse. With `best_match_sim ≥ 0.7`,
  this is essentially a confirmed bug.
- `low_match`: Whisper transcribed the audio but it doesn't match the
  claimed verse OR any neighbour well. Could be a CTC-style WX problem,
  could be edge drift large enough to confuse Whisper.

```bash
python verify_with_whisper.py                                   # all 114
python verify_with_whisper.py --model-size large-v3             # more accurate
python verify_with_whisper.py 13 82 --verbose                   # specific surahs
python verify_with_whisper.py --reciter-id 7
```

Time budget at `medium`: ~30 min for the full Quran on a 4090.
At `large-v3`: ~60 min.

### 7. Summarize — `summarize_findings.py`

Aggregates all `reports/whisper_verify_r*.json` (and the legacy
`reports/whisper_verify.json` for Tunaiji) into:

```text
logs/findings_so_far.md
```

A markdown table sortable by reciter and surah, listing every
high-confidence shift (sim ≥ 0.7).

```bash
python summarize_findings.py
```

### 8. Status — `status.py`

Tells you which steps are done for which reciters:

```bash
python status.py
```

Output (truncated):

```text
 rid                            name  audio    wx  heal   fix   ver  shifts
--------------------------------------------------------------------------------
 161             Khalifah Al Tunaiji    114   114   114   114   114      39
   7        Mishari Rashid al-`Afasy    114   114   114   114   114      23
   3          Abdur-Rahman as-Sudais    114    --    --    --    --      --
```

### 9. Audible verification — `build_demo.py` + `serve.py`

For any surah you want to listen to with side-by-side red (current
API) / green (corrected) translation flips:

```bash
python build_demo.py 13 78 82
python serve.py
# browse to http://localhost:8000/demo/surah_13_v2.html
```

## Per-reciter end-to-end — `process_reciter.py`

```bash
python process_reciter.py 7 --name "Mishary al-Afasy"
```

Runs steps 1-6 above for one reciter, logs to `logs/r7.log`, appends
a structured event to `logs/master.ndjson`, and emits a per-reciter
findings dict.

Flags:

```bash
--whisper-model medium|large-v3
--skip-whisper-verify             # CTC-only sweep, ~10x faster
```

## All reciters — `run_all_reciters.py`

```bash
python run_all_reciters.py --whisper-model medium
```

Iterates `process_reciter.py` over the 11 non-Tunaiji ids in a
small-data-first order. ~20 hours total on a 4090 because the longest
reciters (Husary mujawwad) take 5+ hours of GPU time each.

```bash
python run_all_reciters.py --start-from 5    # resume after a crash
python run_all_reciters.py --skip-whisper-verify
```

## Filing fixes upstream

- The data lives at <https://qul.tarteel.ai/>; see the FAQ entry
  ["How do I submit corrections?"](https://qul.tarteel.ai/faq#faq-5).
- Open an issue at
  <https://github.com/TarteelAI/quranic-universal-library/issues>
  attaching:
  - the affected reciter id and surah(s),
  - the corrected `data/corrected_v2/surah_<N>_qul.csv`,
  - a screen-recording of the relevant
    `demo/surah_<N>_v2.html` showing the wrong-vs-right flip,
  - the `reports/whisper_verify*.json` excerpt with character-similarity
    evidence.

See [findings.md](findings.md) for ready-to-attach example issue
bodies.

## Conventions

- All times are milliseconds, except WhisperX word-level `start`/`end`
  which are seconds (legacy from whisperx).
- Surah numbers are 1-indexed (1..114). Verse numbers are 1-indexed
  within a surah. The string form is `"<surah>:<verse>"` (e.g.
  `"13:20"`).
- Reciter id 161 is the legacy Tunaiji default. Outputs go to top-level
  `audio/`, `data/`, etc. Other reciters live under `reciters/r<id>/`.
