"""
Read every reports/whisper_verify_r*.json and produce a single
human-readable summary table of confirmed verse-shift bugs across
reciters.

Output is also written to logs/findings_so_far.md so it can be
referenced from anywhere.

Usage:
    python summarize_findings.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
LOG_DIR = ROOT / "logs"

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

HIGH_CONF_SIM = 0.70


def find_files():
    # Tunaiji's report file is whisper_verify.json (no _r suffix because
    # he was the legacy default reciter for the project).
    legacy = ROOT / "reports" / "whisper_verify.json"
    if legacy.exists():
        yield 161, legacy
    for p in sorted(ROOT.glob("reports/whisper_verify_r*.json")):
        stem = p.stem  # e.g. whisper_verify_r4
        if stem.startswith("whisper_verify_r"):
            try:
                yield int(stem[len("whisper_verify_r"):]), p
            except ValueError:
                continue


def summarize(rid: int, path: Path):
    """Return dict {surah_str: {count, offsets, sample_verses}} for
    high-confidence shifts only."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for s, res in data.items():
        if not isinstance(res, dict):
            continue
        flags = res.get("flags", [])
        high = [f for f in flags
                if f.get("flag", "").startswith("shift")
                and f.get("best_match_sim", 0) >= HIGH_CONF_SIM]
        if not high:
            continue
        out[s] = {
            "count": len(high),
            "offsets": sorted(set(f["best_match_offset"] for f in high)),
            "verses": [f["verse_key"] for f in high],
        }
    return out


def fmt_verse_runs(verse_keys):
    """Compress consecutive verse numbers into N-M ranges within each surah."""
    nums = sorted(set(int(vk.split(":")[1]) for vk in verse_keys))
    if not nums:
        return ""
    runs = [[nums[0]]]
    for n in nums[1:]:
        if n == runs[-1][-1] + 1:
            runs[-1].append(n)
        else:
            runs.append([n])
    return ", ".join(str(r[0]) if len(r) == 1 else f"{r[0]}-{r[-1]}" for r in runs)


def main():
    LOG_DIR.mkdir(exist_ok=True)
    out_path = LOG_DIR / "findings_so_far.md"

    lines = ["# Confirmed verse-shift findings across reciters",
             f"(High-confidence shifts: Whisper-transcription char-similarity "
             f">= {HIGH_CONF_SIM} vs a neighbour verse, via "
             f"`reports/whisper_verify_r<id>.json`)", "",
             "| reciter | id | surah | n_shifts | verses | offsets |",
             "|---------|---:|------:|---------:|--------|--------:|"]

    total_per_reciter = {}
    for rid, path in find_files():
        summary = summarize(rid, path)
        if not summary:
            continue
        n = sum(s["count"] for s in summary.values())
        total_per_reciter[rid] = n
        rname = NAMES.get(rid, f"r{rid}")
        for surah_str in sorted(summary, key=lambda x: int(x)):
            d = summary[surah_str]
            offsets_str = ", ".join(f"{o:+d}" for o in d["offsets"])
            lines.append(f"| {rname} | {rid} | {surah_str} | "
                         f"{d['count']} | {fmt_verse_runs(d['verses'])} | {offsets_str} |")

    lines.append("")
    lines.append(f"## Per-reciter totals (only reciters with at least one shift)")
    lines.append("")
    lines.append(f"| reciter | id | total high-conf shifts |")
    lines.append(f"|---------|---:|----------------------:|")
    for rid in sorted(total_per_reciter, key=lambda r: -total_per_reciter[r]):
        lines.append(f"| {NAMES.get(rid, f'r{rid}')} | {rid} | {total_per_reciter[rid]} |")

    text = "\n".join(lines)
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print()
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
