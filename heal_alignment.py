"""
Post-process WhisperX forced-alignment output using the chronological-
order constraint (words come in canonical order and cannot overlap).

Applies six healing passes to data/whisperx/surah_<N>_force_v2.json
and writes data/whisperx_healed/surah_<N>.json. The healed JSON has
the same shape as the input but with corrected word timings + a
per-word `healed_by` field naming the pass that touched it.

Healing passes
--------------
1. MONOTONICITY: enforce word[i+1].start >= word[i].end + MIN_INTER_WORD.
   CTC sometimes emits overlapping or zero-gap words when uncertain.
2. ANCHOR_INTERPOLATE: words with score < LOW_SCORE between two
   high-score "anchors" get redistributed within the anchor window
   weighted by canonical character count.
3. SILENCE_SNAP: when ffmpeg silencedetect finds a real silence inside
   a low-confidence run, the silence boundary is used as the inter-
   word gap (much higher precision than char-count interpolation).
4. DENSITY_OUTLIER: flag any word whose ms_per_char is more than
   DENSITY_OUTLIER_RATIO times the verse's high-conf median. These get
   the same anchor-interpolation treatment as low-score words.
5. VERSE_CONTINUITY: enforce verse[N].last_word.end + MIN_INTER_VERSE
   <= verse[N+1].first_word.start. Violations indicate chunk-edge CTC
   compression and trigger a redistribution of the affected verse(s).
6. FILL_RATIO_CHECK: compute aligned_span / verse_span. If < FILL_MIN
   for a verse with HIGH median score, flag as compressed and
   anchor-redistribute its words across the full verse span using
   API timestamps as a fallback span.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

from reciter_paths import paths_for, LEGACY_RECITER_ID

ROOT = Path(__file__).parent
_LEGACY_P = paths_for(LEGACY_RECITER_ID)
DATA = _LEGACY_P.data_dir
WX_IN = _LEGACY_P.wx_dir
WX_OUT = _LEGACY_P.wx_healed_dir
AUDIO = _LEGACY_P.audio_dir

LOW_SCORE = 0.55       # below this, the aligned word is untrusted
HIGH_SCORE = 0.70      # at or above, the aligned word can be an anchor
MIN_INTER_WORD_S = 0.001  # 1 ms minimum gap to keep monotonicity strict
MIN_INTER_VERSE_S = 0.05  # 50 ms minimum gap between verses
DENSITY_OUTLIER_RATIO = 3.0
FILL_MIN = 0.60        # aligned-word coverage must reach 60% of verse span
SILENCE_NOISE_DB = -22
SILENCE_MIN_DUR_S = 0.20
SILENCE_MIN_INTRA_VERSE_S = 0.10  # accept shorter silences inside a verse


def silencedetect(mp3_path, start_s, end_s, min_dur_s=SILENCE_MIN_INTRA_VERSE_S):
    """Return list of (start_ms, end_ms) silences in [start_s, end_s] of mp3."""
    duration = max(0.0, end_s - start_s)
    if duration <= 0:
        return []
    cmd = ["ffmpeg", "-ss", str(start_s), "-t", str(duration),
           "-i", str(mp3_path),
           "-af", f"silencedetect=noise={SILENCE_NOISE_DB}dB:d={min_dur_s}",
           "-f", "null", "-"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except Exception:
        return []
    stderr = r.stderr or ""
    starts = [float(m) for m in re.findall(r"silence_start:\s*([\d.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([\d.]+)", stderr)]
    out = []
    for s, e in zip(starts, ends):
        if e >= s:
            out.append(((start_s + s) * 1000.0, (start_s + e) * 1000.0))
    return out


def char_len(word: str) -> int:
    """Approximate phonetic length: count letters, ignore diacritics."""
    if not word:
        return 1
    # Strip Arabic diacritics
    s = re.sub(r"[ً-ْٰۖ-ۭ]", "", word)
    s = s.replace("ـ", "")  # tatweel
    return max(1, len(s))


# --- Pass 1 ----------------------------------------------------------------
def pass_monotonicity(words):
    """Enforce word[i+1].start >= word[i].end. Snap overlaps to midpoint."""
    fixed = 0
    for i in range(len(words) - 1):
        a = words[i]; b = words[i + 1]
        if a["end"] > b["start"]:
            mid = (a["end"] + b["start"]) / 2.0
            a["end"] = mid - MIN_INTER_WORD_S / 2
            b["start"] = mid + MIN_INTER_WORD_S / 2
            a.setdefault("healed_by", []).append("monotonicity")
            b.setdefault("healed_by", []).append("monotonicity")
            fixed += 1
    return fixed


# --- Helper for redistribution ---------------------------------------------
def redistribute_run(words, run_start, run_end, audio_lo, audio_hi,
                     silences=None, reason=""):
    """Re-place words[run_start..run_end] uniformly between audio_lo and
    audio_hi, weighted by character count. If `silences` (list of
    (start_ms, end_ms)) is provided and falls inside the window, use
    silences as inter-word boundaries when there's exactly the right
    number to split the run.
    """
    n = run_end - run_start + 1
    if n <= 0 or audio_hi <= audio_lo:
        return 0
    target_words = words[run_start:run_end + 1]
    chars = [char_len(w["word"]) for w in target_words]
    total_chars = sum(chars)
    span_ms = (audio_hi - audio_lo) * 1000.0

    # Try silence-snap if we have exactly n-1 silences to use as inter-
    # word gaps inside [audio_lo, audio_hi].
    inner = []
    if silences:
        inner = [s for s in silences
                 if audio_lo * 1000.0 < (s[0] + s[1]) / 2 < audio_hi * 1000.0]
    if inner and len(inner) >= n - 1 and len(inner) <= n + 1:
        # Use silence-snap. Sort silences by midpoint, take the n-1
        # whose centers are closest to the proportional positions.
        inner.sort(key=lambda s: (s[0] + s[1]) / 2)
        # If too many silences, pick the n-1 nearest expected positions.
        if len(inner) > n - 1:
            # Expected centers: at proportional cumulative-char positions.
            expected = []
            cum = 0
            for c in chars[:-1]:
                cum += c
                expected.append(audio_lo * 1000.0 + (cum / total_chars) * span_ms)
            chosen = []
            used = set()
            for ec in expected:
                # find closest unused silence
                best = min(((j, s) for j, s in enumerate(inner) if j not in used),
                           key=lambda x: abs((x[1][0] + x[1][1]) / 2 - ec),
                           default=None)
                if best is None:
                    chosen = []
                    break
                used.add(best[0])
                chosen.append(best[1])
            chosen.sort(key=lambda s: (s[0] + s[1]) / 2)
            inner = chosen
        if len(inner) == n - 1:
            MIN_WORD_DUR_S = 0.02
            cur_start = audio_lo
            for k, w in enumerate(target_words):
                if k < n - 1:
                    sil_s, sil_e = inner[k]
                    w["start"] = cur_start
                    w["end"] = max(cur_start + MIN_WORD_DUR_S, sil_s / 1000.0)
                    cur_start = max(w["end"] + MIN_INTER_WORD_S, sil_e / 1000.0)
                else:
                    w["start"] = cur_start
                    w["end"] = max(cur_start + MIN_WORD_DUR_S, audio_hi)
                w.setdefault("healed_by", []).append(f"silence_snap:{reason}")
            return n

    # Fall back to char-count proportional split. Enforce a min word
    # duration of MIN_WORD_DUR_S so we don't emit zero-length words
    # when the window is unusually tight.
    MIN_WORD_DUR_S = 0.02
    available = audio_hi - audio_lo
    if available < n * MIN_WORD_DUR_S:
        # Window is too narrow for n words at the floor. Best we can do
        # is split it uniformly -- log will show this as a degenerate
        # case (rare; only happens when anchor neighbours are unusually
        # close).
        per = available / n
        for k, w in enumerate(target_words):
            w["start"] = audio_lo + k * per
            w["end"] = audio_lo + (k + 1) * per
            w.setdefault("healed_by", []).append(f"interpolate_tight:{reason}")
        return n

    cum = 0
    pos = audio_lo
    for k, (w, c) in enumerate(zip(target_words, chars)):
        word_dur = (c / total_chars) * available
        if word_dur < MIN_WORD_DUR_S:
            word_dur = MIN_WORD_DUR_S
        w["start"] = pos
        w["end"] = pos + word_dur
        if k < n - 1:
            # leave a small inter-word gap (5% of word duration, max 50ms)
            gap = min(word_dur * 0.05, 0.05)
            w["end"] = max(w["start"] + MIN_WORD_DUR_S, w["end"] - gap)
        pos = w["end"] + max(0, gap if k < n - 1 else 0)
        w.setdefault("healed_by", []).append(f"interpolate:{reason}")
    # If we overshot audio_hi (rounding from MIN_WORD_DUR_S floor), pull
    # the trailing words back proportionally.
    if pos > audio_hi:
        # Linear scale to fit
        scale = (audio_hi - audio_lo) / (pos - audio_lo)
        for w in target_words:
            w["start"] = audio_lo + (w["start"] - audio_lo) * scale
            w["end"] = audio_lo + (w["end"] - audio_lo) * scale
    return n


# --- Pass 2 + 4 (combined: low-score + density-outlier) --------------------
def pass_anchor_interpolate(verse, mp3_path):
    """Find runs of low-confidence or density-outlier words and re-place
    them between the surrounding high-conf anchors. Optionally use
    silence-snap if ffmpeg finds matching silences."""
    words = verse.get("words") or []
    if len(words) < 2:
        return 0

    # Median ms_per_char from high-score words only.
    densities = []
    for w in words:
        if (w.get("score") or 0) >= HIGH_SCORE:
            cl = char_len(w["word"])
            d_ms = (w["end"] - w["start"]) * 1000.0
            if cl > 0 and d_ms > 0:
                densities.append(d_ms / cl)
    densities.sort()
    median_density = densities[len(densities) // 2] if densities else None

    # Mark each word as anchor / suspect.
    suspect = [False] * len(words)
    for i, w in enumerate(words):
        score = w.get("score") or 0
        is_low = score < LOW_SCORE
        is_outlier = False
        if median_density is not None:
            cl = char_len(w["word"])
            d_ms = (w["end"] - w["start"]) * 1000.0
            if cl > 0 and d_ms > 0:
                ratio = (d_ms / cl) / median_density
                if ratio > DENSITY_OUTLIER_RATIO or ratio < 1 / DENSITY_OUTLIER_RATIO:
                    is_outlier = True
        suspect[i] = is_low or is_outlier

    # Find runs of suspect indices and redistribute.
    n_healed = 0
    i = 0
    while i < len(words):
        if not suspect[i]:
            i += 1
            continue
        run_start = i
        while i < len(words) and suspect[i]:
            i += 1
        run_end = i - 1
        # Anchor windows
        if run_start == 0:
            audio_lo = words[0]["start"]
        else:
            audio_lo = words[run_start - 1]["end"] + MIN_INTER_WORD_S
        if run_end == len(words) - 1:
            audio_hi = words[-1]["end"]
        else:
            audio_hi = words[run_end + 1]["start"] - MIN_INTER_WORD_S
        if audio_hi <= audio_lo:
            continue
        # Look for ffmpeg silences in the run window.
        silences = silencedetect(mp3_path, audio_lo, audio_hi) if mp3_path else []
        n_healed += redistribute_run(words, run_start, run_end, audio_lo, audio_hi,
                                     silences=silences, reason="low_score_or_outlier")
    return n_healed


# --- Pass 5 ----------------------------------------------------------------
def pass_verse_continuity(verses):
    """Enforce verse[N].last_word.end + MIN <= verse[N+1].first_word.start.
    Snap to a midpoint when verses overlap, but never shrink either word
    below MIN_WORD_DUR_S so we don't emit zero/negative-duration words."""
    MIN_WORD_DUR_S = 0.02
    violations = 0
    for i in range(len(verses) - 1):
        a = verses[i]; b = verses[i + 1]
        a_words = a.get("words") or []
        b_words = b.get("words") or []
        if not a_words or not b_words:
            continue
        a_last = a_words[-1]
        b_first = b_words[0]
        if a_last["end"] + MIN_INTER_VERSE_S > b_first["start"]:
            violations += 1
            mid = (a_last["end"] + b_first["start"]) / 2.0
            # Don't shrink either word below MIN_WORD_DUR_S.
            new_a_end = max(a_last["start"] + MIN_WORD_DUR_S,
                            mid - MIN_INTER_VERSE_S / 2)
            new_b_start = min(b_first["end"] - MIN_WORD_DUR_S,
                              mid + MIN_INTER_VERSE_S / 2)
            # If even those clamps overlap (can happen when both words
            # are very short), give up and just enforce ordering with
            # the minimum gap.
            if new_a_end >= new_b_start:
                # Push verse B's first word forward (and shift the rest
                # of its words by the same delta).
                gap = MIN_INTER_VERSE_S
                shift = (a_last["end"] + gap) - b_first["start"]
                if shift > 0:
                    for w in b_words:
                        w["start"] += shift
                        w["end"] += shift
                    b_words[0].setdefault("healed_by", []).append(
                        "verse_continuity:shift")
            else:
                a_last["end"] = new_a_end
                b_first["start"] = new_b_start
                a_last.setdefault("healed_by", []).append("verse_continuity")
                b_first.setdefault("healed_by", []).append("verse_continuity")
    return violations


# --- Pass 6 ----------------------------------------------------------------
def pass_fill_ratio(verses, api_ts, mp3_path):
    """For each verse, detect "compressed" alignment (CTC packed all the
    words into a small fraction of the verse's audio span) and re-place
    them across a better window. Two cases:

    A) HIGH-confidence words but compressed window: usually a chunk-edge
       failure where the audio window was wrong but per-word matches are
       good. Redistribute across the API span.
    B) ALL-low-confidence words and short aligned span: WhisperX failed
       on the verse. Use the gap between neighbour verses' high-conf
       words to find a better target window. If that fails, fall back
       to API span.
    """
    healed_count = 0
    for i, v in enumerate(verses):
        words = v.get("words") or []
        if len(words) < 2:
            continue
        scores = sorted(w.get("score") or 0 for w in words)
        med_score = scores[len(scores) // 2]
        aligned_span = words[-1]["end"] - words[0]["start"]
        api_span_ms = api_ts[i]["timestamp_to"] - api_ts[i]["timestamp_from"]
        if api_span_ms <= 0:
            continue
        api_span_s = api_span_ms / 1000.0
        ratio = aligned_span / api_span_s

        if ratio >= FILL_MIN:
            continue  # alignment fills the verse adequately

        # Determine the best target window. Default = API span.
        target_lo = api_ts[i]["timestamp_from"] / 1000.0
        target_hi = api_ts[i]["timestamp_to"] / 1000.0

        # Tighten using neighbour-verse anchors when their last/first
        # words are high confidence -- those are firmer ground than
        # API timestamps.
        if i > 0:
            prev_words = verses[i - 1].get("words") or []
            if prev_words and (prev_words[-1].get("score") or 0) >= HIGH_SCORE:
                cand = prev_words[-1]["end"] + MIN_INTER_VERSE_S
                if cand < target_hi:
                    target_lo = max(target_lo, cand)
        if i + 1 < len(verses):
            next_words = verses[i + 1].get("words") or []
            if next_words and (next_words[0].get("score") or 0) >= HIGH_SCORE:
                cand = next_words[0]["start"] - MIN_INTER_VERSE_S
                if cand > target_lo:
                    target_hi = min(target_hi if med_score >= HIGH_SCORE
                                    else next_words[0]["start"], cand)

        if target_hi <= target_lo:
            continue

        # Don't re-place if the window we'd use is also tiny.
        if (target_hi - target_lo) < aligned_span * 1.2:
            continue

        silences = silencedetect(mp3_path, target_lo, target_hi) \
            if mp3_path else []
        reason = "fill_ratio_high_conf" if med_score >= HIGH_SCORE \
            else "fill_ratio_low_conf"
        redistribute_run(words, 0, len(words) - 1, target_lo, target_hi,
                         silences=silences, reason=reason)
        healed_count += 1
    return healed_count


# --- Public ----------------------------------------------------------------
def heal_surah(surah: int, verbose: bool = False, P=None):
    P = P or _LEGACY_P
    in_path = P.wx_json(surah)
    if not in_path.exists():
        return None
    out_path = P.wx_healed_json(surah)
    api_path = P.api_json(surah)
    audio_path = P.audio_mp3(surah)

    verses = json.loads(in_path.read_text(encoding="utf-8"))
    api_ts = (json.loads(api_path.read_text(encoding="utf-8"))["audio_file"]["timestamps"]
              if api_path.exists() else None)

    counts = {"monotonicity": 0, "anchor_interp": 0,
              "verse_continuity": 0, "fill_ratio": 0}

    # Pass 1: monotonicity per verse
    for v in verses:
        words = v.get("words") or []
        counts["monotonicity"] += pass_monotonicity(words)

    # Passes 2 + 3 + 4: low-score / density-outlier interpolation per verse
    for v in verses:
        counts["anchor_interp"] += pass_anchor_interpolate(v, audio_path
                                                            if audio_path.exists()
                                                            else None)

    # Pass 6: fill-ratio (needs API timestamps)
    if api_ts is not None and len(api_ts) == len(verses):
        counts["fill_ratio"] = pass_fill_ratio(verses, api_ts, audio_path
                                                if audio_path.exists()
                                                else None)
        # After fill_ratio re-distributes some verses, run monotonicity
        # & anchor_interp again to clean up.
        for v in verses:
            pass_monotonicity(v.get("words") or [])

    # Pass 5: verse continuity
    counts["verse_continuity"] = pass_verse_continuity(verses)

    # Recompute per-verse from_ms, to_ms.
    for v in verses:
        words = v.get("words") or []
        if words:
            v["from_ms"] = int(round(words[0]["start"] * 1000))
            v["to_ms"] = int(round(words[-1]["end"] * 1000))
            v["first_word"] = words[0]["word"]
            v["last_word"] = words[-1]["word"]

    out_path.write_text(json.dumps(verses, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    if verbose:
        print(f"surah {surah:>3}: {sum(counts.values()):>4} edits  "
              f"({counts['monotonicity']} mono, {counts['anchor_interp']} anchor, "
              f"{counts['verse_continuity']} continuity, {counts['fill_ratio']} fill)")
    return counts


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

    totals = {"monotonicity": 0, "anchor_interp": 0,
              "verse_continuity": 0, "fill_ratio": 0}
    for s in targets:
        c = heal_surah(s, verbose=True, P=P)
        if c is None:
            print(f"surah {s:>3}: skip (no input)")
            continue
        for k, v in c.items():
            totals[k] += v
    print(f"\nTotals: {totals}")


if __name__ == "__main__":
    main()
