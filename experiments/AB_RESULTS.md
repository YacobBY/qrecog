# A/B test: candidate Whisper models for the verify step

> 📎 **Per-case clickable evidence (audio span + quran.com pages with reciter
> preselected):** [`AB_VERIFICATION.md`](AB_VERIFICATION.md) — auto-generated
> from `ab_results.json` by `annotate_results.py`.

## Setup

- **Test set**: 33 hand-curated Mishary al-Afasy verses across surahs 37,
  78, 82.
  - 15 confirmed shifts (7 user-audibly-confirmed in surah 82 plus
    high-confidence cases from `reports/whisper_verify_r7.json`).
  - 18 clean controls (pre-shift verses in the same surahs).
- **Threshold**: 0.70 character-similarity vs a neighbour verse (same as
  production).
- **Hardware**: RTX 4090 + CUDA 13.x, fp16.
- **Harness**: `experiments/ab_test_models.py`.

## Results

| model                | TP | FN | FP | TN | precision | recall |   F1 | avg_best on shifts | avg_self on clean | avg latency (s/verse) |
|----------------------|---:|---:|---:|---:|----------:|-------:|-----:|-------------------:|------------------:|----------------------:|
| **baseline-large-v3**|  11|   4|   1|  17|     0.917 |  0.733 | 0.815|              0.809 |             0.884 |                  0.151 |
| turbo-large-v3       |   9|   6|   0|  18|     1.000 |  0.600 | 0.750|              0.710 |             0.872 |                  0.080 |
| tarteel-base-quran   |  10|   5|   0|  18|     1.000 |  0.667 | 0.800|          **0.854** |             0.877 |                  0.528 |

## Per-case best-match similarity

(`±N@x.yy` = best-match offset and similarity. Bold = above 0.70 threshold.)

All verse links open quran.com with Mishary al-Afasy (id 7) preselected.
For audio span links per case (clicking plays exactly the disputed slice
in your browser), see [`AB_VERIFICATION.md`](AB_VERIFICATION.md).

| verse | true | baseline | turbo | tarteel | notes |
|-------|------|----------|-------|---------|-------|
| [82:9](https://quran.com/82/9?reciter=7)     | shift | +2@0.43       | -1@0.51       | -1@0.67       | very short verse ("كَلَّا...") — all miss |
| [82:10](https://quran.com/82/10?reciter=7)   | shift | **-1@0.90**   | **-1@0.90**   | **-1@1.00**   | tarteel strongest                        |
| [82:11](https://quran.com/82/11?reciter=7)   | shift | **-1@0.97**   | **-1@0.97**   | **-1@0.97**   | tied                                     |
| [82:12](https://quran.com/82/12?reciter=7)   | shift | -1@0.67       | -1@0.67       | -1@0.67       | short verse ("كِرَامًا") — all miss        |
| [82:13](https://quran.com/82/13?reciter=7)   | shift | **-1@0.82**   | **-1@0.82**   | -1@0.62       | tarteel REGRESSES                        |
| [82:14](https://quran.com/82/14?reciter=7)   | clean | -1@0.72 ✗FP   | -1@0.67       | -1@0.56       | **tarteel kills the only baseline FP**   |
| [82:16](https://quran.com/82/16?reciter=7)   | shift | **-2@0.97**   | **-2@0.89**   | **-2@0.97**   |                                          |
| [82:19](https://quran.com/82/19?reciter=7)   | shift | **-1@0.92**   | -2@0.47       | -1@0.66       | turbo gets the offset wrong              |
| [37:109](https://quran.com/37/109?reciter=7) | shift | **+1@1.00**   | +0@0.00       | **+1@1.00**   | turbo emits empty transcription          |
| [37:127](https://quran.com/37/127?reciter=7) | shift | **+1@0.92**   | -1@0.20       | **+1@0.94**   | turbo wrong direction                    |
| [37:128](https://quran.com/37/128?reciter=7) | shift | **+1@0.90**   | **+1@0.95**   | **+1@0.97**   | tarteel strongest                        |
| [37:139](https://quran.com/37/139?reciter=7) | shift | **+1@1.00**   | **+1@1.00**   | **+1@0.87**   |                                          |
| [37:140](https://quran.com/37/140?reciter=7) | shift | **+1@1.00**   | **+1@0.93**   | **+1@1.00**   |                                          |
| [37:141](https://quran.com/37/141?reciter=7) | shift | **+1@0.95**   | **+1@0.95**   | **+1@1.00**   |                                          |
| [78:7](https://quran.com/78/7?reciter=7)     | shift | -2@0.39       | **-1@0.77**   | **-1@0.80**   | **only turbo & tarteel catch this!**     |
| [78:22](https://quran.com/78/22?reciter=7)   | shift | -1@0.30       | -1@0.62       | -1@0.67       | tarteel closest, just under threshold    |

(Clean cases all classified correctly across all models except 82:14.)

## What the numbers say

### Turbo (large-v3-turbo): NOT a clear win

My original recommendation said "negligible accuracy loss" — the data
disagrees. On this set turbo:

- ✓ **2× faster** than baseline (0.08 s vs 0.15 s per verse)
- ✓ Eliminated baseline's one false positive on 82:14
- ✓ Caught 78:7 that baseline missed
- ✗ Lost 4 cases baseline catches (37:109 emitted empty text, 37:127 got
  the offset direction wrong, 82:19 misidentified the offset, 82:13 fine
  but 82:9/12 marginally worse)
- ✗ Net recall: 60% vs baseline 73%

Verdict: **turbo is a speed-for-recall trade, not a free win**. Worth
keeping for fast initial sweeps but not as the primary signal.

### Tarteel-base-quran: precision win, recall sideways

- ✓ **Zero false positives** (vs baseline's 1)
- ✓ **Highest avg best-sim on true shifts (0.854)** — when it's right,
  it's *very* right. Cases like 82:10 jump from 0.90 → 1.00, 37:128 from
  0.90 → 0.97, 37:141 from 0.95 → 1.00.
- ✓ Caught 78:7 that baseline missed (-1@0.80) — same as turbo
- ✗ Lost 82:13 (regressed from 0.82 → 0.62)
- ✗ Recall 67% vs baseline 73%
- ✗ Currently 3.5× slower than baseline. **This is a tooling artefact**:
  the test runs the un-optimised HF transformers checkpoint. Converting
  to CTranslate2 (`ct2-transformers-converter --model
  tarteel-ai/whisper-base-ar-quran ...`) and loading via faster-whisper
  would close the gap and likely make it the fastest of the three (it's
  a *base* model, ~140 MB).

The most interesting Tarteel signal is qualitative: on 78:22 it pushed
the best-match similarity from baseline's 0.30 (totally lost) to 0.67
(just barely under threshold). That's the right kind of failure — close
enough that a slightly different aggregation rule would catch it.

### The cases nobody catches — short verses

82:9 and 82:12 are missed by all three models. Both are very short
verses ("كَلَّا بَلْ تُكَذِّبُونَ بِٱلدِّينِ" / "كِرَامًا كَاتِبِينَ"). The audio span the
API claims is short, the canonical text is short, and char-LCS between
two short strings is fragile.

This is **not a model problem** — the verify step needs widening: pad
the API span by ±300 ms before transcription, or compare against the
2-verse window (N-1 + N) when the verse is short.

## Recommendation

The single test that would clearly improve precision *and* recall is
**ensemble baseline + tarteel** with `max(best_sim)` aggregation:

- Baseline catches: 11
- + tarteel catches that baseline missed (78:7): 12
- 82:14 baseline FP: still triggered by baseline's 0.72; need
  agreement rule (require both models above threshold OR baseline above
  + tarteel-margin > 0.10) to suppress

Estimated ensemble F1: ~0.86 vs baseline 0.815, with same FP count if
agreement rule applied (or slightly higher recall, same FP, with
max-agg).

Cost: 2× compute, but if the Tarteel checkpoint is ct2-converted that
becomes ~1.3× total wall-time vs baseline.

## Caveats

- **n=33** is too small to draw strong conclusions. F1 differences of
  0.05 are within noise. A real evaluation needs ~200 cases stratified
  across reciters (Sudais, Tunaiji, AbdulBaset).
- Test set is Mishary-only. Tarteel models may behave very differently
  on Sudais (mujawwad, slow), Husary (mujawwad, very slow), or AbdulBaset
  (alt mujawwad).
- A larger Tarteel checkpoint (`whisper-medium-ar-quran` / `whisper-
  large-v3-ar-quran` if/when published) is the obvious next test.

## Reproducing

```bash
# All three models
.venv/Scripts/python.exe experiments/ab_test_models.py

# Re-run a specific model only (results merged into ab_results.json)
.venv/Scripts/python.exe experiments/ab_test_models.py --models turbo-large-v3
```

Outputs: `experiments/ab_results.json` (raw per-case + summaries),
console table.
