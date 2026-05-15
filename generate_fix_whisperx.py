"""
Generate corrected timestamps for Khalifah Al Tunaiji using a hybrid
ffmpeg + WhisperX signal.

Two signals
-----------
1. ffmpeg silencedetect (-22 dB / 200 ms) -- accurate "is the audio
   audibly quiet here?" judgment. Used to classify each API verse
   boundary as INSIDE / EARLY / LATE. Same threshold the original
   silence-detection PoC used, so the SET of boundaries we touch is
   the same set the user can perceive as drift.

2. WhisperX forced alignment (data/whisperx/surah_<N>_force_v2.json)
   -- precise per-word [start, end] from feeding canonical text_uthmani
   to whisperx.align with jonatasgrosman/wav2vec2-large-xlsr-53-arabic.
   Used for two things:
     a) Choosing where to snap a corrected boundary: the start of the
        next verse's first word per CTC is more precise than ffmpeg's
        amplitude-threshold crossing.
     b) Per-verse word-level segments (replaces the proportional rescale
        in the v1 PoC).

Why both? ffmpeg's silence is the user-perceptible "audio is quiet"
signal; CTC posterior fires later than ffmpeg's threshold (vowel decay
keeps audio above -22 dB after CTC declares the word ended), so a pure-
WhisperX in-silence test under-counts true silence and over-corrects
fine boundaries (verified: surah 112 v1 = 0 corrections, pure-WhisperX
v2 first draft = 1 wrong correction inside a real ffmpeg silence).

Boundary rule
-------------
For each adjacent verse pair (N, N+1):
  silence = nearest ffmpeg silence interval to API boundary
  if no silence within MAX_MATCH_MS: leave alone
  if API is INSIDE silence:           leave alone (no perceptible drift)
  else:
      target = whisperx_first_word_start[N+1] - SAFETY_MS
      if |target - API| < MIN_FIX_DRIFT_MS: leave alone
      if WhisperX score is too low or |target - API| is huge:
          fall back to API (alignment failure guard)
      else: snap boundary to target

Outputs (under data/corrected_v2/):
    surah_<N>_corrected.json  same shape as API, fixed timings
    surah_<N>_diff.json       per-verse diff vs API
    surah_<N>_qul.csv         QUL-style CSV
    summary.json              aggregate report
"""
import csv
import json
import re
import subprocess
from pathlib import Path

from reciter_paths import paths_for, LEGACY_RECITER_ID

ROOT = Path(__file__).parent
_LEGACY_P = paths_for(LEGACY_RECITER_ID)
DATA = _LEGACY_P.data_dir
AUDIO = _LEGACY_P.audio_dir
OUT = _LEGACY_P.corrected_dir

# ffmpeg silence detection (matches v1 / analyze_drift_v2)
NOISE_DB = -22
MIN_SILENCE_DUR_S = 0.10  # ffmpeg's silencedetect duration filter --
                          # raised the floor so we catch Tunaiji's
                          # very brief inter-verse breaths (e.g. the
                          # 143 ms gap at the surah 13 verse 21/22
                          # boundary)
MIN_SILENCE_LEN_MS = 100  # Tunaiji takes brief 130-150 ms breaths at
                          # some inter-verse boundaries (e.g. 13:21/22
                          # at 562193 ms). 200 ms was too strict.
MAX_MATCH_MS = 2500    # ignore silences this far from API boundary
                       # (raised to 2500 to catch the Tunaiji surah 13
                       # cluster around verse 18-20 where the API is
                       # drifted by ~1.7-1.9 s)

# Boundary correction
SAFETY_MS = 150        # snap to (next_verse_first_word - SAFETY_MS).
                       # CTC posterior rises just before the audio
                       # crosses ffmpeg's silence threshold, so 150 ms
                       # leaves the boundary inside the audibly-quiet
                       # zone for Tunaiji (typical inter-verse silence
                       # is 500-700 ms).
MIN_FIX_DRIFT_MS = 150 # only rewrite if the change is at least this
                       # large; matches the v1 PoC threshold

# WhisperX trust guards
MAX_TRUST_DELTA_MS = 2500  # if WhisperX target disagrees with API by
                           # more than this, distrust (probably a CTC
                           # alignment failure -- e.g. surah 2 verse 17
                           # collapsed by 6 s in the first draft).
                           # Set to 2500 because Tunaiji surah 13 has
                           # legitimate API drift up to ~1.9 s in verses
                           # 17-20 and we want to correct those.
MIN_WORD_SCORE = 0.20      # if median aligned-word score for verse
                           # N or N+1 is below this, distrust
MIN_TRUST_BYPASS_SCORE = 0.75  # if the median word score is at least
                           # this high AND WX matches an ffmpeg silence
                           # within 500 ms, bypass MAX_TRUST_DELTA_MS
                           # entirely -- WX is well-anchored to real
                           # acoustic boundaries even if the delta is
                           # large

# First-verse left-edge handling
LEAD_MS = 50           # subtitle for verse 1 appears LEAD_MS before
                       # the first word starts


def silencedetect(mp3: Path):
    """Return list of (start_ms, end_ms) silence intervals."""
    cmd = ["ffmpeg", "-i", str(mp3),
           "-af", f"silencedetect=noise={NOISE_DB}dB:d={MIN_SILENCE_DUR_S}",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except Exception:
        return []
    text = r.stderr or ""
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", text)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", text)]
    return [(s * 1000.0, e * 1000.0) for s, e in zip(starts, ends) if e >= s]


def nearest_silence(boundary_ms: float, silences):
    """Find the silence whose midpoint is closest to boundary_ms,
    constrained to MAX_MATCH_MS distance and MIN_SILENCE_LEN_MS length.
    Returns (start, end) or None."""
    if not silences:
        return None
    candidates = [iv for iv in silences if (iv[1] - iv[0]) >= MIN_SILENCE_LEN_MS]
    if not candidates:
        return None
    best = min(candidates, key=lambda iv: abs((iv[0] + iv[1]) / 2 - boundary_ms))
    if abs(((best[0] + best[1]) / 2) - boundary_ms) > MAX_MATCH_MS:
        return None
    return best


def median_score(verse):
    ws = verse.get("words") or []
    scores = [w["score"] for w in ws if w.get("score") is not None]
    if not scores:
        return 0.0
    scores.sort()
    return scores[len(scores) // 2]


def load_whisperx(surah: int, P=None):
    """Prefer healed output (whisperx_healed/) if present -- the
    healer enforces chronological-order consistency and snaps low-conf
    words to silences. Fall back to raw force_align output."""
    P = P or _LEGACY_P
    healed = P.wx_healed_json(surah)
    if healed.exists():
        return json.loads(healed.read_text(encoding="utf-8"))
    p = P.wx_json(surah)
    return json.loads(p.read_text(encoding="utf-8"))


def load_api(surah: int, P=None):
    P = P or _LEGACY_P
    return json.loads(P.api_json(surah).read_text(encoding="utf-8"))


def correct_surah(surah: int, P=None):
    P = P or _LEGACY_P
    api = load_api(surah, P)["audio_file"]
    wx = load_whisperx(surah, P)
    api_ts = api["timestamps"]
    if len(api_ts) != len(wx):
        print(f"surah {surah}: WARN verse-count mismatch "
              f"api={len(api_ts)} wx={len(wx)} -- skipping")
        return None

    audio_path = P.audio_mp3(surah)
    if not audio_path.exists():
        print(f"surah {surah}: WARN no audio -- skipping silencedetect")
        return None
    silences = silencedetect(audio_path)

    first_words = [r["words"][0] if r.get("words") else None for r in wx]
    last_words = [r["words"][-1] if r.get("words") else None for r in wx]
    scores = [median_score(r) for r in wx]

    new_from = [vt["timestamp_from"] for vt in api_ts]
    new_to = [vt["timestamp_to"] for vt in api_ts]
    n_distrusted = 0

    # First-verse left edge: API usually starts at 0. If it's positive
    # and later than where the first word actually starts, advance it
    # to (first_word - LEAD_MS) so the subtitle isn't visibly late.
    if first_words[0] is not None and scores[0] >= MIN_WORD_SCORE:
        wx_first_start = int(round(first_words[0]["start"] * 1000))
        api_from = api_ts[0]["timestamp_from"]
        if api_from > wx_first_start \
                and abs(api_from - wx_first_start) <= MAX_TRUST_DELTA_MS:
            new_from[0] = max(0, wx_first_start - LEAD_MS)

    # Inter-verse boundaries.
    for i in range(len(wx) - 1):
        api_boundary = api_ts[i]["timestamp_to"]

        sil = nearest_silence(api_boundary, silences)
        if sil is None:
            # Couldn't find a credible silence to anchor against.
            # The user perceives drift only when boundary lands during
            # voice; without a silence reference we can't classify, so
            # leave alone.
            continue
        s_start, s_end = sil
        if s_start <= api_boundary <= s_end:
            # API boundary is inside a real ffmpeg silence -- the user
            # doesn't perceive any drift. Leave alone.
            continue

        # API is OUTSIDE silence: drift is perceptible. Decide where to
        # snap. Prefer WhisperX's next-verse-first-word edge (precise
        # consonant onset); fall back to the ffmpeg silence_end if WX
        # is unavailable / untrusted for this verse pair.
        if first_words[i + 1] is not None \
                and scores[i] >= MIN_WORD_SCORE \
                and scores[i + 1] >= MIN_WORD_SCORE:
            wx_target = int(round(first_words[i + 1]["start"] * 1000)) - SAFETY_MS
            if abs(wx_target - api_boundary) > MAX_TRUST_DELTA_MS:
                # WhisperX disagrees too much -- alignment glitch. Use
                # the ffmpeg silence end as a more conservative target.
                target = int(round(s_end - SAFETY_MS))
                n_distrusted += 1
            else:
                target = wx_target
        else:
            target = int(round(s_end - SAFETY_MS))
            n_distrusted += 1

        # Clamp the snap target inside the silence interval so we never
        # land outside the audibly-quiet zone.
        target = max(int(round(s_start)), min(target, int(round(s_end))))

        if abs(target - api_boundary) < MIN_FIX_DRIFT_MS:
            continue

        new_to[i] = target
        new_from[i + 1] = target

    # Last-verse right edge: keep API. UX expects the translation to
    # stay on screen until audio fully ends.

    corrected = []
    diff = []
    n_corrected_boundaries = 0

    for i, (r, vt) in enumerate(zip(wx, api_ts)):
        nf = new_from[i]
        nt = new_to[i]
        changed = (nf != vt["timestamp_from"]) or (nt != vt["timestamp_to"])
        if changed:
            n_corrected_boundaries += 1

        # Word-level segments from WhisperX aligned words.
        segments = []
        for idx, w in enumerate(r.get("words", []), start=1):
            if "start" not in w or "end" not in w:
                continue
            segments.append([idx,
                             int(round(w["start"] * 1000)),
                             int(round(w["end"] * 1000))])

        corrected_v = {
            "verse_key": vt["verse_key"],
            "timestamp_from": nf,
            "timestamp_to": nt,
            "duration": nt - nf,
            "segments": segments,
        }
        corrected.append(corrected_v)
        diff.append({
            "verse_key": vt["verse_key"],
            "old_from": vt["timestamp_from"],
            "old_to": vt["timestamp_to"],
            "new_from": nf,
            "new_to": nt,
            "delta_from": nf - vt["timestamp_from"],
            "delta_to": nt - vt["timestamp_to"],
            "wx_first_word_start_ms": int(round(first_words[i]["start"] * 1000))
                if first_words[i] else None,
            "wx_last_word_end_ms": int(round(last_words[i]["end"] * 1000))
                if last_words[i] else None,
        })

    out_obj = {
        "audio_file": {
            "id": api.get("id"),
            "chapter_id": api.get("chapter_id"),
            "audio_url": api["audio_url"],
            "format": api.get("format"),
            "timestamps": corrected,
        },
        "_meta": {
            "source": "qrfix v2: ffmpeg silencedetect (in-silence test) + "
                      "WhisperX (jonatasgrosman/wav2vec2-large-xlsr-53-arabic) "
                      "for snap position and word-level segments",
            "noise_db": NOISE_DB,
            "min_silence_dur_s": MIN_SILENCE_DUR_S,
            "safety_ms": SAFETY_MS,
            "min_fix_drift_ms": MIN_FIX_DRIFT_MS,
            "max_trust_delta_ms": MAX_TRUST_DELTA_MS,
            "min_word_score": MIN_WORD_SCORE,
            "n_boundaries_corrected": n_corrected_boundaries,
            "n_boundaries_distrusted": n_distrusted,
        },
    }
    (P.corrected_dir / f"surah_{surah}_corrected.json").write_text(
        json.dumps(out_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    (P.corrected_dir / f"surah_{surah}_diff.json").write_text(
        json.dumps(diff, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = P.qul_csv(surah)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["chapter", "ayah", "timestamp_from_ms", "timestamp_to_ms",
                    "duration_ms", "segments_json"])
        for v in corrected:
            chapter, ayah = v["verse_key"].split(":")
            w.writerow([chapter, ayah, v["timestamp_from"], v["timestamp_to"],
                        v["duration"], json.dumps(v["segments"])])

    return {
        "surah": surah,
        "n_verses": len(corrected),
        "n_corrected_boundaries": n_corrected_boundaries,
        "n_distrusted": n_distrusted,
        "max_delta_to": max((abs(d["delta_to"]) for d in diff), default=0),
        "max_delta_from": max((abs(d["delta_from"]) for d in diff), default=0),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("surahs", nargs="*", type=int,
                    help="surah numbers (default: all surahs that have "
                         "whisperx output)")
    ap.add_argument("--reciter-id", type=int, default=LEGACY_RECITER_ID)
    args = ap.parse_args()
    P = paths_for(args.reciter_id)

    targets = args.surahs or sorted(
        int(p.name.split("_")[1])
        for p in P.wx_dir.glob("surah_*_force_v2.json"))

    summary = []
    for s in targets:
        if not P.wx_json(s).exists():
            print(f"surah {s:>3}: SKIP (no whisperx output)")
            continue
        r = correct_surah(s, P)
        if r is None:
            continue
        summary.append(r)
        print(f"surah {r['surah']:>3}: corrected {r['n_corrected_boundaries']:>3}/"
              f"{r['n_verses']} verses  "
              f"distrusted={r['n_distrusted']:>3}  "
              f"max |delta_to|={r['max_delta_to']:>5}ms  "
              f"max |delta_from|={r['max_delta_from']:>5}ms")
    (P.corrected_dir / "summary.json").write_text(json.dumps(summary, indent=2),
                                                   encoding="utf-8")
    print(f"\nWrote outputs to {P.corrected_dir}")


if __name__ == "__main__":
    main()
