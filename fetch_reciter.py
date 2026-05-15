"""
Fetch a complete reciter's audio + API timestamps + canonical verses.
Reciter is identified by quran.com reciter_id (e.g. 7 = Mishary,
161 = Tunaiji). Skips files already on disk.
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

from reciter_paths import paths_for

TIMESTAMPS_URL = "https://api.quran.com/api/v4/chapter_recitations/{r}/{n}?segments=true"
VERSES_URL = ("https://api.quran.com/api/v4/verses/by_chapter/{n}"
              "?translations=20&fields=text_uthmani&words=false&per_page=500")


def http_get(url: str, dest: Path, retries: int = 3, sleep_s: float = 2.0):
    if dest.exists() and dest.stat().st_size > 0:
        return False
    tmp = dest.with_suffix(dest.suffix + ".part")
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "qrfix/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r, tmp.open("wb") as f:
                while True:
                    chunk = r.read(64 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
            tmp.rename(dest)
            return True
        except Exception as e:
            last_err = e
            if tmp.exists():
                tmp.unlink()
            if attempt < retries - 1:
                time.sleep(sleep_s * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {retries} retries: {last_err}")


def fetch_surah(reciter_id: int, n: int):
    P = paths_for(reciter_id)
    actions = []

    api_dest = P.api_json(n)
    if http_get(TIMESTAMPS_URL.format(r=reciter_id, n=n), api_dest):
        actions.append("api")

    verses_dest = P.verses_json(n)
    if http_get(VERSES_URL.format(n=n), verses_dest):
        actions.append("verses")

    audio_dest = P.audio_mp3(n)
    if not audio_dest.exists() or audio_dest.stat().st_size == 0:
        # Pull audio_url from the just-fetched API JSON.
        api_data = json.loads(api_dest.read_text(encoding="utf-8"))
        audio_url = api_data["audio_file"]["audio_url"]
        if http_get(audio_url, audio_dest):
            size_mb = audio_dest.stat().st_size / 2**20
            actions.append(f"audio ({size_mb:.1f} MB)")
    return actions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reciter_id", type=int)
    ap.add_argument("surahs", nargs="*", type=int,
                    help="surah numbers (default: 1-114)")
    args = ap.parse_args()
    targets = args.surahs or list(range(1, 115))

    t0 = time.monotonic()
    n_new = 0
    for n in targets:
        try:
            done = fetch_surah(args.reciter_id, n)
        except Exception as e:
            print(f"surah {n:>3}: FAILED -- {e}", flush=True)
            continue
        if done:
            n_new += 1
            print(f"surah {n:>3}: fetched {', '.join(done)}", flush=True)
        else:
            print(f"surah {n:>3}: already present", flush=True)
    print(f"\nDone in {time.monotonic()-t0:.1f}s. New downloads: {n_new}/{len(targets)}.")


if __name__ == "__main__":
    main()
