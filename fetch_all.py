"""
Fetch every surah's audio + API timestamp JSON for reciter 161
(Khalifah Al Tunaiji). Skips files that already exist.

Outputs:
    audio/surah_<NNN>.mp3
    data/surah_<N>_tunaiji.json
    data/surah_<N>_verses.json   (canonical text + Saheeh translation)
"""
import argparse
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
AUDIO = ROOT / "audio"
DATA = ROOT / "data"
AUDIO.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)

RECITER = 161
TUNAIJI_AUDIO_URL = "https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/{n}.mp3"
TIMESTAMPS_URL = "https://api.quran.com/api/v4/chapter_recitations/{r}/{n}?segments=true"
VERSES_URL = ("https://api.quran.com/api/v4/verses/by_chapter/{n}"
              "?translations=20&fields=text_uthmani&words=false&per_page=500")


def http_get(url: str, dest: Path, retries: int = 3, sleep_s: float = 2.0):
    """Download url to dest atomically (write to .part, rename)."""
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


def fetch_surah(n: int):
    audio_dest = AUDIO / f"surah_{n:03d}.mp3"
    ts_dest = DATA / f"surah_{n}_tunaiji.json"
    verses_dest = DATA / f"surah_{n}_verses.json"

    actions = []
    if http_get(TIMESTAMPS_URL.format(r=RECITER, n=n), ts_dest):
        actions.append("timestamps")
    if http_get(VERSES_URL.format(n=n), verses_dest):
        actions.append("verses")
    if http_get(TUNAIJI_AUDIO_URL.format(n=n), audio_dest):
        size_mb = audio_dest.stat().st_size / 2**20
        actions.append(f"audio ({size_mb:.1f} MB)")
    return actions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("surahs", nargs="*", type=int,
                    help="surah numbers (default: 1-114)")
    args = ap.parse_args()
    targets = args.surahs or list(range(1, 115))

    t0 = time.monotonic()
    n_new = 0
    for n in targets:
        try:
            done = fetch_surah(n)
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
