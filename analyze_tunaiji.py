"""
analyze_tunaiji.py
==================

Single-file end-to-end analysis pipeline for Khalifah Al Tunaiji
(reciter id 161 on quran.com). Run it once:

    python analyze_tunaiji.py

It does these steps in order:

  1. fetch_all.py            -- audio MP3s + API timestamps + canonical text
  2. batch_align.py          -- WhisperX forced alignment (jonatasgrosman wav2vec2)
  3. heal_alignment.py       -- chronological-order healing pass
  4. generate_fix_whisperx.py -- hybrid fix (ffmpeg silences + WX anchors)
  5. detect_shifts.py        -- WX-vs-API IoU shift detector
  6. verify_with_whisper.py  -- Whisper-transcription cross-check (slowest;
                                catches whole-verse shifts CTC missed)
  7. summarize and print findings table

Each step is idempotent -- if its output already exists, the underlying
script skips and re-running this orchestrator just re-prints the report.

Output artefacts (all under repo root):
  audio/surah_<NNN>.mp3
  data/surah_<N>_tunaiji.json     -- API timestamps
  data/surah_<N>_verses.json      -- canonical text
  data/whisperx/surah_<N>_force_v2.json
  data/whisperx_healed/surah_<N>.json
  data/corrected_v2/surah_<N>_*.{json,csv}
  reports/whisper_verify.json     -- Whisper-verify findings
  reports/tunaiji_findings.md     -- final human-readable report

Flags:
  --skip-whisper-verify    skip the slowest step (CTC pipeline only)
  --whisper-model SIZE     medium (default, ~30 min/full-quran) or large-v3
  --only-step N            run only step N (1-7) for debugging
"""
import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
PY = sys.executable
RECITER_ID = 161  # Khalifah Al Tunaiji (the constant our pipeline calls
                  # LEGACY_RECITER_ID -- kept as the default everywhere)

# Where each step's output ends up.  Used to print a status table at the
# top so you can see what's already done before kicking off the slow
# steps.
def out_paths():
    return {
        "audio_mp3":         ROOT / "audio",
        "api_json":          ROOT / "data",
        "wx_json":           ROOT / "data" / "whisperx",
        "wx_healed":         ROOT / "data" / "whisperx_healed",
        "corrected_v2":      ROOT / "data" / "corrected_v2",
        "verify_report":     ROOT / "reports" / "whisper_verify.json",
        "shifts_report":     ROOT / "reports" / "verse_shifts.json",
        "summary_md":        ROOT / "reports" / "tunaiji_findings.md",
    }


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def banner(msg: str):
    print()
    print(f"=== [{now()}] {msg} ===", flush=True)


def run(cmd, label: str, allow_fail: bool = False) -> bool:
    """Run a subprocess and stream its stdout. Returns True on success."""
    banner(f"step: {label}")
    print(f"$ {' '.join(str(c) for c in cmd)}", flush=True)
    t0 = time.monotonic()
    proc = subprocess.run(cmd, encoding="utf-8", errors="replace")
    elapsed = time.monotonic() - t0
    ok = proc.returncode == 0
    print(f"-- {label}: {'OK' if ok else 'FAILED'} in {elapsed:.1f}s "
          f"(rc={proc.returncode})", flush=True)
    if not ok and not allow_fail:
        print(f"!! aborting because step '{label}' failed and is not "
              f"marked allow_fail")
        sys.exit(proc.returncode)
    return ok


def count(p: Path, glob: str) -> int:
    if not p.exists():
        return 0
    return len(list(p.glob(glob)))


def print_status_table():
    p = out_paths()
    print()
    print("Pipeline state:")
    print(f"  audio mp3s              : {count(p['audio_mp3'], 'surah_*.mp3'):>3} / 114")
    print(f"  API timestamp jsons     : {count(p['api_json'], 'surah_*_tunaiji.json'):>3} / 114")
    print(f"  WhisperX alignments     : {count(p['wx_json'], 'surah_*_force_v2.json'):>3} / 114")
    print(f"  Healed alignments       : {count(p['wx_healed'], 'surah_*.json'):>3} / 114")
    print(f"  Hybrid-fix corrected    : {count(p['corrected_v2'], 'surah_*_corrected.json'):>3} / 114")
    print(f"  Whisper-verify report   : "
          f"{'present' if p['verify_report'].exists() else 'MISSING'}")
    print()


# ------------------------------------------------------------------
# Final report aggregation
# ------------------------------------------------------------------

# Surah names for the report
SURAH_NAMES = {
    1: "Al-Fatihah", 2: "Al-Baqarah", 3: "Aal-Imran", 4: "An-Nisa",
    5: "Al-Maidah", 6: "Al-Anam", 7: "Al-Araf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf", 13: "Ar-Rad",
    14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl", 17: "Al-Isra",
    18: "Al-Kahf", 19: "Maryam", 20: "Taha", 21: "Al-Anbiya",
    22: "Al-Hajj", 23: "Al-Muminun", 24: "An-Nur", 25: "Al-Furqan",
    26: "Ash-Shuara", 27: "An-Naml", 28: "Al-Qasas", 29: "Al-Ankabut",
    30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah", 33: "Al-Ahzab",
    34: "Saba", 35: "Fatir", 36: "Ya-Sin", 37: "As-Saffat", 38: "Sad",
    39: "Az-Zumar", 40: "Ghafir", 41: "Fussilat", 42: "Ash-Shuraa",
    43: "Az-Zukhruf", 44: "Ad-Dukhan", 45: "Al-Jathiyah", 46: "Al-Ahqaf",
    47: "Muhammad", 48: "Al-Fath", 49: "Al-Hujurat", 50: "Qaf",
    51: "Adh-Dhariyat", 52: "At-Tur", 53: "An-Najm", 54: "Al-Qamar",
    55: "Ar-Rahman", 56: "Al-Waqiah", 57: "Al-Hadid", 58: "Al-Mujadilah",
    59: "Al-Hashr", 60: "Al-Mumtahanah", 61: "As-Saff", 62: "Al-Jumuah",
    63: "Al-Munafiqun", 64: "At-Taghabun", 65: "At-Talaq",
    66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam", 69: "Al-Haqqah",
    70: "Al-Maarij", 71: "Nuh", 72: "Al-Jinn", 73: "Al-Muzzammil",
    74: "Al-Muddathir", 75: "Al-Qiyamah", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "An-Naba", 79: "An-Naziat", 80: "Abasa",
    81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin",
    84: "Al-Inshiqaq", 85: "Al-Buruj", 86: "At-Tariq", 87: "Al-Ala",
    88: "Al-Ghashiyah", 89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams",
    92: "Al-Layl", 93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin",
    96: "Al-Alaq", 97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah",
    100: "Al-Adiyat", 101: "Al-Qariah", 102: "At-Takathur",
    103: "Al-Asr", 104: "Al-Humazah", 105: "Al-Fil", 106: "Quraysh",
    107: "Al-Maun", 108: "Al-Kawthar", 109: "Al-Kafirun",
    110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas", 113: "Al-Falaq",
    114: "An-Nas",
}

WHISPER_VERIFY_HIGH_CONF_SIM = 0.70


def fmt_verse_runs(nums):
    """Compress consecutive verse numbers into N-M ranges."""
    nums = sorted(set(nums))
    if not nums:
        return ""
    runs = [[nums[0]]]
    for n in nums[1:]:
        if n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}-{r[-1]}"
                     for r in runs)


def aggregate_findings():
    p = out_paths()

    # 1. Whisper-verify shifts (whole-verse misassignments)
    shifts_per_surah = {}
    if p["verify_report"].exists():
        try:
            data = json.loads(p["verify_report"].read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for s_str, res in data.items():
            if not isinstance(res, dict):
                continue
            high = []
            for f in res.get("flags", []):
                if (f.get("flag", "").startswith("shift")
                        and f.get("best_match_sim", 0) >= WHISPER_VERIFY_HIGH_CONF_SIM):
                    high.append({
                        "verse_key": f["verse_key"],
                        "offset":    f["best_match_offset"],
                        "sim":       round(f["best_match_sim"], 2),
                        "matches":   f.get("best_match_verse"),
                    })
            if high:
                shifts_per_surah[int(s_str)] = high

    # 2. Hybrid-fix boundary corrections (edge drift)
    edges_per_surah = {}
    for diff_path in sorted(p["corrected_v2"].glob("surah_*_diff.json"),
                            key=lambda x: int(x.stem.split("_")[1])):
        surah = int(diff_path.stem.split("_")[1])
        try:
            diffs = json.loads(diff_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        edits = [d for d in diffs if d["delta_to"] != 0]
        if not edits:
            continue
        edges_per_surah[surah] = edits

    return shifts_per_surah, edges_per_surah


def write_report(shifts_per_surah, edges_per_surah):
    out = []
    out.append(f"# Tunaiji (reciter 161) — mistiming findings")
    out.append(f"_Generated {now()}_")
    out.append("")

    out.append("## Whole-verse shifts (Whisper-verify, sim ≥ 0.70)")
    out.append("")
    if not shifts_per_surah:
        out.append("_None._")
    else:
        out.append("| surah | name | n_shifts | verses | offsets |")
        out.append("|------:|:-----|---------:|--------|--------:|")
        for s in sorted(shifts_per_surah):
            entries = shifts_per_surah[s]
            verses = fmt_verse_runs(int(e["verse_key"].split(":")[1])
                                    for e in entries)
            offsets = ", ".join(f"{o:+d}" for o in
                                sorted(set(e["offset"] for e in entries)))
            out.append(f"| {s} | {SURAH_NAMES.get(s, '')} | "
                       f"{len(entries)} | {verses} | {offsets} |")

    out.append("")
    out.append("## Boundary drift (hybrid fix, ≥ 150 ms)")
    out.append("")
    if not edges_per_surah:
        out.append("_None._")
    else:
        out.append("| surah | name | n_boundaries | verses (left of boundary) | "
                   "max |Δ| (ms) | direction |")
        out.append("|------:|:-----|-------------:|---------------------------|"
                   "-------------:|:----------|")
        for s in sorted(edges_per_surah):
            edits = edges_per_surah[s]
            verse_nums = sorted(set(int(e["verse_key"].split(":")[1])
                                    for e in edits))
            max_d = max(abs(e["delta_to"]) for e in edits if e["delta_to"] != 0)
            pos = sum(1 for e in edits if e["delta_to"] > 0)
            neg = sum(1 for e in edits if e["delta_to"] < 0)
            if pos and neg:
                direction = "mixed"
            elif pos:
                direction = "EARLY (api flips before voice)"
            else:
                direction = "LATE (api flips after voice)"
            out.append(f"| {s} | {SURAH_NAMES.get(s, '')} | "
                       f"{len(edits)} | {fmt_verse_runs(verse_nums)} | "
                       f"{max_d} | {direction} |")

    # Aggregate stats
    n_shift_surahs = len(shifts_per_surah)
    n_shift_total = sum(len(v) for v in shifts_per_surah.values())
    n_edge_surahs = len(edges_per_surah)
    n_edge_total = sum(len(v) for v in edges_per_surah.values())

    out.append("")
    out.append("## Aggregate")
    out.append("")
    out.append(f"- Surahs with confirmed whole-verse shift(s): **{n_shift_surahs}**")
    out.append(f"- Total confirmed whole-verse shifts: **{n_shift_total}**")
    out.append(f"- Surahs with boundary drift: **{n_edge_surahs}**")
    out.append(f"- Total boundary drifts >= 150 ms: **{n_edge_total}**")

    text = "\n".join(out) + "\n"
    out_paths()["summary_md"].parent.mkdir(parents=True, exist_ok=True)
    out_paths()["summary_md"].write_text(text, encoding="utf-8")
    return text


# ------------------------------------------------------------------
# Step runners
# ------------------------------------------------------------------

def step_fetch():
    return run([PY, str(ROOT / "fetch_all.py")], "fetch")


def step_align():
    return run([PY, str(ROOT / "batch_align.py"),
                "--reciter-id", str(RECITER_ID)], "align")


def step_heal():
    return run([PY, str(ROOT / "heal_alignment.py"),
                "--reciter-id", str(RECITER_ID)], "heal")


def step_fix():
    return run([PY, str(ROOT / "generate_fix_whisperx.py"),
                "--reciter-id", str(RECITER_ID)], "fix")


def step_detect():
    return run([PY, str(ROOT / "detect_shifts.py"),
                "--reciter-id", str(RECITER_ID)], "detect", allow_fail=True)


def step_verify(model_size: str):
    cmd = [PY, str(ROOT / "verify_with_whisper.py"),
           "--reciter-id", str(RECITER_ID),
           "--model-size", model_size]
    return run(cmd, "verify", allow_fail=True)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--whisper-model", default="medium",
                    help="medium (~30 min) or large-v3 (more accurate, slower)")
    ap.add_argument("--skip-whisper-verify", action="store_true",
                    help="skip step 6 (whole-verse shift cross-check)")
    ap.add_argument("--only-step", type=int, default=None,
                    help="run only step 1..7 (debugging)")
    args = ap.parse_args()

    print(f"analyze_tunaiji.py — reciter {RECITER_ID} (Khalifah Al Tunaiji)")
    print_status_table()

    steps = [
        (1, "fetch",  step_fetch),
        (2, "align",  step_align),
        (3, "heal",   step_heal),
        (4, "fix",    step_fix),
        (5, "detect", step_detect),
    ]
    if not args.skip_whisper_verify:
        steps.append((6, "verify", lambda: step_verify(args.whisper_model)))

    for n, name, fn in steps:
        if args.only_step is not None and args.only_step != n:
            continue
        fn()

    # Step 7: aggregate and print
    if args.only_step is not None and args.only_step != 7:
        return

    banner("step: aggregate findings")
    shifts, edges = aggregate_findings()
    text = write_report(shifts, edges)
    print(text)
    print(f"Wrote {out_paths()['summary_md']}")


if __name__ == "__main__":
    main()
