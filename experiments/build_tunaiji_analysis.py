"""
Build a comprehensive Tunaiji (reciter id 161) findings report with
clickable evidence for every flagged verse and drifted boundary.

Reads existing pipeline outputs (no GPU re-run needed):
    reports/whisper_verify.json          -- per-verse Whisper-verify flags
    data/corrected_v2/surah_<N>_diff.json -- per-verse boundary corrections
    data/surah_<N>_tunaiji.json           -- API timestamps + audio_url

Writes:
    reports/tunaiji_full_analysis.md

Uses the same link conventions as the A/B test reports:
  * quran.com page:        https://quran.com/<surah>/<verse>?reciter=161
  * audio span (HTML5):    <mp3_url>#t=<start>,<end>
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from reciter_paths import paths_for, LEGACY_RECITER_ID  # noqa: E402

RECITER_ID = LEGACY_RECITER_ID            # 161
RECITER_NAME = "Khalifah Al Tunaiji"
SHIFT_SIM_THRESHOLD = 0.70
DRIFT_MS_THRESHOLD = 150
OUT_PATH = ROOT / "reports" / "tunaiji_full_analysis.md"

SURAH_NAMES = {
    1: "Al-Fatihah", 2: "Al-Baqarah", 3: "Aal-Imran", 4: "An-Nisa",
    5: "Al-Maidah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Rad", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
    21: "Al-Anbya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-'Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
    45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
    49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
    53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqi'ah",
    57: "Al-Hadid", 58: "Al-Mujadilah", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "As-Saff", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at", 80: "Abasa",
    81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
    85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la", 88: "Al-Ghashiyah",
    89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
    93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-'Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah", 100: "Al-'Adiyat",
    101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-'Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}


def quran_com_url(surah: int, verse: int) -> str:
    return f"https://quran.com/{surah}/{verse}?reciter={RECITER_ID}"


def audio_span_url(audio_url: str, start_ms: int, end_ms: int,
                   pad_s: float = 0.10) -> str:
    s = max(0.0, start_ms / 1000.0 - pad_s)
    e = end_ms / 1000.0 + pad_s
    return f"{audio_url}#t={s:.2f},{e:.2f}"


def fmt_ms(ms: int) -> str:
    s = ms / 1000.0
    m = int(s // 60)
    return f"{m}:{s - m*60:05.2f}"


def fmt_verse_list(verses):
    """[1,2,3,5,7,8,9] -> '1-3, 5, 7-9'"""
    if not verses:
        return ""
    verses = sorted(set(verses))
    out, i = [], 0
    while i < len(verses):
        j = i
        while j + 1 < len(verses) and verses[j + 1] == verses[j] + 1:
            j += 1
        if j == i:
            out.append(str(verses[i]))
        else:
            out.append(f"{verses[i]}-{verses[j]}")
        i = j + 1
    return ", ".join(out)


def load_inputs():
    P = paths_for(RECITER_ID)
    verify = json.loads((ROOT / "reports" / "whisper_verify.json")
                        .read_text(encoding="utf-8"))
    api_cache = {}
    for s in range(1, 115):
        ap = P.api_json(s)
        if ap.exists():
            api_cache[s] = json.loads(ap.read_text(encoding="utf-8"))

    diffs = {}
    for s in range(1, 115):
        dp = P.corrected_dir / f"surah_{s}_diff.json"
        if dp.exists():
            try:
                diffs[s] = json.loads(dp.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"WARN diff {s}: {e}", file=sys.stderr)
    return verify, api_cache, diffs


def collect_shifts(verify, api_cache):
    """Return list of dicts, one per high-confidence shift."""
    shifts = []
    for sk, payload in verify.items():
        try:
            surah = int(sk)
        except ValueError:
            continue
        af = api_cache.get(surah, {}).get("audio_file", {})
        audio_url = af.get("audio_url", "")
        ts = af.get("timestamps", [])
        for f in payload.get("flags", []):
            if not f["flag"].startswith("shift_"):
                continue
            if f.get("best_match_sim", 0) < SHIFT_SIM_THRESHOLD:
                continue
            verse_key = f["verse_key"]
            v_str = verse_key.split(":")[1]
            verse = int(v_str)
            offset = f["best_match_offset"]
            actual_v = verse + offset
            api_from, api_to = f.get("api_span_ms", [0, 0])
            shifts.append({
                "surah": surah,
                "verse": verse,
                "offset": offset,
                "actual_verse": actual_v,
                "best_match_verse": f["best_match_verse"],
                "sim_self": f.get("sim_self", 0),
                "best_sim": f.get("best_match_sim", 0),
                "transcribed": f.get("transcribed_normalized", ""),
                "canonical": f.get("canonical_normalized", ""),
                "api_from_ms": api_from,
                "api_to_ms": api_to,
                "audio_url": audio_url,
            })
    return shifts


def collect_drifts(diffs, api_cache):
    """Return list of dicts, one per drifted boundary."""
    drifts = []
    for surah, verse_list in diffs.items():
        af = api_cache.get(surah, {}).get("audio_file", {})
        audio_url = af.get("audio_url", "")
        for v in verse_list:
            delta = v.get("delta_to", 0)
            if abs(delta) < DRIFT_MS_THRESHOLD:
                continue
            verse_key = v.get("verse_key", "")
            try:
                vnum = int(verse_key.split(":")[1])
            except Exception:
                continue
            old_to = v["old_to"]
            new_to = v["new_to"]
            # Direction: positive delta (new > old) means API was EARLY
            # (subtitle flipped before the verse audibly ended); we push
            # the boundary later. Negative delta = API was LATE.
            direction = "EARLY" if delta > 0 else "LATE"
            # Audio window covering both original and corrected boundary
            # so the listener hears the drift directly.
            lo = min(old_to, new_to) - 1500
            hi = max(old_to, new_to) + 1500
            drifts.append({
                "surah": surah,
                "verse": vnum,
                "old_to_ms": old_to,
                "new_to_ms": new_to,
                "delta_ms": delta,
                "direction": direction,
                "audio_url": audio_url,
                "audio_window_lo_ms": lo,
                "audio_window_hi_ms": hi,
            })
    return drifts


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def render(verify, api_cache, shifts, drifts):
    out = []
    add = out.append

    add(f"# {RECITER_NAME} (reciter id {RECITER_ID}) — full timing analysis")
    add("")
    add("Comprehensive audit of the per-verse audio-to-translation timing data "
        f"served by `api.quran.com/api/v4/chapter_recitations/{RECITER_ID}/<surah>` "
        "for every surah in the recitation.")
    add("")
    add("- **Whole-verse shifts** are flagged when Whisper-large-v3 transcribes "
        f"the API span and the result matches a *neighbour* verse with "
        f"char-similarity ≥ {SHIFT_SIM_THRESHOLD:.2f} (and ≥ 0.20 better than "
        "the claimed verse). This is the most reliable signal — independent "
        "of CTC alignment.")
    add(f"- **Boundary drifts** are flagged when the silence-anchored hybrid "
        f"fix moves the API verse-end by ≥ {DRIFT_MS_THRESHOLD} ms (audibly "
        "perceptible).")
    add("")
    add("**Every finding below is independently verifiable by clicking the "
        "🔊 link** — it plays the exact disputed audio span in your browser "
        "via an HTML5 media-fragment URL (no player setup needed). The "
        "verse-page links open quran.com with this reciter preselected.")
    add("")
    add("---")
    add("")

    # ---- Headline ----
    add("## Headline")
    add("")
    n_shifts = len(shifts)
    n_drifts = len(drifts)
    surahs_with_shifts = sorted({s["surah"] for s in shifts})
    surahs_with_drifts = sorted({d["surah"] for d in drifts})
    surahs_either = sorted(set(surahs_with_shifts) | set(surahs_with_drifts))
    add(f"- **{n_shifts} confirmed whole-verse shifts** "
        f"(across {len(surahs_with_shifts)} surahs)")
    add(f"- **{n_drifts} drifted boundaries** ≥ {DRIFT_MS_THRESHOLD} ms "
        f"(across {len(surahs_with_drifts)} surahs)")
    add(f"- **{len(surahs_either)} surahs** have at least one issue; "
        f"**{114 - len(surahs_either)} surahs** are clean.")
    add("")

    # ---- Whole-verse shifts summary table ----
    add("## Whole-verse shifts — per-surah summary")
    add("")
    add("| surah | name | shifts | offsets | verses |")
    add("|------:|:-----|-------:|--------:|--------|")
    by_surah_shifts = defaultdict(list)
    for s in shifts:
        by_surah_shifts[s["surah"]].append(s)
    for surah in sorted(by_surah_shifts):
        items = by_surah_shifts[surah]
        offsets = sorted({s["offset"] for s in items},
                         key=lambda x: (abs(x), x))
        offsets_str = ", ".join(f"{o:+d}" for o in offsets)
        verses = fmt_verse_list([s["verse"] for s in items])
        add(f"| {surah} | {SURAH_NAMES.get(surah, '?')} | "
            f"{len(items)} | {offsets_str} | {verses} |")
    add("")

    # ---- Per-shift detail ----
    add("## Whole-verse shifts — per-verse evidence")
    add("")
    add("Each card below is one confirmed shift. The 🔊 link plays the "
        "exact API-claimed span; it should sound like the *Audio actually "
        "contains* verse, not the *API claims* verse.")
    add("")
    for surah in sorted(by_surah_shifts):
        items = by_surah_shifts[surah]
        add(f"### Surah {surah} — {SURAH_NAMES.get(surah, '?')} "
            f"({len(items)} shift{'s' if len(items) != 1 else ''})")
        add("")
        for s in items:
            v, av, off = s["verse"], s["actual_verse"], s["offset"]
            add(f"#### {surah}:{v} (offset {off:+d})")
            add(f"- API claims: [{surah}:{v}]({quran_com_url(surah, v)})")
            add(f"- Audio actually contains: "
                f"[{surah}:{av}]({quran_com_url(surah, av)})")
            if s["audio_url"]:
                add(f"- 🔊 [Listen "
                    f"({fmt_ms(s['api_from_ms'])}–{fmt_ms(s['api_to_ms'])})]"
                    f"({audio_span_url(s['audio_url'], s['api_from_ms'], s['api_to_ms'])})")
            add(f"- char-similarity: vs claimed `{s['sim_self']:.2f}` · "
                f"vs actual `{s['best_sim']:.2f}`")
            if s["transcribed"]:
                # Truncate Arabic to keep the markdown readable.
                t = s["transcribed"][:80]
                add(f"- Whisper heard: `{t}{'…' if len(s['transcribed']) > 80 else ''}`")
            add("")
        add("")

    # ---- Boundary drifts summary table ----
    add("## Boundary drifts — per-surah summary")
    add("")
    by_surah_drifts = defaultdict(list)
    for d in drifts:
        by_surah_drifts[d["surah"]].append(d)
    add("| surah | name | drifts | max |Δ| (ms) | direction |")
    add("|------:|:-----|-------:|--------------:|:----------|")
    for surah in sorted(by_surah_drifts):
        items = by_surah_drifts[surah]
        max_abs = max(abs(d["delta_ms"]) for d in items)
        directions = sorted({d["direction"] for d in items})
        if len(directions) == 1:
            dirstr = (f"{directions[0]} "
                      f"({'api flips before voice' if directions[0]=='EARLY' else 'api flips after voice'})")
        else:
            dirstr = "mixed"
        add(f"| {surah} | {SURAH_NAMES.get(surah, '?')} | "
            f"{len(items)} | {max_abs} | {dirstr} |")
    add("")

    # ---- Per-drift detail ----
    add("## Boundary drifts — per-verse evidence")
    add("")
    add("Each entry below is one verse-end boundary that the hybrid silence "
        "+ WhisperX fix moved by ≥ "
        f"{DRIFT_MS_THRESHOLD} ms. The 🔊 link plays a 3-second window "
        "around the boundary so you can hear the recitation crossing the "
        "originally-claimed time.")
    add("")
    for surah in sorted(by_surah_drifts):
        items = by_surah_drifts[surah]
        add(f"### Surah {surah} — {SURAH_NAMES.get(surah, '?')} "
            f"({len(items)} drifted boundary{'ies' if len(items)!=1 else ''})")
        add("")
        add("| verse-end | old `to` | new `to` | Δ ms | direction | listen |")
        add("|----------:|---------:|---------:|-----:|:----------|:-------|")
        for d in sorted(items, key=lambda x: x["verse"]):
            v = d["verse"]
            link = quran_com_url(surah, v)
            audio_link = (audio_span_url(d["audio_url"],
                                         d["audio_window_lo_ms"],
                                         d["audio_window_hi_ms"], pad_s=0.0)
                          if d["audio_url"] else "")
            audio_cell = f"[🔊]({audio_link})" if audio_link else "—"
            add(f"| [{surah}:{v}]({link}) | {fmt_ms(d['old_to_ms'])} "
                f"| {fmt_ms(d['new_to_ms'])} | {d['delta_ms']:+d} "
                f"| {d['direction']} | {audio_cell} |")
        add("")
        add("")

    # ---- Method ----
    add("## Method")
    add("")
    add("Every claim above can be reproduced from this repository:")
    add("")
    add("```bash")
    add("python analyze_tunaiji.py            # end-to-end pipeline")
    add("python experiments/build_tunaiji_analysis.py  # rebuild this report")
    add("```")
    add("")
    add(f"Confidence basis (see `experiments/AB_RESULTS.md` for the A/B "
        "sweep that compared three Whisper variants):")
    add("")
    add("- **Recall** (large-v3 baseline on the AB ground-truth set): 73 %")
    add("- **Precision**: 92 % (one false positive at threshold 0.70 "
        "across the AB set)")
    add("- **Cross-check**: a Quran-fine-tuned Whisper variant "
        "(`tarteel-ai/whisper-base-ar-quran`) hit 100 % precision on the "
        "same AB set, raising the *avg* best-match similarity on true "
        "shifts from 0.81 → 0.85. Re-running the verify step on Tunaiji "
        "with that model would tighten precision further; the shifts "
        "reported here are conservative.")
    add("")
    add("## Filing path")
    add("")
    add("The data lives in QUL (`Audio::Segment` records keyed by "
        f"recitation id {RECITER_ID}). Either route:")
    add("")
    add("- File a GitHub issue at "
        "<https://github.com/TarteelAI/quranic-universal-library/issues> "
        "with the per-surah `data/corrected_v2/surah_<N>_qul.csv` and a "
        "screen-recording of the demo player from `build_demo.py`.")
    add("- Or click *Send Access Request* at "
        "<https://qul.tarteel.ai/tools> for the *Audio Segments* "
        "resource and edit directly.")
    add("")
    add(f"_Generated by `experiments/build_tunaiji_analysis.py`._")

    return "\n".join(out) + "\n"


def main():
    print("loading inputs...")
    verify, api_cache, diffs = load_inputs()
    print(f"  verify: {len(verify)} surahs")
    print(f"  api_cache: {len(api_cache)} surahs")
    print(f"  diffs: {len(diffs)} surahs")

    shifts = collect_shifts(verify, api_cache)
    drifts = collect_drifts(diffs, api_cache)
    print(f"high-conf shifts: {len(shifts)}")
    print(f"drifted boundaries (>= {DRIFT_MS_THRESHOLD} ms): {len(drifts)}")

    md = render(verify, api_cache, shifts, drifts)
    OUT_PATH.write_text(md, encoding="utf-8")
    print(f"wrote {OUT_PATH}  ({len(md):,} chars)")


if __name__ == "__main__":
    main()
