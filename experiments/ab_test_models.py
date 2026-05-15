"""
A/B test of candidate Whisper models for the verse-shift verify step.

Compares three models on a hand-curated ground-truth set of Mishary
al-Afasy verses (reciter id 7) for which we already know the right
answer. The audio (audibly verified by the user for surah 82) is the
arbiter; the existing Whisper-large-v3 reports are not.

Models compared
---------------
1. baseline           openai/whisper-large-v3          (current pipeline default)
2. turbo              openai/whisper-large-v3-turbo    (Sep-2024, ~4x faster)
3. tarteel-base       tarteel-ai/whisper-base-ar-quran (Quran-fine-tuned, tiny)

Metrics
-------
For each model, on each test case:
  - sim_self        : char-similarity of transcribed text vs the verse
                      the API claims is being recited (high = model agrees
                      with API claim)
  - best_match_sim  : char-similarity vs the best-matching neighbour verse
                      (the verse the audio actually contains, for shifts)
  - best_offset     : verse index of best match minus claimed verse index
  - latency_s       : seconds per transcribe call

Then aggregated:
  - confusion matrix at threshold 0.70 (predicted-shift vs true-shift)
  - mean best_match_sim on true-shifts (recall proxy: higher = stronger
    detection signal)
  - mean sim_self on true-clean verses (precision proxy: higher = model
    confirms clean cases more strongly, less likely to wobble below
    threshold)
  - throughput

Output: experiments/ab_results.json + a markdown table on stdout.

Run:
    .venv/Scripts/python.exe experiments/ab_test_models.py
"""
from __future__ import annotations

import gc
import io
import json
import re
import subprocess
import sys
import time

# Force UTF-8 stdout on Windows so Arabic text + table headers don't
# trip cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from dataclasses import dataclass, asdict
from pathlib import Path

# Make the parent dir importable so we can reuse normalize/char_sim
sys.path.insert(0, str(Path(__file__).parent.parent))
from verify_with_whisper import normalize, char_sim  # noqa: E402
from reciter_paths import paths_for  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT_PATH = Path(__file__).parent / "ab_results.json"

# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------
# Each entry is (reciter_id, surah, verse_idx_1based, true_label,
#                expected_offset_or_None, note).
#
# true_label: "shift" | "clean"
# expected_offset: for shifts, what offset the audio actually has
#                  (e.g. -1 means audio actually plays the previous verse).
#
# Sources:
#   * Mishary 82:9-13, 16, 19  -- user audibly confirmed (see
#                                 reports/mishary_findings.md and the
#                                 demo player). These are the gold cases.
#   * Mishary 82:1-7, 14       -- "clean" controls: pre-shift verses in
#                                 the same surah that no detector has
#                                 ever flagged.
#   * Mishary 37:109,127,128,
#         139,140,141          -- high-confidence shifts (>=0.85 best-sim
#                                 in current report; consistent +1 offset
#                                 across the cluster).
#   * Mishary 37:1-5           -- "clean" controls early in surah 37.
#   * Mishary 78:7,22          -- shift cases from mishary_findings.md.
#   * Mishary 78:1-5           -- "clean" controls.
GROUND_TRUTH = [
    # --- Surah 82: confirmed shifts (audibly verified by user) ---
    (7, 82,  9, "shift", -1, "user-confirmed: audio plays 82:8 tail"),
    (7, 82, 10, "shift", -1, "user-confirmed: audio plays 82:9"),
    (7, 82, 11, "shift", -1, "user-confirmed: audio plays 82:10"),
    (7, 82, 12, "shift", -1, "user-confirmed: audio plays 82:11 head"),
    (7, 82, 13, "shift", -1, "user-confirmed: audio plays 82:12"),
    (7, 82, 16, "shift", -2, "user-confirmed: audio plays 82:14"),
    (7, 82, 19, "shift", -1, "user-confirmed: audio plays 82:18"),
    # --- Surah 82: clean controls ---
    (7, 82,  1, "clean", None, "pre-shift control"),
    (7, 82,  2, "clean", None, "pre-shift control"),
    (7, 82,  3, "clean", None, "pre-shift control"),
    (7, 82,  4, "clean", None, "pre-shift control"),
    (7, 82,  5, "clean", None, "pre-shift control"),
    (7, 82,  6, "clean", None, "pre-shift control"),
    (7, 82,  7, "clean", None, "pre-shift control"),
    (7, 82, 14, "clean", None, "between shifts (16 is shifted, 14/15 are clean)"),
    # --- Surah 37: high-confidence cluster shifts ---
    (7, 37, 109, "shift", +1, "report sim=0.97 vs 37:110"),
    (7, 37, 127, "shift", +1, "report sim=0.92 vs 37:128"),
    (7, 37, 128, "shift", +1, "report sim=0.90 vs 37:129"),
    (7, 37, 139, "shift", +1, "report sim=1.00 vs 37:140"),
    (7, 37, 140, "shift", +1, "report sim=0.90 vs 37:141"),
    (7, 37, 141, "shift", +1, "report sim=1.00 vs 37:142"),
    # --- Surah 37: clean controls ---
    (7, 37,  1, "clean", None, "early-surah control"),
    (7, 37,  2, "clean", None, "early-surah control"),
    (7, 37,  3, "clean", None, "early-surah control"),
    (7, 37,  4, "clean", None, "early-surah control"),
    (7, 37,  5, "clean", None, "early-surah control"),
    # --- Surah 78: smaller findings ---
    (7, 78,  7, "shift", -1, "report sim=0.84 vs 78:6"),
    (7, 78, 22, "shift", -1, "report sim=0.69 vs 78:21"),
    (7, 78,  1, "clean", None, "control"),
    (7, 78,  2, "clean", None, "control"),
    (7, 78,  3, "clean", None, "control"),
    (7, 78,  4, "clean", None, "control"),
    (7, 78,  5, "clean", None, "control"),
]

THRESHOLD = 0.70  # same as the production verify pass

# ---------------------------------------------------------------------------
# Audio loading (same approach as verify_with_whisper.py)
# ---------------------------------------------------------------------------
SR = 16000


def load_audio(path: Path):
    import numpy as np
    cmd = ["ffmpeg", "-loglevel", "error", "-i", str(path),
           "-ar", str(SR), "-ac", "1", "-f", "f32le", "-"]
    r = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32)


# ---------------------------------------------------------------------------
# URL builders for human verification
# ---------------------------------------------------------------------------
def quran_com_url(surah: int, verse: int, reciter_id: int) -> str:
    """Verse page on quran.com, with the chosen reciter selected.
    Frontend honours `?reciter=<id>` to preselect the audio voice."""
    return f"https://quran.com/{surah}/{verse}?reciter={reciter_id}"


def audio_span_url(audio_url: str, start_s: float, end_s: float) -> str:
    """HTML5 media-fragment URL: clicking plays exactly start..end of
    the mp3. Works in Chrome / Firefox / Safari without any player
    state."""
    return f"{audio_url}#t={start_s:.2f},{end_s:.2f}"


# ---------------------------------------------------------------------------
# Model wrappers
# ---------------------------------------------------------------------------
class FasterWhisperModel:
    """Wraps faster-whisper for openai/whisper-large-v3 and turbo."""
    def __init__(self, model_size: str):
        from faster_whisper import WhisperModel
        self.name = model_size
        self.model = WhisperModel(model_size, device="cuda",
                                  compute_type="float16")

    def transcribe(self, audio_chunk) -> str:
        import numpy as np
        segments, _ = self.model.transcribe(
            audio_chunk.astype(np.float32),
            language="ar",
            beam_size=1,
            condition_on_previous_text=False,
            without_timestamps=True,
            vad_filter=False,
        )
        return " ".join(seg.text for seg in segments)

    def close(self):
        del self.model
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass


class HFWhisperModel:
    """Wraps HuggingFace transformers for tarteel-ai/* and similar."""
    def __init__(self, model_id: str):
        import torch
        from transformers import (AutoProcessor,
                                  AutoModelForSpeechSeq2Seq)
        self.name = model_id
        self.device = "cuda"
        self.dtype = torch.float16
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, torch_dtype=self.dtype
        ).to(self.device).eval()
        # Tarteel/Quran-fine-tuned Whisper checkpoints are monolingual
        # (Arabic baked in). Their generation_config typically lacks the
        # lang_to_id table, so trying to set language="ar" makes
        # generate() crash. Only set language if the table is present
        # (i.e. an unmodified multilingual Whisper).
        gc_obj = self.model.generation_config
        try:
            gc_obj.forced_decoder_ids = None
        except Exception:
            pass
        if getattr(gc_obj, "lang_to_id", None):
            try:
                gc_obj.language = "ar"
                gc_obj.task = "transcribe"
            except Exception:
                pass

    def transcribe(self, audio_chunk) -> str:
        import torch
        inputs = self.processor(
            audio_chunk, sampling_rate=SR, return_tensors="pt"
        )
        feat = inputs.input_features.to(self.device, dtype=self.dtype)
        with torch.no_grad():
            ids = self.model.generate(
                feat, max_new_tokens=256, num_beams=1)
        text = self.processor.batch_decode(ids, skip_special_tokens=True)
        return text[0] if text else ""

    def close(self):
        del self.model
        del self.processor
        gc.collect()
        try:
            import torch
            torch.cuda.empty_cache()
        except Exception:
            pass


MODELS = [
    ("baseline-large-v3",  "fw", "large-v3"),
    ("turbo-large-v3",     "fw", "large-v3-turbo"),
    ("tarteel-base-quran", "hf", "tarteel-ai/whisper-base-ar-quran"),
]


def load_model(kind, ident):
    if kind == "fw":
        return FasterWhisperModel(ident)
    elif kind == "hf":
        return HFWhisperModel(ident)
    raise ValueError(kind)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------
@dataclass
class CaseResult:
    reciter_id: int
    surah: int
    verse: int
    true_label: str          # "shift" or "clean"
    expected_offset: int | None
    transcribed: str
    sim_self: float
    best_offset: int
    best_sim: float
    latency_s: float
    audio_span_s: float
    # Verification links so anyone reading the JSON can audit a case
    # without re-running the pipeline.
    quran_com_claimed: str = ""    # the verse the API claims is playing
    quran_com_actual: str = ""     # the verse Whisper says is actually playing
                                   # (only set when best_offset != 0)
    audio_span_url: str = ""       # mp3 with HTML5 #t= fragment for direct playback

    def predicted_shift(self, threshold: float) -> bool:
        return (self.best_offset != 0
                and self.best_sim >= threshold
                and (self.best_sim - self.sim_self) >= 0.20)


def gather_canonical(reciter_id, surah, neighbour_window=3):
    """Returns (canonical_norm_list, api_ts_list, audio_path, audio_url)."""
    P = paths_for(reciter_id)
    api = json.loads(P.api_json(surah).read_text(encoding="utf-8"))
    verses = json.loads(P.verses_json(surah).read_text(encoding="utf-8"))
    ts = api["audio_file"]["timestamps"]
    canonical = [normalize(v.get("text_uthmani", "")) for v in verses["verses"]]
    audio_url = api.get("audio_file", {}).get("audio_url", "")
    return canonical, ts, P.audio_mp3(surah), audio_url


def run_one_model(label, kind, ident, ground_truth):
    print(f"\n=== {label} ({ident}) ===", flush=True)
    t_load = time.monotonic()
    model = load_model(kind, ident)
    print(f"  loaded in {time.monotonic()-t_load:.1f}s", flush=True)

    # Cache audio + canonical per (reciter, surah) so we don't re-decode
    # the same MP3 30 times.
    audio_cache = {}
    cano_cache = {}
    url_cache = {}

    results = []
    for (rid, surah, verse, true_label, off, _note) in ground_truth:
        key = (rid, surah)
        if key not in cano_cache:
            cano, ts, audio_path, audio_url = gather_canonical(rid, surah)
            cano_cache[key] = (cano, ts)
            audio_cache[key] = load_audio(audio_path)
            url_cache[key] = audio_url
        canonical, ts = cano_cache[key]
        audio = audio_cache[key]
        audio_url = url_cache[key]

        v = ts[verse - 1]   # 1-indexed -> 0-indexed
        s_s = max(0.0, v["timestamp_from"]/1000.0 - 0.05)
        e_s = min(len(audio)/SR, v["timestamp_to"]/1000.0 + 0.05)
        chunk = audio[int(s_s*SR):int(e_s*SR)]

        t0 = time.monotonic()
        try:
            text = model.transcribe(chunk)
        except Exception as e:
            print(f"  ! {rid}/{surah}:{verse} transcribe failed: {e}",
                  flush=True)
            text = ""
        latency = time.monotonic() - t0

        norm = normalize(text)
        i0 = verse - 1
        sim_self = char_sim(norm, canonical[i0])
        best_j = i0
        best_sim = sim_self
        for dj in range(-3, 4):
            j = i0 + dj
            if j < 0 or j >= len(canonical) or j == i0:
                continue
            s = char_sim(norm, canonical[j])
            if s > best_sim:
                best_sim = s
                best_j = j
        offset = best_j - i0

        actual_verse = verse + offset  # 1-indexed within surah
        cr = CaseResult(
            reciter_id=rid, surah=surah, verse=verse,
            true_label=true_label, expected_offset=off,
            transcribed=text.strip()[:120],
            sim_self=round(sim_self, 3),
            best_offset=offset,
            best_sim=round(best_sim, 3),
            latency_s=round(latency, 3),
            audio_span_s=round(e_s - s_s, 3),
            quran_com_claimed=quran_com_url(surah, verse, rid),
            quran_com_actual=(quran_com_url(surah, actual_verse, rid)
                              if offset != 0 else ""),
            audio_span_url=(audio_span_url(audio_url, s_s, e_s)
                            if audio_url else ""),
        )
        results.append(cr)
        marker = "shift" if cr.predicted_shift(THRESHOLD) else "clean"
        ok = "OK " if marker == true_label else "MISS"
        print(f"  {ok}  r{rid}/{surah}:{verse:>3}  true={true_label:<5} "
              f"pred={marker:<5} sim_self={sim_self:.2f} "
              f"best={offset:+d}@{best_sim:.2f}  ({latency:.2f}s)",
              flush=True)

    model.close()
    return results


def aggregate(label, results, threshold=THRESHOLD):
    n_total = len(results)
    n_shift_true  = sum(1 for r in results if r.true_label == "shift")
    n_clean_true  = sum(1 for r in results if r.true_label == "clean")

    tp = sum(1 for r in results
             if r.true_label == "shift" and r.predicted_shift(threshold))
    fn = sum(1 for r in results
             if r.true_label == "shift" and not r.predicted_shift(threshold))
    fp = sum(1 for r in results
             if r.true_label == "clean" and r.predicted_shift(threshold))
    tn = sum(1 for r in results
             if r.true_label == "clean" and not r.predicted_shift(threshold))

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2*precision*recall/(precision+recall)) if (precision+recall) else 0.0

    mean_best_on_shifts = (
        sum(r.best_sim for r in results if r.true_label == "shift")
        / max(1, n_shift_true)
    )
    mean_self_on_clean = (
        sum(r.sim_self for r in results if r.true_label == "clean")
        / max(1, n_clean_true)
    )
    # Offset agreement: of TPs, how many also got the offset direction right
    offset_correct = sum(
        1 for r in results
        if r.true_label == "shift" and r.predicted_shift(threshold)
        and r.expected_offset is not None
        and r.best_offset == r.expected_offset
    )
    total_latency = sum(r.latency_s for r in results)

    return {
        "label": label,
        "n_total": n_total,
        "n_shift_true": n_shift_true,
        "n_clean_true": n_clean_true,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "offset_correct_of_tp": offset_correct,
        "mean_best_sim_on_shifts": round(mean_best_on_shifts, 3),
        "mean_self_sim_on_clean":  round(mean_self_on_clean, 3),
        "total_latency_s": round(total_latency, 2),
        "mean_latency_s": round(total_latency / max(1, n_total), 3),
    }


def print_summary(summaries):
    print("\n" + "=" * 70)
    print("SUMMARY  (threshold = %.2f, %d test cases)" %
          (THRESHOLD, summaries[0]["n_total"]))
    print("=" * 70)
    cols = [
        ("model", 22, "label"),
        ("TP", 4, "tp"),
        ("FN", 4, "fn"),
        ("FP", 4, "fp"),
        ("TN", 4, "tn"),
        ("prec", 6, "precision"),
        ("rec",  6, "recall"),
        ("F1",   6, "f1"),
        ("off-ok", 7, "offset_correct_of_tp"),
        ("avg_best|shift", 14, "mean_best_sim_on_shifts"),
        ("avg_self|clean", 14, "mean_self_sim_on_clean"),
        ("avg_lat(s)", 11, "mean_latency_s"),
    ]
    header = " ".join(f"{name:>{w}}" for name, w, _ in cols)
    print(header)
    print("-" * len(header))
    for s in summaries:
        row = " ".join(
            f"{s[k]:>{w}}" if not isinstance(s[k], float)
            else f"{s[k]:>{w}.3f}"
            for _, w, k in cols
        )
        print(row)
    print()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*",
                    help="Only run these model labels "
                         "(default: all). Existing JSON results for "
                         "untouched models are merged forward.")
    args = ap.parse_args()

    print(f"Test set: {len(GROUND_TRUTH)} cases "
          f"({sum(1 for x in GROUND_TRUTH if x[3]=='shift')} shifts, "
          f"{sum(1 for x in GROUND_TRUTH if x[3]=='clean')} clean)")

    # If we're only re-running a subset, seed from existing JSON so the
    # other models' previous results survive.
    all_summaries = []
    all_raw = {}
    if args.models and OUT_PATH.exists():
        prev = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        for s in prev.get("summaries", []):
            if s["label"] not in args.models:
                all_summaries.append(s)
        for k, v in prev.get("raw", {}).items():
            if k not in args.models:
                all_raw[k] = v

    selected = MODELS if not args.models else [
        m for m in MODELS if m[0] in args.models
    ]
    for label, kind, ident in selected:
        try:
            results = run_one_model(label, kind, ident, GROUND_TRUTH)
        except Exception as e:
            print(f"!! model {label} failed to load/run: {e}", flush=True)
            continue
        s = aggregate(label, results)
        all_summaries.append(s)
        all_raw[label] = [asdict(r) for r in results]
        # Persist after each model so a crash doesn't lose work.
        OUT_PATH.write_text(
            json.dumps({"summaries": all_summaries, "raw": all_raw,
                        "threshold": THRESHOLD},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            print_summary(all_summaries)
        except Exception as e:
            print(f"  (print_summary failed: {e}; results saved to "
                  f"{OUT_PATH})", flush=True)

    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
