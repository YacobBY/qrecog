"""Build a static GitHub Pages snapshot of the qrecog web UI for reciter 161.

Reads cached pipeline outputs via web.loader, writes flat JSON snapshots
under docs/api/, copies the frontend assets into docs/, and patches app.js
to fetch the flat files instead of the live FastAPI endpoints. Disables
the "Run analysis" button and SSE log panel since neither exists in static
hosting.
"""
from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.loader import all_statuses, load_results, load_verse  # noqa: E402

RECITER_ID = 161
DOCS = ROOT / "docs"
API = DOCS / "api"
STATIC_SRC = ROOT / "web" / "static"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def dump_reciter_list() -> None:
    statuses = [s for s in all_statuses() if s.reciter_id == RECITER_ID]
    write_json(API / "reciters.json", [asdict(s) for s in statuses])
    print(f"wrote api/reciters.json ({len(statuses)} reciter)")


def dump_results() -> dict:
    payload = load_results(RECITER_ID)
    payload["cached"] = True
    write_json(API / f"reciters/{RECITER_ID}/results.json", payload)
    print(f"wrote api/reciters/{RECITER_ID}/results.json"
          f"  ({len(payload['shifts'])} shifts, {len(payload['drifts'])} drifts)")
    return payload


def needed_verses(payload: dict) -> set[tuple[int, int]]:
    """Return the set of (surah, verse) the frontend may fetch on row open."""
    pairs: set[tuple[int, int]] = set()
    for d in payload["drifts"]:
        pairs.add((d["surah"], d["verse"]))
        pairs.add((d["surah"], d["verse"] + 1))
    for s in payload["shifts"]:
        pairs.add((s["surah"], s["verse"]))
        pairs.add((s["surah"], s["actual_verse"]))
    return pairs


def dump_verses(pairs: set[tuple[int, int]]) -> None:
    written = skipped = 0
    for surah, verse in sorted(pairs):
        data = load_verse(RECITER_ID, surah, verse)
        if data is None:
            skipped += 1
            continue
        write_json(API / f"reciters/{RECITER_ID}/verse/{surah}/{verse}.json", data)
        written += 1
    print(f"wrote {written} verse files (skipped {skipped} uncached)")


def copy_and_patch_frontend() -> None:
    shutil.copy(STATIC_SRC / "index.html", DOCS / "index.html")
    shutil.copy(STATIC_SRC / "style.css",  DOCS / "style.css")

    # rewrite index.html to point at relative paths and drop the run button
    html = (DOCS / "index.html").read_text(encoding="utf-8")
    html = html.replace('href="/static/style.css"', 'href="style.css"')
    html = html.replace('src="/static/app.js"',     'src="app.js"')
    (DOCS / "index.html").write_text(html, encoding="utf-8")

    # patch app.js: swap fetch URLs, neutralize run/stream
    js = (STATIC_SRC / "app.js").read_text(encoding="utf-8")
    js = js.replace(
        'reciters:   ()      => fetch("/api/reciters").then(r => r.json()),',
        'reciters:   ()      => fetch("api/reciters.json").then(r => r.json()),',
    )
    js = js.replace(
        'results:    (rid)   => fetch(`/api/reciters/${rid}/results`).then(r => r.json()),',
        'results:    (rid)   => fetch(`api/reciters/${rid}/results.json`).then(r => r.json()),',
    )
    js = js.replace(
        'verse:      (rid, s, v) => fetch(`/api/reciters/${rid}/verse/${s}/${v}`).then(r => r.ok ? r.json() : null),',
        'verse:      (rid, s, v) => fetch(`api/reciters/${rid}/verse/${s}/${v}.json`).then(r => r.ok ? r.json() : null).catch(() => null),',
    )
    js = js.replace(
        'startRun:   (rid)   => fetch(`/api/reciters/${rid}/run`, { method: "POST" }).then(r => r.json()),',
        'startRun:   (rid)   => Promise.resolve({ running: false }),',
    )
    js = js.replace(
        'runState:   (rid)   => fetch(`/api/reciters/${rid}/run/state`).then(r => r.json()),',
        'runState:   (rid)   => Promise.resolve({ exists: false, running: false }),',
    )
    # Disable SSE entirely on the static demo.
    js = js.replace(
        'function attachLogStream(rid) {',
        'function attachLogStream(rid) { return; /* disabled on static demo */',
    )
    # Hide the run button + log panel on boot.
    js += (
        "\n// static demo: hide pipeline run UI\n"
        "document.addEventListener('DOMContentLoaded', () => {\n"
        "  const r = document.getElementById('btn-run');\n"
        "  if (r) r.style.display = 'none';\n"
        "  const l = document.getElementById('logwrap');\n"
        "  if (l) l.hidden = true;\n"
        "});\n"
    )
    (DOCS / "app.js").write_text(js, encoding="utf-8")
    print("copied + patched frontend (index.html, app.js, style.css)")


def write_nojekyll() -> None:
    """Stop GitHub Pages from running Jekyll (which can hide files starting with _)."""
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")


def main() -> None:
    # Only clean the demo artifacts, not the pre-existing project markdown.
    if API.exists():
        shutil.rmtree(API)
    for name in ("index.html", "app.js", "style.css", ".nojekyll"):
        f = DOCS / name
        if f.exists():
            f.unlink()
    DOCS.mkdir(parents=True, exist_ok=True)
    dump_reciter_list()
    payload = dump_results()
    pairs = needed_verses(payload)
    print(f"will dump {len(pairs)} unique verse files for openable rows")
    dump_verses(pairs)
    copy_and_patch_frontend()
    write_nojekyll()
    print(f"\nstatic demo built at {DOCS}")


if __name__ == "__main__":
    main()
