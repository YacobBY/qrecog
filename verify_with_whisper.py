"""
Independent verification of API verse boundaries using Whisper transcription.

Runs Whisper (large-v3, Arabic) on the audio segment that the API claims
is verse N, then compares the transcribed text to canonical verse N's
text. If they don't match, the API span is likely on the wrong audio --
this catches the "whole-sentence shift" bug independently of the
wav2vec2 forced-alignment pass.

Output per verse:
  api_span_text    -- what Whisper transcribed for the API's verse-N span
  match_score      -- character-level similarity 0.0..1.0 vs canonical
                      verse N text (after diacritic stripping)
  best_match_idx   -- which canonical verse the transcribed text best
                      matches (0 = self, +1 = API verse points at next
                      verse's audio = "TOO EARLY" pattern)
  flag             -- "ok" / "low_match" / "shift_+1" / "shift_-1" / etc.

This is independent of CTC alignment so it catches cases where both API
and our WhisperX both got it wrong (Surah 3:46 in Tunaiji).

Slow: ~1s per verse on RTX 4090. Allocate ~1.5h for the full Quran.
"""
import argparse
import gc
import json
import re
import subprocess
import sys
import time
import warnings
from pathlib import Path

from reciter_paths import paths_for, LEGACY_RECITER_ID

warnings.filterwarnings("ignore")
T0 = time.monotonic()


def log(msg):
    print(f"[{time.monotonic()-T0:7.1f}s] {msg}", flush=True)


def fail(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# Same normalization used elsewhere -- diacritic strip + canonical letter
# folding, so Whisper's transcription matches canonical text.
DIACRITICS = re.compile(r"[ً-ْٰۖ-ۭ]")


def normalize(text: str) -> str:
    t = DIACRITICS.sub("", text)
    t = t.replace("ـ", "")
    t = (t.replace("ٱ", "ا").replace("آ", "ا")
          .replace("أ", "ا").replace("إ", "ا")
          .replace("ى", "ي").replace("ة", "ه"))
    # Drop punctuation/whitespace -> bare letter sequence for char-level
    # similarity. Spaces don't matter for the comparison.
    t = re.sub(r"\s+", "", t)
    return t.strip()


def char_sim(a: str, b: str) -> float:
    """Length-normalized longest-common-subsequence ratio."""
    if not a or not b:
        return 0.0
    n, m = len(a), len(b)
    if n > 1000 or m > 1000:
        # Cap length to keep DP cheap. Verses are short (<1000 chars).
        return 0.0
    # LCS DP
    prev = [0] * (m + 1)
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        ai = a[i - 1]
        for j in range(1, m + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
            else:
                cur[j] = max(prev[j], cur[j - 1])
        prev = cur
    lcs = prev[m]
    return (2.0 * lcs) / (n + m)


def transcribe_window(model, audio, sr, start_s, end_s, language="ar"):
    """Transcribe a single audio span via faster-whisper. Returns the
    concatenated text (no per-word timestamps needed for this check)."""
    import numpy as np
    s = max(0, int(start_s * sr))
    e = min(len(audio), int(end_s * sr))
    if e <= s:
        return ""
    chunk = audio[s:e]
    # faster-whisper accepts numpy float32 arrays directly
    segments, _ = model.transcribe(
        chunk.astype(np.float32),
        language=language,
        beam_size=1,         # fast; we don't need beam quality
        condition_on_previous_text=False,
        without_timestamps=True,
        vad_filter=False,
    )
    return " ".join(seg.text for seg in segments)


def verify_surah(surah, model, P, audio_loader, neighbour_window=3,
                 verbose=False):
    """Run verification for one surah. Loads audio once, transcribes
    each API verse's span, compares to canonical."""
    api_path = P.api_json(surah)
    verses_path = P.verses_json(surah)
    audio_path = P.audio_mp3(surah)
    if not api_path.exists() or not verses_path.exists() or not audio_path.exists():
        return None
    api_ts = json.loads(api_path.read_text(encoding="utf-8"))["audio_file"]["timestamps"]
    raw_verses = json.loads(verses_path.read_text(encoding="utf-8"))["verses"]
    if len(api_ts) != len(raw_verses):
        return {"error": f"verse-count mismatch api={len(api_ts)} canonical={len(raw_verses)}"}

    canonical_norm = [normalize(v.get("text_uthmani", "")) for v in raw_verses]
    canonical_keys = [v["verse_key"] for v in raw_verses]

    audio = audio_loader(audio_path)
    sr = 16000
    duration_s = len(audio) / sr

    flags = []
    for i, v in enumerate(api_ts):
        api_from_s = v["timestamp_from"] / 1000.0
        api_to_s = v["timestamp_to"] / 1000.0
        if api_to_s - api_from_s < 0.5:
            continue
        # Pad a bit so we don't clip word edges.
        ts = max(0.0, api_from_s - 0.05)
        te = min(duration_s, api_to_s + 0.05)
        try:
            text = transcribe_window(model, audio, sr, ts, te)
        except Exception as e:
            log(f"  surah {surah} {canonical_keys[i]}: transcribe failed -- {e}")
            continue
        norm_text = normalize(text)

        sim_self = char_sim(norm_text, canonical_norm[i])
        # Compare to neighbour verses for shift detection.
        best_j = i
        best_sim = sim_self
        for dj in range(-neighbour_window, neighbour_window + 1):
            j = i + dj
            if j < 0 or j >= len(canonical_norm) or j == i:
                continue
            s = char_sim(norm_text, canonical_norm[j])
            if s > best_sim:
                best_sim = s
                best_j = j
        offset = best_j - i

        flag = "ok"
        if sim_self < 0.50 and best_sim - sim_self >= 0.20:
            flag = f"shift_{offset:+d}"
        elif sim_self < 0.40:
            flag = "low_match"

        if flag != "ok":
            flags.append({
                "verse_key": canonical_keys[i],
                "api_span_ms": [v["timestamp_from"], v["timestamp_to"]],
                "transcribed_normalized": norm_text[:200],
                "canonical_normalized": canonical_norm[i][:200],
                "sim_self": round(sim_self, 3),
                "best_match_offset": offset,
                "best_match_verse": canonical_keys[best_j],
                "best_match_sim": round(best_sim, 3),
                "flag": flag,
            })
            if verbose:
                print(f"  {canonical_keys[i]}: sim_self={sim_self:.2f} "
                      f"best={canonical_keys[best_j]}({offset:+d})={best_sim:.2f} "
                      f"flag={flag}", flush=True)

    return {"flags": flags, "n_verses": len(api_ts)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("surahs", nargs="*", type=int)
    ap.add_argument("--reciter-id", type=int, default=LEGACY_RECITER_ID)
    ap.add_argument("--model-size", default="large-v3")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    P = paths_for(args.reciter_id)
    targets = args.surahs or list(range(1, 115))
    targets = [s for s in targets if P.api_json(s).exists()]

    log("loading whisper...")
    import torch
    from faster_whisper import WhisperModel
    if not torch.cuda.is_available():
        fail("CUDA unavailable")
    model = WhisperModel(args.model_size, device="cuda", compute_type="float16")
    log(f"loaded {args.model_size}")

    # Audio loader: read with whisperx helper or ffmpeg
    def load_audio(path):
        # use ffmpeg via subprocess to convert to 16k mono float32
        import numpy as np
        cmd = ["ffmpeg", "-loglevel", "error", "-i", str(path),
               "-ar", "16000", "-ac", "1", "-f", "f32le", "-"]
        r = subprocess.run(cmd, capture_output=True, check=True)
        return np.frombuffer(r.stdout, dtype=np.float32)

    out = {}
    for s in targets:
        log(f"surah {s}: verify...")
        try:
            res = verify_surah(s, model, P, load_audio,
                               verbose=args.verbose)
        except Exception as e:
            log(f"  ERROR: {e}")
            continue
        if res is None:
            continue
        if isinstance(res, dict) and "error" in res:
            log(f"  skip: {res['error']}")
            continue
        out[s] = res
        log(f"  {len(res['flags'])} flag(s)")

    suffix = f"_r{args.reciter_id}" if args.reciter_id != LEGACY_RECITER_ID else ""
    out_path = Path(__file__).parent / "reports" / f"whisper_verify{suffix}.json"
    out_path.parent.mkdir(exist_ok=True)
    # Merge with any existing results so partial runs accumulate.
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        existing.update({str(k): v for k, v in out.items()})
        merged = {str(k): v for k, v in existing.items()}
    else:
        merged = {str(k): v for k, v in out.items()}
    out_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    total = sum(len(r["flags"]) for r in out.values())
    log(f"DONE -- {total} new flags across {len(out)} surahs. "
        f"Total in {out_path}: {sum(len(v.get('flags', [])) for v in merged.values())}")


if __name__ == "__main__":
    main()
