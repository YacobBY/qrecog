# Methodology

This document explains *why* the qrfix pipeline is shaped the way it
is, what failure modes each stage catches, and which design decisions
were forced by what we found in the data.

## The bug we're catching

The quran.com API serves per-verse `timestamp_from` and `timestamp_to`
for every (reciter, surah) pair. The frontend uses those numbers to
flip the translation column in sync with the audio. When the
timestamps are off, the user sees the wrong translation while the
audio plays.

Two distinct failure modes show up in the wild:

### A. Boundary drift

The verse identity is right, but the boundary fires too early or too
late by a few hundred ms to a couple of seconds. Worst Tunaiji case:
Surah 13 verses 13-33, where the API verse boundaries fire 0.5-2.5 s
*before* the actual inter-verse silence. Translation flips while
the previous verse's last word is still audibly being recited.

### B. Whole-verse shift

The API span for verse N actually contains the audio of a *different*
verse — usually verse N±1, occasionally N±2. Once a shift starts, it
typically cascades for the rest of the surah until something resyncs.
Worst case found: Sudais Surah 3, where 36 verses (100-186) are mostly
shifted by -1, -2, or -3.

These two modes need different signals to detect. Boundary drift is
caught by silence-based comparison. Whole-verse shifts are caught by
*content* comparison — transcribing the API span and seeing if the
words match the verse the API claims.

## Pipeline overview

```
                                 ┌──────────────────┐
                                 │ quran.com API    │
                                 │ + canonical text │
                                 │ + audio MP3      │
                                 └────────┬─────────┘
                                          │
                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │ 1. fetch              (network, ~45s)                │
       └──────────────────────────────────────────────────────┘
                                          │
                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │ 2. WhisperX align     (GPU, jonatasgrosman wav2vec2) │
       │    canonical text → audio, per-word [start, end, σ]  │
       └──────────────────────────────────────────────────────┘
                                          │
                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │ 3. heal_alignment     (CPU + ffmpeg)                 │
       │    chronological-order constraints,                  │
       │    silence-snap of low-confidence runs               │
       └──────────────────────────────────────────────────────┘
                                          │
                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │ 4. generate_fix_whisperx (CPU + ffmpeg)              │
       │    silence-anchored corrected timestamps             │
       └──────────────────────────────────────────────────────┘
                                          │
                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │ 5. detect_shifts      (CPU)                          │
       │    IoU(API, WX) — STRONG/WEAK/WX_GLITCH              │
       └──────────────────────────────────────────────────────┘
                                          │
                                          ▼
       ┌──────────────────────────────────────────────────────┐
       │ 6. verify_with_whisper (GPU, large-v3 / medium)      │
       │    transcribe API span, char-similarity vs canonical │
       │    catches whole-verse shifts CTC missed             │
       └──────────────────────────────────────────────────────┘
```

## Why these particular choices

### Forced alignment model: `jonatasgrosman/wav2vec2-large-xlsr-53-arabic`

The first attempt used `elgeish/wav2vec2-large-xlsr-53-arabic`. Its
vocabulary is **Buckwalter Latin transliteration**, not Arabic. Feeding
it raw Arabic text means every character is `<unk>`, the CTC trellis
collapses, and the alignment is meaningless. Alternative was to add a
Buckwalter transliteration step, but the jonatasgrosman model uses
**native Arabic chars** including hamza variants and diacritics, so we
just switched models. It's also WhisperX's documented default for
Arabic (`DEFAULT_ALIGN_MODELS_HF["ar"]`).

Tokens are diacritic-stripped before alignment because the model was
trained on undiacriticised broadcast Arabic — emitting a fatha/kasra at
every position would still collapse the posterior even though the
characters are in the vocab.

### Chunking by ≤30 s of audio

Wav2vec2 attention is O(n²) memory in audio length. Surah 2 in slow
mujawwad reciters is ~3 hours of audio; one-shot alignment OOMs even on
a 4090. We chunk at API timestamps (which are imprecise — that's the
bug — but tight enough to land in real silences after ±500 ms padding).

A failure mode to watch for: **chunk-edge CTC compression**. Sometimes
all the words in a chunk get squeezed into the front, leaving the back
of the chunk unaccounted for. We caught one of these in Mishary Surah
2:17. The fill-ratio check in `heal_alignment.py` flags and re-spreads
these.

### Healing pass: chronological-order constraints

Six independent passes:

1. **Monotonicity.** `word[i+1].start ≥ word[i].end`. CTC sometimes
   emits overlaps when uncertain; snap to midpoint.
2. **Anchor + interpolate.** Words with WX score < 0.55 between two
   anchors (score ≥ 0.70) get re-positioned in the anchor window
   weighted by character count.
3. **Silence-snap.** When ffmpeg silence detection finds a real silence
   inside a low-confidence run, use the silence boundary as the
   inter-word gap. Much higher precision than character-count interp.
4. **Density outliers.** Flag words whose ms-per-character is wildly
   outside the verse median (>3x or <1/3x).
5. **Verse continuity.** verse N's last word ends ≥ 50 ms before
   verse N+1's first word starts.
6. **Fill ratio.** If aligned-words span < 60 % of the verse's API span
   AND the score is reasonable, re-distribute words across the API
   span.

Every healed word records which passes touched it under
`words[i].healed_by`, so any decision can be audited.

### Hybrid fix generator

Combines two signals:

- **ffmpeg silencedetect** (-22 dB / 100 ms minimum) to find the
  actual inter-verse silences in the audio.
- **WhisperX next-word start** for where the next verse audibly begins.

For each API verse boundary:

```text
if API boundary is INSIDE the inter-verse silence:
    leave alone  (translation flip happens during quiet — invisible)

if API boundary is LATE (> silence_end + LATE_PAD_MS):
    snap to silence_end - SAFETY_MS
    (subtitle flips just before next voice resumes)

if API boundary is EARLY (< silence_start - EARLY_PAD_MS):
    snap to silence_start + SAFETY_MS

guard: if WhisperX target disagrees with API by > MAX_TRUST_DELTA_MS:
    distrust WX (probably a CTC alignment failure)
guard: if no ffmpeg silence within MAX_MATCH_MS of the API boundary:
    can't anchor confidently, leave alone
```

`EARLY_PAD_MS = 250` and `LATE_PAD_MS = 50` are deliberately
asymmetric — LATE drift (subtitle lingers into next verse audio) is
acutely perceptible even at 100 ms, while EARLY drift in the
vowel-decay zone right after a verse ends is essentially invisible.

### Why we need a second detector

The IoU detector (`detect_shifts.py`) compares API spans to *our
WhisperX* spans. It's the natural first thing to try, and it catches
the shifts that WX agrees with. But WhisperX itself fails on the same
verses where the API is most broken — the alignment is anchored to
text, and broken API timestamps produce broken WX chunk boundaries
which produce broken WX alignment. When both are wrong, IoU
comparisons go to zero and we can't tell who's at fault.

The Whisper-verify step uses an **independent acoustic signal**: open-
domain transcription, no canonical text given, then character-
similarity comparison to every nearby verse's canonical text. If the
API claims verse N's audio, and Whisper transcribes it to something
that matches verse N+1's canonical text with similarity 0.85, the API
is wrong by exactly one verse — high confidence, no CTC-failure
ambiguity.

This is the single most reliable signal in the pipeline. The CTC-side
detector is supplementary.

### Why we care about character similarity, not BLEU/WER

For shift detection we don't care about transcription quality, only
about *which canonical text* the audio matches best. Character-level
longest common subsequence (length-normalised) is robust to small
Whisper transcription errors and to different normalisation of
diacritics, while still being sensitive to verse identity.

Threshold of 0.70 was picked empirically: ≥ 0.70 vs a non-self verse
has zero false positives in the verses I manually verified. ≥ 0.85
catches the high-confidence shifts; everything between is "WX glitch
or partial drift" territory and gets surfaced as `low_match` for human
review.

## Failure modes and mitigations

| Failure | Where it shows up | Mitigation |
|---------|-------------------|------------|
| Buckwalter-vocab CTC collapse | Surah 1 alignment compressed to 24 s in early prototype | Switched model to jonatasgrosman |
| Chunk-edge CTC compression | Surah 2:17 alignment 6 s wrong | `heal_alignment.fill_ratio_check` |
| WhisperX failed on whole verse | Surah 3:46 (low score throughout) | Score-gated: WX_GLITCH bucket, no claim made |
| Both API and WX wrong | Same surah/verse | Whisper-verify cross-check (independent signal) |
| Intra-verse breath misclassed | False inter-verse boundary | `MIN_SILENCE_LEN_MS = 100` filter; varies by reciter |
| API drift > MAX_TRUST_DELTA_MS | Tunaiji surah 13 v17-20 (drift 1.7-1.9s) | Raised threshold from 1500 → 2500 |
| First-verse left edge | Subtitle should start at 0 ms | Special-cased: never extend before audio start |
| Last-verse right edge | Subtitle should stay until audio ends | Special-cased: never shrink to last_word.end |

## Open questions

- **How to detect partial-overlap drift automatically.** When the API
  boundary lands in the middle of speech (~1.5 s away from a real
  silence), the API span is mostly the right verse plus a tail of the
  previous one. Whisper-verify doesn't reliably flag these because
  similarity to the claimed verse stays moderate. Currently caught by
  the fix generator (silence-anchored), but not surfaced as a separate
  diagnostic.
- **Reciter-specific pacing.** Husary mujawwad has 1 s+ inter-verse
  pauses in places, while Tunaiji murattal sometimes has 130 ms breaths
  that *are* inter-verse boundaries. The MIN_SILENCE_DUR threshold has
  to flex per reciter; currently a single global value.
- **Audio-only confirmation that doesn't require the user to listen.**
  Could compare the corrected boundary to a high-quality VAD
  (pyannote, Silero) for an independent third signal. Not yet
  implemented.
