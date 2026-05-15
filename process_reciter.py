"""
End-to-end pipeline for one reciter: fetch -> align -> heal -> fix ->
detect -> Whisper-verify (suspect surahs first, then everything else).

All progress + findings are tee'd to a per-reciter log file at
  logs/r<reciter_id>.log
plus appended to a master ndjson at
  logs/master.ndjson
so a separate watcher can tail progress / aggregate later.

Usage:
    python process_reciter.py <reciter_id> [--name "..."]
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def append_master(event: dict):
    event = {"ts": now(), **event}
    with (LOG_DIR / "master.ndjson").open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


class Tee:
    def __init__(self, log_path):
        self.log = open(log_path, "a", encoding="utf-8")

    def write(self, msg):
        line = f"[{now()}] {msg}"
        print(line, flush=True)
        self.log.write(line + "\n")
        self.log.flush()


def run(cmd, tee, label):
    tee.write(f"$ {' '.join(str(c) for c in cmd)}")
    t0 = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    elapsed = time.monotonic() - t0
    if proc.returncode != 0:
        tee.write(f"  FAILED ({label}) rc={proc.returncode} in {elapsed:.1f}s")
        if proc.stdout:
            tee.write(f"  stdout: {proc.stdout[-1500:]}")
        if proc.stderr:
            tee.write(f"  stderr: {proc.stderr[-1500:]}")
        return False, proc.stdout, proc.stderr
    tee.write(f"  OK ({label}) in {elapsed:.1f}s")
    return True, proc.stdout, proc.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reciter_id", type=int)
    ap.add_argument("--name", default="")
    ap.add_argument("--skip-whisper-verify", action="store_true",
                    help="skip the slow Whisper-verify pass (CTC-only run)")
    ap.add_argument("--whisper-model", default="medium",
                    help="model size for verify pass: medium (fast) or "
                         "large-v3 (more accurate)")
    args = ap.parse_args()

    rid = args.reciter_id
    log_path = LOG_DIR / f"r{rid}.log"
    tee = Tee(log_path)
    py = sys.executable
    repo = ROOT

    tee.write(f"=== reciter {rid} ({args.name or '?'}) -- pipeline start ===")
    append_master({"reciter_id": rid, "name": args.name, "phase": "start"})

    t_total = time.monotonic()

    # 1. Fetch
    ok, _, _ = run([py, str(repo / "fetch_reciter.py"), str(rid)], tee, "fetch")
    if not ok:
        append_master({"reciter_id": rid, "phase": "fetch_fail"})
        return

    # 2. Batch align
    ok, _, _ = run([py, str(repo / "batch_align.py"),
                    "--reciter-id", str(rid)], tee, "align")
    if not ok:
        append_master({"reciter_id": rid, "phase": "align_fail"})
        return

    # 3. Heal
    ok, _, _ = run([py, str(repo / "heal_alignment.py"),
                    "--reciter-id", str(rid)], tee, "heal")
    if not ok:
        append_master({"reciter_id": rid, "phase": "heal_fail"})
        # continue: heal failure isn't fatal

    # 4. Detect shifts (CTC-based)
    ok, stdout, _ = run([py, str(repo / "detect_shifts.py"),
                         "--reciter-id", str(rid)], tee, "detect")
    if ok:
        # Pull summary stats from stdout
        for line in stdout.splitlines()[-20:]:
            tee.write(f"  detect: {line}")

    # 5. Generate fix
    ok, stdout, _ = run([py, str(repo / "generate_fix_whisperx.py"),
                         "--reciter-id", str(rid)], tee, "fix")
    if ok:
        # Tail last 5 lines
        for line in stdout.splitlines()[-5:]:
            tee.write(f"  fix: {line}")

    # 6. Identify suspect surahs to send to Whisper-verify (the slow step).
    # Anything where the fix generator made a >=500 ms correction OR the
    # detector flagged STRONG/WEAK is worth Whisper-verifying.
    suspect = set()
    summary_path = repo / "reciters" / f"r{rid}" / "data" / "corrected_v2" / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        for s in summary:
            if s.get("max_delta_to", 0) >= 500 or s.get("max_delta_from", 0) >= 500:
                suspect.add(s["surah"])
    detector_path = repo / "reports" / f"verse_shifts_r{rid}.json"
    if detector_path.exists():
        det = json.loads(detector_path.read_text(encoding="utf-8"))
        for s_str, res in det.get("results", {}).items():
            for f in res.get("flags", []):
                if f.get("confidence") in ("STRONG", "WEAK"):
                    suspect.add(int(s_str))

    tee.write(f"=== {len(suspect)} suspect surahs for Whisper-verify pass: "
              f"{sorted(suspect)} ===")
    append_master({"reciter_id": rid, "phase": "after_detect",
                   "suspect_surahs": sorted(suspect)})

    if args.skip_whisper_verify:
        tee.write("skipping Whisper-verify (--skip-whisper-verify)")
    else:
        # First pass: suspects with the chosen model size
        if suspect:
            ok, stdout, _ = run([py, str(repo / "verify_with_whisper.py"),
                                 "--reciter-id", str(rid),
                                 "--model-size", args.whisper_model,
                                 "--verbose"]
                                + [str(s) for s in sorted(suspect)],
                                tee, "verify-suspects")
            if ok:
                # Capture final summary line
                for line in stdout.splitlines()[-10:]:
                    tee.write(f"  verify: {line}")

        # Second pass: everything else (small surahs are fast; this catches
        # bugs the CTC pipeline missed, like Mishary's Surah 37 which had
        # no STRONG/WEAK detector flag but was rife with shifts)
        all_surahs = set(range(1, 115))
        remaining = sorted(all_surahs - suspect)
        if remaining:
            tee.write(f"=== Whisper-verify remaining {len(remaining)} "
                      f"surahs ===")
            ok, stdout, _ = run([py, str(repo / "verify_with_whisper.py"),
                                 "--reciter-id", str(rid),
                                 "--model-size", args.whisper_model]
                                + [str(s) for s in remaining],
                                tee, "verify-rest")
            if ok:
                for line in stdout.splitlines()[-5:]:
                    tee.write(f"  verify: {line}")

    # 7. Aggregate findings into a per-reciter summary
    findings = aggregate_findings(rid)
    tee.write(f"=== final findings ===")
    tee.write(json.dumps(findings, ensure_ascii=False, indent=2))
    append_master({"reciter_id": rid, "phase": "done",
                   "findings": findings})

    elapsed = time.monotonic() - t_total
    tee.write(f"=== reciter {rid} done in {elapsed/60:.1f} min ===")


def aggregate_findings(rid: int):
    """Pull together CTC detector + fix + Whisper-verify into a single dict."""
    repo = ROOT
    out = {"reciter_id": rid}

    # Whisper-verify: which surahs have shift_+N or shift_-N flags
    wv_suffix = "" if rid == 161 else f"_r{rid}"
    wv_path = repo / "reports" / f"whisper_verify{wv_suffix}.json"
    wv = {}
    if wv_path.exists():
        try:
            wv_raw = json.loads(wv_path.read_text(encoding="utf-8"))
        except Exception:
            wv_raw = {}
        # Aggregate per surah: count of confirmed shifts
        for s_str, res in wv_raw.items():
            flags = res.get("flags", []) if isinstance(res, dict) else []
            shift_flags = [f for f in flags
                           if isinstance(f.get("flag", ""), str)
                           and f["flag"].startswith("shift")
                           and f.get("best_match_sim", 0) >= 0.7]
            if shift_flags:
                wv[s_str] = {
                    "n_shifts_high_conf": len(shift_flags),
                    "verses": [{"verse_key": f["verse_key"],
                                "best_match_offset": f["best_match_offset"],
                                "best_match_sim": f["best_match_sim"]}
                               for f in shift_flags[:20]],
                }
    out["whisper_verify_shifts"] = wv

    # Hybrid fix: largest correction per surah (only verse-edge drift)
    sum_path = repo / "reciters" / f"r{rid}" / "data" / "corrected_v2" / "summary.json"
    if rid == 161:
        sum_path = repo / "data" / "corrected_v2" / "summary.json"
    fix_summary = []
    if sum_path.exists():
        for s in json.loads(sum_path.read_text(encoding="utf-8")):
            if s["n_corrected_boundaries"] > 0:
                fix_summary.append({
                    "surah": s["surah"],
                    "n_corrected": s["n_corrected_boundaries"],
                    "max_delta_ms": s["max_delta_to"],
                })
    fix_summary.sort(key=lambda r: -r["max_delta_ms"])
    out["edge_drift_corrections"] = fix_summary[:30]

    return out


if __name__ == "__main__":
    main()
