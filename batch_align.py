"""
Run forced alignment for many surahs in a single Python session.
Loads the wav2vec2 model once, then iterates. Skips any surah whose
output JSON already exists (use --force to override).

Usage:
    python batch_align.py                    # all 114 surahs
    python batch_align.py 1 2 18 --force     # specific surahs, re-run
"""
import argparse
import gc
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from force_align import load_align_model, align_surah, log
from reciter_paths import paths_for, LEGACY_RECITER_ID


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("surahs", nargs="*", type=int,
                    help="surah numbers (default: 1-114)")
    ap.add_argument("--reciter-id", type=int, default=LEGACY_RECITER_ID)
    ap.add_argument("--force", action="store_true",
                    help="re-run even if output JSON exists")
    args = ap.parse_args()

    P = paths_for(args.reciter_id)
    targets = args.surahs or list(range(1, 115))

    # Skip-existing pass first so we know whether to load the model.
    todo = []
    for n in targets:
        out_path = P.wx_json(n)
        if out_path.exists() and not args.force:
            continue
        # Skip if audio missing
        if not P.audio_mp3(n).exists():
            continue
        todo.append(n)

    log(f"queued {len(todo)} surahs to align "
        f"(skipping {len(targets)-len(todo)} already done)")
    if not todo:
        return

    align_model, align_meta, whisperx_mod = load_align_model()

    t_start = time.monotonic()
    n_done = 0
    n_skip = 0
    n_fail = 0
    for n in todo:
        try:
            res = align_surah(n, align_model, align_meta, whisperx_mod,
                              force=args.force, print_summary=False, P=P)
        except Exception as e:
            log(f"surah {n}: ERROR {e}")
            n_fail += 1
            # Free GPU memory in case the failure left something behind.
            import torch
            gc.collect()
            torch.cuda.empty_cache()
            continue
        if res is None:
            n_skip += 1
        else:
            n_done += 1

    elapsed = time.monotonic() - t_start
    log(f"DONE in {elapsed:.1f}s. aligned={n_done} skipped={n_skip} failed={n_fail}")


if __name__ == "__main__":
    main()
