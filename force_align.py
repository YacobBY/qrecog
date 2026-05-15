"""
Per-verse forced alignment of Khalifah Al Tunaiji recitation to canonical
Quran text using whisperx.align with a wav2vec2 Arabic CTC model.

Model choice
------------
Default: jonatasgrosman/wav2vec2-large-xlsr-53-arabic. This is whisperx's
documented default for Arabic and uses native Arabic characters in its
vocab (28 letters + hamza variants + diacritics + ta marbuta). The
previously-tried elgeish/wav2vec2-large-xlsr-53-arabic uses Buckwalter
Latin transliteration, so feeding raw Arabic produced an all-<unk> trellis
that collapsed the alignment. Switching models avoids the transliteration
round-trip entirely and is reversibly close to vanilla whisperx behavior.

Tokens fed to the aligner are diacritic-stripped: the model wasn't trained
on harakat, so requiring it to emit fatha/kasra at every position destroys
the CTC posterior even though those characters exist in the vocab.

Strategy
--------
1. For each verse, compute a rough audio window using silencedetect:
   window_from = (silence_end of previous inter-verse gap) - GUARD_MS
   window_to   = (silence_start of next inter-verse gap)   + GUARD_MS
   Falls back to the API-published timestamps if no silence is found nearby.
2. Pass each verse as its own segment to whisperx.align with:
     - start = window_from / 1000
     - end   = window_to   / 1000
     - text  = canonical text_uthmani for that verse, normalized
3. Get per-word [start, end, score] strictly within the verse window.
4. Per-verse fixed boundary = (first word's start) ... (last word's end).

This avoids feeding the alignment model 46 s of audio against 29 words,
which made it collapse everything into the first half.

Usage:
    python force_align.py <surah>

Outputs:
    data/whisperx/surah_<N>_force_v2.json  per-verse word timings
    data/corrected_v2/surah_<N>_*           same shape as the silence-only fix
"""
import argparse
import gc
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from reciter_paths import paths_for, LEGACY_RECITER_ID

T0 = time.monotonic()
ROOT = Path(__file__).parent
# Legacy module-level constants point at Tunaiji's flat layout.
# All actual I/O goes through the per-reciter `P` argument passed to
# the helper functions, so the same code serves any reciter.
_LEGACY_P = paths_for(LEGACY_RECITER_ID)
DATA = _LEGACY_P.data_dir
AUDIO = _LEGACY_P.audio_dir
OUT = _LEGACY_P.wx_dir

CHUNK_TARGET_S = 30.0   # close a chunk once accumulated verse audio exceeds this
CHUNK_PAD_MS = 500      # pad each chunk on both sides so we don't clip a word


def log(msg):
    print(f"[{time.monotonic()-T0:7.1f}s] {msg}", flush=True)


def fail(msg, code=1):
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


# Arabic normalization for wav2vec2 dictionary matching
DIACRITICS = re.compile(r"[ً-ْٰۖ-ۭ]")
TATWEEL = "ـ"


def normalize(word: str) -> str:
    w = DIACRITICS.sub("", word)
    w = w.replace(TATWEEL, "")
    w = (w.replace("ٱ", "ا")
          .replace("آ", "ا")
          .replace("أ", "ا")
          .replace("إ", "ا")
          .replace("ى", "ي")
          .replace("ة", "ه"))
    return w.strip()


def ensure_16k_mono_wav(input_path: Path) -> Path:
    if shutil.which("ffmpeg") is None:
        fail("ffmpeg not found")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate,channels",
         "-of", "default=nw=1:nk=0", str(input_path)],
        capture_output=True, text=True)
    info = dict(line.split("=", 1) for line in probe.stdout.splitlines() if "=" in line)
    if (input_path.suffix.lower() == ".wav"
            and info.get("codec_name") == "pcm_s16le"
            and info.get("sample_rate") == "16000"
            and info.get("channels") == "1"):
        return input_path
    out = input_path.with_suffix(".16k.wav")
    if not out.exists():
        log(f"converting {input_path.name} -> {out.name} (16 kHz mono)...")
        subprocess.run(["ffmpeg", "-y", "-i", str(input_path),
                        "-ar", "16000", "-ac", "1", str(out)],
                       capture_output=True, check=True)
    return out


def load_verses(surah: int, P=None):
    P = P or _LEGACY_P
    p = P.verses_json(surah)
    if not p.exists():
        url = (f"https://api.quran.com/api/v4/verses/by_chapter/{surah}"
               f"?translations=20&fields=text_uthmani&words=false&per_page=500")
        subprocess.run(["curl", "-sS", url, "-o", str(p)], check=True)
    raw = json.loads(p.read_text(encoding="utf-8"))["verses"]
    return [{"verse_key": v["verse_key"],
             "words": [w for w in v.get("text_uthmani", "").split() if w.strip()]}
            for v in raw]


def load_api_timestamps(surah: int, P=None):
    P = P or _LEGACY_P
    p = P.api_json(surah)
    return json.loads(p.read_text(encoding="utf-8"))["audio_file"]["timestamps"]


def load_align_model(model_name: str = "jonatasgrosman/wav2vec2-large-xlsr-53-arabic"):
    """Import torch+whisperx, sanity-check CUDA, and load the wav2vec2
    alignment model. Returns (align_model, align_meta, whisperx)."""
    log("importing torch + whisperx...")
    import torch
    import whisperx
    if not torch.cuda.is_available():
        fail("CUDA unavailable")
    log(f"torch {torch.__version__}  device={torch.cuda.get_device_name(0)}")
    log(f"loading alignment model {model_name}...")
    t = time.monotonic()
    align_model, align_meta = whisperx.load_align_model(
        language_code="ar", device="cuda", model_name=model_name)
    log(f"loaded in {time.monotonic()-t:.1f}s")
    return align_model, align_meta, whisperx


def align_surah(surah: int, align_model, align_meta, whisperx_mod,
                force: bool = False, print_summary: bool = False, P=None):
    """Run forced alignment for one surah using a pre-loaded model.
    Returns the path to the output JSON, or None if skipped."""
    P = P or _LEGACY_P
    out_path = P.wx_json(surah)
    if out_path.exists() and not force:
        log(f"skip surah {surah}: {out_path.name} exists")
        return out_path
    audio_path = P.audio_mp3(surah)
    if not audio_path.exists():
        log(f"surah {surah}: missing audio {audio_path.name} -- skipping")
        return None

    verses = load_verses(surah, P)
    api_ts = load_api_timestamps(surah, P)
    if len(verses) != len(api_ts):
        log(f"surah {surah}: verse count mismatch "
            f"api={len(api_ts)} canonical={len(verses)} -- skipping")
        return None

    log(f"surah {surah}: {len(verses)} verses, "
        f"{sum(len(v['words']) for v in verses)} canonical words")

    audio_path16 = ensure_16k_mono_wav(audio_path)
    audio = whisperx_mod.load_audio(str(audio_path16))
    audio_ms = int(len(audio) / 16 + 0.5)

    raw_per_verse = []
    norm_per_verse = []
    for v in verses:
        raw, norm = [], []
        for w in v["words"]:
            n = normalize(w)
            if not n:
                continue
            raw.append(w); norm.append(n)
        raw_per_verse.append(raw)
        norm_per_verse.append(norm)

    chunks = []
    cur_idxs, cur_start = [], None
    for i, v in enumerate(api_ts):
        if cur_start is None:
            cur_start = v["timestamp_from"]
        cur_idxs.append(i)
        span = (v["timestamp_to"] - cur_start) / 1000.0
        if span >= CHUNK_TARGET_S:
            chunks.append((cur_idxs, cur_start, v["timestamp_to"]))
            cur_idxs, cur_start = [], None
    if cur_idxs:
        chunks.append((cur_idxs, cur_start, api_ts[cur_idxs[-1]]["timestamp_to"]))

    segments = []
    for idxs, start_ms, end_ms in chunks:
        wf = max(0, start_ms - CHUNK_PAD_MS) / 1000.0
        wt = min(audio_ms, end_ms + CHUNK_PAD_MS) / 1000.0
        text = " ".join(w for i in idxs for w in norm_per_verse[i])
        segments.append({"start": wf, "end": wt, "text": text})

    n_words_total = sum(len(norm_per_verse[i]) for c in chunks for i in c[0])
    log(f"  aligning {len(segments)} chunks, {n_words_total} words, "
        f"{audio_ms/1000:.1f}s audio")
    t = time.monotonic()
    aligned = whisperx_mod.align(
        segments, align_model, align_meta, audio, "cuda",
        return_char_alignments=False,
    )
    log(f"  aligned in {time.monotonic()-t:.1f}s")

    flat_aligned = []
    for seg in aligned.get("segments", []):
        for w in seg.get("words", []):
            if "start" in w and "end" in w:
                flat_aligned.append(w)
    if len(flat_aligned) != n_words_total:
        log(f"  WARNING: aligned {len(flat_aligned)}/{n_words_total} words")

    rows = []
    cursor = 0
    for v, raw_words in zip(verses, raw_per_verse):
        n = len(raw_words)
        ws = flat_aligned[cursor:cursor + n]
        cursor += n
        if not ws:
            rows.append({"verse_key": v["verse_key"],
                         "n_words": len(v["words"]),
                         "n_aligned": 0,
                         "from_ms": None, "to_ms": None})
            continue
        out_words = [
            {"word": raw_w,
             "aligned_word": aw.get("word"),
             "start": aw["start"], "end": aw["end"],
             "score": aw.get("score")}
            for raw_w, aw in zip(raw_words, ws)
        ]
        rows.append({
            "verse_key": v["verse_key"],
            "n_words": len(v["words"]),
            "n_aligned": len(out_words),
            "from_ms": int(round(out_words[0]["start"] * 1000)),
            "to_ms": int(round(out_words[-1]["end"] * 1000)),
            "first_word": out_words[0]["word"],
            "last_word": out_words[-1]["word"],
            "words": out_words,
        })

    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    log(f"  wrote {out_path.name}")

    if print_summary:
        print()
        print(f"{'verse':>6}  {'n_w':>4}  {'aligned':>7}  {'from(ms)':>9}  "
              f"{'to(ms)':>8}  delta_to_vs_API")
        for r, ats in zip(rows, api_ts):
            delta = "-" if r.get("to_ms") is None \
                else f"{r['to_ms'] - ats['timestamp_to']:+}"
            print(f"{r['verse_key']:>6}  {r['n_words']:>4}  {r['n_aligned']:>7}  "
                  f"{r.get('from_ms','-'):>9}  {r.get('to_ms','-'):>8}  {delta}")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("surah", type=int)
    ap.add_argument("--reciter-id", type=int, default=LEGACY_RECITER_ID)
    ap.add_argument("--align-model",
                    default="jonatasgrosman/wav2vec2-large-xlsr-53-arabic")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    P = paths_for(args.reciter_id)
    out_path = P.wx_json(args.surah)
    if out_path.exists() and not args.force:
        log(f"skip surah {args.surah}: {out_path.name} exists "
            f"(use --force to override)")
        return

    align_model, align_meta, whisperx_mod = load_align_model(args.align_model)
    align_surah(args.surah, align_model, align_meta, whisperx_mod,
                force=args.force, print_summary=True, P=P)
    log("DONE")


if __name__ == "__main__":
    main()
