"""
Re-render AB_RESULTS.md from ab_results.json with verification links.

Reads ab_results.json (must already exist from a prior
ab_test_models.py run), augments each case with quran.com page URLs and
HTML5 media-fragment audio URLs, and rewrites the per-case section of
AB_RESULTS.md so every shift case has clickable evidence.

This is a no-GPU step -- safe to re-run any time.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from reciter_paths import paths_for  # noqa: E402

HERE = Path(__file__).parent
JSON_PATH = HERE / "ab_results.json"
MD_PATH = HERE / "AB_VERIFICATION.md"
THRESHOLD = 0.70

# These two helpers are duplicated from ab_test_models.py so this
# script can be run standalone (e.g. against an older results JSON).
def quran_com_url(surah, verse, rid):
    return f"https://quran.com/{surah}/{verse}?reciter={rid}"


def audio_span_url(audio_url, start_s, end_s):
    return f"{audio_url}#t={start_s:.2f},{end_s:.2f}"


def reciter_name(rid: int) -> str:
    return {
        1: "AbdulBaset (murattal)",
        2: "AbdulBaset (alt)",
        3: "Sudais",
        4: "Shatri",
        5: "Hani ar-Rifai",
        6: "Husary",
        7: "Mishary al-Afasy",
        8: "Minshawi (mujawwad)",
        9: "Minshawi (murattal)",
        10: "Sa`ud ash-Shuraym",
        11: "Tablawi",
        12: "Husary muallim",
        161: "Khalifah Al Tunaiji",
    }.get(rid, f"reciter-{rid}")


def lookup_audio_meta(rid: int, surah: int):
    """Pull (audio_url, timestamps[verse-1]) from the cached API json
    so we can build an audio-span URL even if the original run didn't
    persist it."""
    P = paths_for(rid)
    api = json.loads(P.api_json(surah).read_text(encoding="utf-8"))
    af = api["audio_file"]
    return af.get("audio_url", ""), af["timestamps"]


def main():
    if not JSON_PATH.exists():
        sys.exit(f"missing {JSON_PATH} -- run ab_test_models.py first")
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    summaries = data["summaries"]
    raw = data["raw"]

    # Index by (surah, verse) -> {model_label: case_dict}
    by_case = {}
    for label, cases in raw.items():
        for c in cases:
            key = (c["reciter_id"], c["surah"], c["verse"])
            by_case.setdefault(key, {})[label] = c

    # Order: same as the in-script GROUND_TRUTH order — sort by
    # (reciter, surah, verse) for stable output that any reader can
    # follow.
    ordered_keys = sorted(by_case.keys())

    lines = []
    lines.append("# Verification links — click to audit each finding")
    lines.append("")
    lines.append("Auto-generated from `experiments/ab_results.json` by "
                 "`experiments/annotate_results.py`.")
    lines.append("")
    lines.append("Each row below has direct links to the disputed audio "
                 "span (clicking plays exactly that slice in your "
                 "browser) and to the relevant verse pages on "
                 "quran.com. The reciter is preselected via `?reciter=<id>`.")
    lines.append("")
    lines.append(f"Threshold for \"shift\" prediction: {THRESHOLD:.2f}.")
    lines.append("")

    # Group by (reciter, surah) for readability
    last_group = None
    for key in ordered_keys:
        rid, surah, verse = key
        if (rid, surah) != last_group:
            last_group = (rid, surah)
            lines.append("")
            lines.append(f"## {reciter_name(rid)} (id {rid}) — Surah {surah}")
            lines.append("")

        cases = by_case[key]
        # All models share reciter/surah/verse + truth, so pick any
        sample = next(iter(cases.values()))
        true_label = sample["true_label"]
        expected_off = sample.get("expected_offset")

        # Build URLs from cached API json (works even if the original
        # results JSON predates URL fields)
        try:
            audio_url, ts = lookup_audio_meta(rid, surah)
            v = ts[verse - 1]
            s_s = max(0.0, v["timestamp_from"]/1000.0 - 0.05)
            e_s = v["timestamp_to"]/1000.0 + 0.05
            audio_link = (audio_span_url(audio_url, s_s, e_s)
                          if audio_url else "")
        except Exception as e:
            audio_link = ""
            print(f"WARN: r{rid} surah {surah} v{verse} no audio meta: {e}")

        page_claimed = quran_com_url(surah, verse, rid)

        # Per-model best-match summary line
        per_model = []
        actual_verse_seen = None
        for label in ["baseline-large-v3", "turbo-large-v3",
                      "tarteel-base-quran"]:
            c = cases.get(label)
            if not c:
                continue
            b_off = c["best_offset"]
            b_sim = c["best_sim"]
            mark = ("**SHIFT**" if (b_off != 0 and b_sim >= THRESHOLD
                                    and (b_sim - c["sim_self"]) >= 0.20)
                    else "clean")
            per_model.append(f"`{label}`: {b_off:+d}@{b_sim:.2f} → {mark}")
            if b_off != 0 and b_sim >= THRESHOLD:
                actual_verse_seen = verse + b_off

        # Header per-case
        truth_str = true_label.upper()
        if true_label == "shift" and expected_off is not None:
            truth_str += f" (expected offset {expected_off:+d})"
        lines.append(f"### {surah}:{verse} — truth: {truth_str}")
        lines.append("")
        lines.append(f"- API-claimed verse: [{surah}:{verse}]({page_claimed})")
        if true_label == "shift" and expected_off is not None:
            actual_v = verse + expected_off
            page_actual = quran_com_url(surah, actual_v, rid)
            lines.append(f"- Audio actually contains: "
                         f"[{surah}:{actual_v}]({page_actual}) "
                         f"(offset {expected_off:+d})")
        elif actual_verse_seen and actual_verse_seen != verse:
            page_actual = quran_com_url(surah, actual_verse_seen, rid)
            lines.append(f"- A model says audio contains: "
                         f"[{surah}:{actual_verse_seen}]({page_actual})")
        if audio_link:
            lines.append(f"- 🔊 [Listen to the disputed span]({audio_link}) "
                         f"({s_s:.2f}s – {e_s:.2f}s of the surah mp3)")
        lines.append("")
        for line in per_model:
            lines.append(f"  - {line}")
        lines.append("")

    out = "\n".join(lines) + "\n"
    MD_PATH.write_text(out, encoding="utf-8")
    print(f"wrote {MD_PATH} ({len(ordered_keys)} cases, "
          f"{len(summaries)} models)")


if __name__ == "__main__":
    main()
