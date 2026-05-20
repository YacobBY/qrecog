# Full-Quran scan findings — Khalifah Al Tunaiji (reciter 161)

Scope: all 114 surahs of Tunaiji's recitation. Audio downloaded from
quranicaudio.com (1.2 GB total). API timestamps + canonical text from
`api.quran.com/api/v4/chapter_recitations/161/<N>?segments=true`.
WhisperX forced alignment using
`jonatasgrosman/wav2vec2-large-xlsr-53-arabic`. Hybrid fix generator
(ffmpeg silencedetect for in-silence judgment, WhisperX for snap
target) wrote corrected timestamps to `data/corrected_v2/`.

## Aggregate

  * 6236 verses across 114 surahs
  * 166 verses had at least one boundary corrected by the hybrid fix
  * 24 surahs have any correction at all; 90 surahs are clean
  * 41 verses have a boundary correction of >= 800 ms

## Whole-verse-shift detector (detect_shifts.py)

Compares each API verse span to its WhisperX span via IoU and looks
for cases where API[N]'s span best matches WhisperX[N+k] for k != 0.
Across 114 surahs:

  * 1 STRONG flag — turned out to be a WhisperX failure on the same
    verse, not a real API shift (Surah 34:49)
  * 9 WEAK flags — low WhisperX confidence, can't conclude
  * 20 WX_GLITCH flags — our alignment failed, no inference possible

**No multi-verse shift cluster (>=2 consecutive verses with the same
shift offset) was found.** The user's hypothesis "API verse N actually
plays verse N+1's audio" is not the dominant failure mode here.

What we did find is **sustained edge-drift over many consecutive
verses**, which produces the same listener experience as a shift: the
translation lags or leads by a full second or more for a stretch of
verses, then resyncs.

## Top suspect surahs (audibly verify in `demo/surah_<N>_v2.html`)

### Surah 13 — clearest pattern

  * Verses 1-19: clean (zero corrections)
  * Verses 20-31: sustained +700 to +1574 ms correction (API is
    EARLY: translation flips before the verse audibly ends)
  * Verses 32-43: mostly clean again

The drift begins abruptly at verse 20 (delta_to = +1438 ms) and
gradually decays over the next ~12 verses. ffmpeg silencedetect
confirms several of these API boundaries land in the *middle* of
speech, not in inter-verse silence (e.g. 13:23 boundary at 612 420 ms
is 5.8 s away from any silence >= 500 ms).

### Surah 10 — many drifts

  * 17 verses with |delta| >= 500 ms (median +603 ms)
  * Concentrated in verses 65-110
  * Pattern is messier than Surah 13 -- could be partly drift,
    partly WhisperX failure on the same passages

### Surah 14 — mixed-direction drifts

  * 8 verses with |delta| >= 500 ms (median -593 ms)
  * Both EARLY and LATE corrections, up to 1456 ms
  * Verses 14:13/14/15 have the most jarring pattern (boundary
    at 351 600 ms is 5.5 s before the next real inter-verse silence)

### Surah 72

  * 3 verses with |delta| >= 500 ms, max -949 ms
  * Localized cluster around verses 17-18

## Largest single corrections (>= 1000 ms)

```
surah  13  13:22  api_to=589430  -> 591004  delta_to=+1574
surah  13  13:23  api_to=612420  -> 613938  delta_to=+1518
surah  14  14:18  api_to=431390  -> 432846  delta_to=+1456
surah  13  13:20  api_to=543090  -> 544528  delta_to=+1438
surah  14  14:42  api_to=898630  -> 900023  delta_to=+1393
surah  13  13:24  api_to=612420  -> 623035  delta_to=+1395
surah  10  10:92  api_to=2018160 -> 2019469 delta_to=+1309
surah  14  14:34  api_to=753360  -> 754591  delta_to=+1231
surah  14  14:45  api_to=964170  -> 962939  delta_to=-1231
surah  14  14:14  api_to=358650  -> 357449  delta_to=-1201
```

## Caveats

  * WhisperX itself fails on roughly 20 verses out of 6236 (chunk-
    edge CTC compression: usually a long verse gets compressed to a
    fraction of its real audio span). Those show up as `WX_GLITCH`
    flags and the hybrid fix correctly falls back to ffmpeg silence
    in those spots.
  * The ffmpeg silencedetect threshold (-22 dB / 200 ms) is the same
    as the original PoC and analyze_drift_v2 -- chosen to match the
    user-perceptible "voice vs quiet" distinction. Tighter
    thresholds would catch fewer breaths but miss real boundaries.
  * "Verse-count mismatch" between API and canonical text was zero
    across all 114 surahs (good baseline).

## Reproducing

```
.venv/Scripts/python.exe fetch_all.py            # one-time, ~45 s
.venv/Scripts/python.exe batch_align.py          # ~10 min on RTX 4090
.venv/Scripts/python.exe generate_fix_whisperx.py
.venv/Scripts/python.exe detect_shifts.py
.venv/Scripts/python.exe build_demo.py 13 10 14 72
.venv/Scripts/python.exe serve.py                # browse demos
```
