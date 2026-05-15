"""
Sequentially run process_reciter.py for every available reciter on
quran.com (excluding ones already processed). Each run logs to its own
file and to logs/master.ndjson.

Run order is small-data-first so we get quick wins:
  4 (Shatri), 5 (Hani), 11 (Tablawi), 6 (Husary), 12 (Husary alt),
  10 (Shuraym), 9 (Minshawi alt), 8 (Minshawi), 3 (Sudais),
  2 (AbdulBaset alt), 1 (AbdulBaset)
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

RECITERS = [
    (4,  "Abu Bakr al-Shatri"),
    (5,  "Hani ar-Rifai"),
    (11, "Mohamed al-Tablawi"),
    (6,  "Mahmoud Khalil Al-Husary"),
    (12, "Mahmoud Khalil Al-Husary (alt)"),
    (10, "Sa`ud ash-Shuraym"),
    (9,  "Mohamed Siddiq al-Minshawi (alt)"),
    (8,  "Mohamed Siddiq al-Minshawi"),
    (3,  "Abdur-Rahman as-Sudais"),
    (2,  "AbdulBaset AbdulSamad (alt)"),
    (1,  "AbdulBaset AbdulSamad"),
]


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--whisper-model", default="medium")
    ap.add_argument("--skip-whisper-verify", action="store_true")
    ap.add_argument("--start-from", type=int, default=0,
                    help="skip the first N reciters in the queue")
    args = ap.parse_args()

    master_log = LOG_DIR / "run_all_reciters.log"
    py = sys.executable

    for i, (rid, name) in enumerate(RECITERS):
        if i < args.start_from:
            continue
        line = f"[{now()}] === reciter {rid} ({name}) starting ==="
        print(line, flush=True)
        with master_log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        t0 = time.monotonic()
        cmd = [py, str(ROOT / "process_reciter.py"), str(rid), "--name", name,
               "--whisper-model", args.whisper_model]
        if args.skip_whisper_verify:
            cmd.append("--skip-whisper-verify")
        proc = subprocess.run(cmd, capture_output=False)
        elapsed = time.monotonic() - t0
        line = f"[{now()}] === reciter {rid} done in {elapsed/60:.1f} min "
        line += f"(rc={proc.returncode}) ==="
        print(line, flush=True)
        with master_log.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


if __name__ == "__main__":
    main()
