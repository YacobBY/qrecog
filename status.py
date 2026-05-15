"""
Live status view of the multi-reciter pipeline. Shows for each reciter:
  * audio downloaded / aligned / healed / fixed / verified
  * confirmed shifts (via Whisper-verify)
  * estimated completion percent

Run it any time -- it just reads files.

Usage:
    python status.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"

NAMES = {
    1: "AbdulBaset AbdulSamad",
    2: "AbdulBaset AbdulSamad (alt)",
    3: "Abdur-Rahman as-Sudais",
    4: "Abu Bakr al-Shatri",
    5: "Hani ar-Rifai",
    6: "Mahmoud Khalil Al-Husary",
    7: "Mishari Rashid al-`Afasy",
    8: "Mohamed Siddiq al-Minshawi",
    9: "Mohamed Siddiq al-Minshawi (alt)",
    10: "Sa`ud ash-Shuraym",
    11: "Mohamed al-Tablawi",
    12: "Mahmoud Khalil Al-Husary (alt)",
    161: "Khalifah Al Tunaiji",
}


def reciter_paths(rid):
    if rid == 161:
        return {"audio": ROOT / "audio",
                "data": ROOT / "data",
                "wx": ROOT / "data" / "whisperx",
                "healed": ROOT / "data" / "whisperx_healed",
                "corrected": ROOT / "data" / "corrected_v2"}
    base = ROOT / "reciters" / f"r{rid}"
    return {"audio": base / "audio",
            "data": base / "data",
            "wx": base / "data" / "whisperx",
            "healed": base / "data" / "whisperx_healed",
            "corrected": base / "data" / "corrected_v2"}


def count_files(p, glob="*.json"):
    if not p.exists():
        return 0
    return len(list(p.glob(glob)))


def shifts_summary(rid):
    suffix = "" if rid == 161 else f"_r{rid}"
    p = REPORTS / f"whisper_verify{suffix}.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    n_surahs_verified = len(data)
    high_conf = []
    for s, res in data.items():
        if not isinstance(res, dict):
            continue
        for f in res.get("flags", []):
            if (f.get("flag", "").startswith("shift")
                    and f.get("best_match_sim", 0) >= 0.7):
                high_conf.append((s, f["verse_key"], f["best_match_offset"]))
    return {"n_verified": n_surahs_verified, "n_shifts": len(high_conf),
            "shifts": high_conf}


def main():
    rows = []
    for rid in sorted(NAMES, key=lambda x: (x != 161, x)):
        paths = reciter_paths(rid)
        if not paths["audio"].exists():
            continue
        audio_count = count_files(paths["audio"], "surah_*.mp3")
        wx_count = count_files(paths["wx"], "surah_*_force_v2.json")
        healed_count = count_files(paths["healed"], "surah_*.json")
        corrected_count = count_files(paths["corrected"], "surah_*_corrected.json")
        ss = shifts_summary(rid)
        verified = ss["n_verified"] if ss else 0
        n_shifts = ss["n_shifts"] if ss else 0
        rows.append({
            "rid": rid,
            "name": NAMES[rid],
            "audio": audio_count,
            "wx": wx_count,
            "healed": healed_count,
            "corrected": corrected_count,
            "verified": verified,
            "n_shifts": n_shifts,
        })

    print(f"{'rid':>4}  {'name':>30}  {'audio':>5}  {'wx':>4}  {'heal':>4}  "
          f"{'fix':>4}  {'ver':>4}  {'shifts':>6}")
    print("-" * 80)
    for r in rows:
        print(f"{r['rid']:>4}  {r['name']:>30}  {r['audio']:>5}  "
              f"{r['wx']:>4}  {r['healed']:>4}  {r['corrected']:>4}  "
              f"{r['verified']:>4}  {r['n_shifts']:>6}")


if __name__ == "__main__":
    main()
