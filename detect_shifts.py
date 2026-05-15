"""
Detect whole-verse shifts in the Quran.com API timestamps.

For each verse N, compare API's [from, to] span to WhisperX's
forced-aligned [from, to] span (data/whisperx/surah_<N>_force_v2.json):

  iou_self  = IoU(api[N], wx[N])         -- 1.0 = perfect agreement
  best_off  = argmax_k IoU(api[N], wx[N+k])
                                          -- if best_off != 0, API[N]'s
                                             audio is actually verse N+k

Confidence is gated by WhisperX's per-verse median word score: low-
score verses (median < MIN_SCORE) cannot reliably be used as ground
truth on their own.

Cluster reporting: a single API shift bug typically affects many
consecutive verses (everything after the merge point shifts the same
way). The script groups adjacent flagged verses that share the same
best_off into clusters, which are much higher-confidence than isolated
flags.

Usage:
    python detect_shifts.py            # scan all surahs we have wx output for
    python detect_shifts.py 2 18 36    # specific surahs
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).parent
from reciter_paths import paths_for, LEGACY_RECITER_ID

_LEGACY_P = paths_for(LEGACY_RECITER_ID)
DATA = _LEGACY_P.data_dir
WX_DIR = _LEGACY_P.wx_dir
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# A verse is suspect if its API/WX agreement is below this AND an
# adjacent-verse comparison is above THIS.
LOW_IOU = 0.30   # API and WX disagree on this verse
HIGH_IOU = 0.50  # API span matches an adjacent WX span instead

# Minimum verse duration to bother reporting (very short verses have
# noisy IoU because tiny shifts dominate).
MIN_VERSE_MS = 1500

# WhisperX confidence gate. Verses whose median aligned-word score is
# below this can't be used as ground truth -- WX itself probably failed.
MIN_SCORE = 0.55


def iou(a, b):
    """Intersection-over-union of two [from, to] intervals (ms)."""
    if a is None or b is None:
        return 0.0
    inter = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    union = max(a[1], b[1]) - min(a[0], b[0])
    return inter / union if union > 0 else 0.0


def median_score(verse):
    ws = verse.get("words") or []
    scores = [w["score"] for w in ws if w.get("score") is not None]
    if not scores:
        return 0.0
    scores.sort()
    return scores[len(scores) // 2]


def scan_surah(surah: int, P=None):
    """Return dict with flags + clusters for this surah."""
    P = P or _LEGACY_P
    api_path = P.api_json(surah)
    wx_path = P.wx_json(surah)
    if not api_path.exists() or not wx_path.exists():
        return None

    api_ts = json.loads(api_path.read_text(encoding="utf-8"))["audio_file"]["timestamps"]
    healed = P.wx_healed_json(surah)
    if healed.exists():
        wx = json.loads(healed.read_text(encoding="utf-8"))
    else:
        wx = json.loads(wx_path.read_text(encoding="utf-8"))
    if len(api_ts) != len(wx):
        return {"error": f"verse count mismatch api={len(api_ts)} wx={len(wx)}"}

    api_spans = [(v["timestamp_from"], v["timestamp_to"]) for v in api_ts]
    wx_spans = [(r["from_ms"], r["to_ms"])
                if r.get("from_ms") is not None and r.get("to_ms") is not None
                else None for r in wx]
    scores = [median_score(r) for r in wx]

    flags = []
    for i in range(len(api_ts)):
        api_span = api_spans[i]
        if (api_span[1] - api_span[0]) < MIN_VERSE_MS:
            continue
        wx_self = wx_spans[i]
        if wx_self is None:
            continue

        s_iou = iou(api_span, wx_self)
        if s_iou >= LOW_IOU:
            continue

        # API[N] disagrees with WX[N]. Find best matching WX verse.
        best_j = i
        best_iou = s_iou
        for dj in range(-5, 6):
            j = i + dj
            if j < 0 or j >= len(wx_spans) or wx_spans[j] is None:
                continue
            v_iou = iou(api_span, wx_spans[j])
            if v_iou > best_iou:
                best_iou = v_iou
                best_j = j

        offset = best_j - i
        # Confidence flags:
        #   STRONG  = best_iou high, scores at i and best_j both high
        #   WEAK    = best_iou high but one of the WX scores is low
        #   GLITCH  = no good match anywhere (likely OUR alignment failure)
        if best_iou >= HIGH_IOU and offset != 0:
            score_anchor = scores[best_j]
            score_self = scores[i]
            confidence = "STRONG" if (score_anchor >= MIN_SCORE
                                      and score_self >= MIN_SCORE) \
                else "WEAK"
            flags.append({
                "verse_key": api_ts[i]["verse_key"],
                "iou_self": round(s_iou, 3),
                "iou_best": round(best_iou, 3),
                "best_match_offset": offset,
                "best_match_verse": wx[best_j]["verse_key"],
                "wx_score_self": round(scores[i], 2),
                "wx_score_anchor": round(scores[best_j], 2),
                "api_span_ms": list(api_span),
                "wx_self_span_ms": list(wx_self),
                "wx_best_match_span_ms": list(wx_spans[best_j]),
                "confidence": confidence,
            })
        elif s_iou < 0.10 and best_iou < HIGH_IOU:
            # No good match anywhere -- WX is probably wrong here.
            flags.append({
                "verse_key": api_ts[i]["verse_key"],
                "iou_self": round(s_iou, 3),
                "iou_best": round(best_iou, 3),
                "best_match_offset": 0,
                "best_match_verse": None,
                "wx_score_self": round(scores[i], 2),
                "wx_score_anchor": round(scores[i], 2),
                "api_span_ms": list(api_span),
                "wx_self_span_ms": list(wx_self),
                "wx_best_match_span_ms": None,
                "confidence": "WX_GLITCH",
            })

    # Cluster adjacent flags with same offset.
    clusters = []
    cur = None
    for f in flags:
        if f["confidence"] == "WX_GLITCH":
            cur = None
            continue
        verse_idx = next(i for i, v in enumerate(api_ts)
                         if v["verse_key"] == f["verse_key"])
        if cur and cur["offset"] == f["best_match_offset"] \
                and cur["last_idx"] == verse_idx - 1:
            cur["last_idx"] = verse_idx
            cur["last_verse"] = f["verse_key"]
            cur["count"] += 1
            cur["confidences"].append(f["confidence"])
        else:
            if cur and cur["count"] >= 2:
                clusters.append(cur)
            cur = {
                "offset": f["best_match_offset"],
                "first_verse": f["verse_key"],
                "last_verse": f["verse_key"],
                "first_idx": verse_idx,
                "last_idx": verse_idx,
                "count": 1,
                "confidences": [f["confidence"]],
            }
    if cur and cur["count"] >= 2:
        clusters.append(cur)

    return {"flags": flags, "clusters": clusters}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("surahs", nargs="*", type=int)
    ap.add_argument("--reciter-id", type=int, default=LEGACY_RECITER_ID)
    args = ap.parse_args()
    P = paths_for(args.reciter_id)

    targets = args.surahs or sorted(
        int(p.name.split("_")[1])
        for p in P.wx_dir.glob("surah_*_force_v2.json"))

    all_results = {}
    errors = {}
    total_strong = 0
    total_weak = 0
    total_glitch = 0
    surahs_with_clusters = 0

    for s in targets:
        res = scan_surah(s, P)
        if res is None:
            continue
        if isinstance(res, dict) and "error" in res:
            errors[s] = res["error"]
            continue
        flags = res["flags"]
        clusters = res["clusters"]
        if not flags:
            continue
        all_results[s] = res

        n_strong = sum(1 for f in flags if f["confidence"] == "STRONG")
        n_weak = sum(1 for f in flags if f["confidence"] == "WEAK")
        n_glitch = sum(1 for f in flags if f["confidence"] == "WX_GLITCH")
        total_strong += n_strong
        total_weak += n_weak
        total_glitch += n_glitch

        if clusters:
            surahs_with_clusters += 1
            print(f"\n=== surah {s}: {n_strong} STRONG / {n_weak} WEAK / "
                  f"{n_glitch} WX_GLITCH; {len(clusters)} cluster(s) ===")
            for c in clusters:
                conf_strong = c["confidences"].count("STRONG")
                conf_weak = c["confidences"].count("WEAK")
                offset_word = "TOO EARLY" if c["offset"] > 0 else "TOO LATE"
                print(f"  cluster: verses {c['first_verse']}..{c['last_verse']} "
                      f"({c['count']} consecutive) shifted {abs(c['offset'])} "
                      f"verse(s) {offset_word}  "
                      f"[{conf_strong} STRONG, {conf_weak} WEAK]")
        else:
            print(f"surah {s:>3}: {n_strong} STRONG, {n_weak} WEAK, "
                  f"{n_glitch} WX_GLITCH (no clusters >=2)")

    suffix = f"_r{args.reciter_id}" if args.reciter_id != LEGACY_RECITER_ID else ""
    out = REPORTS / f"verse_shifts{suffix}.json"
    out.write_text(json.dumps({"results": all_results, "errors": errors},
                              ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\n--- summary ---")
    print(f"surahs scanned:                      {len(targets)}")
    print(f"surahs with verse-count mismatch:    {len(errors)}")
    print(f"surahs with any flag:                {len(all_results)}")
    print(f"surahs with multi-verse cluster:     {surahs_with_clusters}")
    print(f"total STRONG flags:                  {total_strong}")
    print(f"total WEAK flags:                    {total_weak}")
    print(f"total WX_GLITCH flags:               {total_glitch}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
