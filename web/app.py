"""
qrfix web GUI -- FastAPI backend.

Endpoints
    GET  /                              -> index.html
    GET  /api/reciters                  -> [{id, name, has_cache, completeness}]
    GET  /api/reciters/{rid}/status     -> CacheStatus
    GET  /api/reciters/{rid}/results    -> shifts + drifts (sorted by largest)
    POST /api/reciters/{rid}/run        -> queue a fresh pipeline run
    GET  /api/reciters/{rid}/stream     -> SSE: live log of current/last run

Run a fresh analysis is GPU-heavy (~30 min/surah on CPU, faster on GPU).
We spawn at most one subprocess per reciter; the SSE endpoint replays the
ring buffer and tails new lines until the process exits.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import (FileResponse, JSONResponse, Response,
                               StreamingResponse)
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from web.loader import (RECITERS, all_statuses, load_results,  # noqa: E402
                        load_verse, reciter_name, status_for)

PYTHON = sys.executable  # use the same interpreter that launched us
HERE = Path(__file__).parent
STATIC_DIR = HERE / "static"
LOG_RING_SIZE = 2000  # keep the most recent N log lines per reciter


# ---------------------------------------------------------------------------
# Run-queue / SSE plumbing
# ---------------------------------------------------------------------------
@dataclass
class RunState:
    reciter_id: int
    started_at: float
    proc: Optional[subprocess.Popen] = None
    log: deque = field(default_factory=lambda: deque(maxlen=LOG_RING_SIZE))
    listeners: list[asyncio.Queue] = field(default_factory=list)
    finished: bool = False
    return_code: Optional[int] = None
    cmd: list[str] = field(default_factory=list)
    seq: int = 0  # monotonic line counter for client resume


_runs: dict[int, RunState] = {}
_runs_lock = threading.Lock()


def _push_line(state: RunState, line: str) -> None:
    state.seq += 1
    rec = {"seq": state.seq, "ts": time.time(), "line": line.rstrip("\r\n")}
    state.log.append(rec)
    # Notify listeners (asyncio.Queue is thread-safe for put_nowait via
    # call_soon_threadsafe; we only use it on the same loop here for
    # streaming, but the producer thread schedules onto the loop).
    loop = state._loop  # type: ignore[attr-defined]
    if loop is None:
        return
    for q in list(state.listeners):
        loop.call_soon_threadsafe(q.put_nowait, rec)


def _reader_thread(state: RunState) -> None:
    assert state.proc is not None
    try:
        for raw in iter(state.proc.stdout.readline, b""):  # type: ignore
            try:
                line = raw.decode("utf-8", errors="replace")
            except Exception:
                line = repr(raw)
            _push_line(state, line)
        state.proc.wait()
    finally:
        state.return_code = state.proc.returncode
        state.finished = True
        _push_line(state, f"\n[run finished with code {state.return_code}]")


def _build_command(rid: int) -> list[str]:
    """Compose the shell command for a fresh end-to-end run."""
    if rid == 161:
        return [PYTHON, "analyze_tunaiji.py", "--whisper-model", "large-v3"]
    name = reciter_name(rid)
    return [PYTHON, "process_reciter.py", str(rid),
            "--name", name, "--whisper-model", "large-v3"]


def start_run(rid: int) -> RunState:
    if rid not in RECITERS:
        raise HTTPException(404, f"unknown reciter {rid}")
    with _runs_lock:
        existing = _runs.get(rid)
        if existing and not existing.finished:
            return existing  # already running -- attach to it
        cmd = _build_command(rid)
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            bufsize=0,
        )
        state = RunState(
            reciter_id=rid,
            started_at=time.time(),
            proc=proc,
            cmd=cmd,
        )
        # Stash the asyncio loop so the reader thread can hand lines back.
        state._loop = asyncio.get_event_loop()  # type: ignore[attr-defined]
        _runs[rid] = state
        threading.Thread(target=_reader_thread, args=(state,),
                         daemon=True).start()
        _push_line(state, f"[launched: {' '.join(cmd)}]")
        return state


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="qrfix")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/reciters")
def reciters():
    return [asdict(s) for s in all_statuses()]


@app.get("/api/reciters/{rid}/status")
def status(rid: int):
    if rid not in RECITERS:
        raise HTTPException(404, f"unknown reciter {rid}")
    return asdict(status_for(rid))


@app.get("/api/reciters/{rid}/results")
def results(rid: int):
    if rid not in RECITERS:
        raise HTTPException(404, f"unknown reciter {rid}")
    s = status_for(rid)
    if not s.has_verify and not s.has_diffs:
        return JSONResponse(
            {"reciter_id": rid, "reciter_name": reciter_name(rid),
             "cached": False,
             "message": "No cached pipeline output. Press 'Run analysis' "
                        "to start a fresh end-to-end run."},
            status_code=200,
        )
    payload = load_results(rid)
    payload["cached"] = True
    return payload


@app.get("/api/reciters/{rid}/verse/{surah}/{verse}")
def verse(rid: int, surah: int, verse: int):
    if rid not in RECITERS:
        raise HTTPException(404, f"unknown reciter {rid}")
    data = load_verse(rid, surah, verse)
    if not data:
        raise HTTPException(404, f"verse {surah}:{verse} not cached")
    return data


@app.post("/api/reciters/{rid}/run")
def run(rid: int):
    state = start_run(rid)
    return {
        "reciter_id": state.reciter_id,
        "started_at": state.started_at,
        "running": not state.finished,
        "cmd": state.cmd,
    }


@app.get("/api/reciters/{rid}/run/state")
def run_state(rid: int):
    state = _runs.get(rid)
    if not state:
        return {"reciter_id": rid, "running": False, "exists": False}
    return {
        "reciter_id": rid,
        "running": not state.finished,
        "return_code": state.return_code,
        "started_at": state.started_at,
        "n_lines": state.seq,
        "exists": True,
    }


@app.get("/api/reciters/{rid}/stream")
async def stream(rid: int, since: int = 0):
    state = _runs.get(rid)

    async def gen():
        # Replay buffered lines first (so a reload picks up history).
        if state is not None:
            for rec in list(state.log):
                if rec["seq"] > since:
                    yield f"data: {json.dumps(rec)}\n\n"
            if state.finished:
                yield (f"event: done\ndata: "
                       f"{json.dumps({'return_code': state.return_code})}\n\n")
                return
            # Live tail
            q: asyncio.Queue = asyncio.Queue()
            state.listeners.append(q)
            try:
                while True:
                    try:
                        rec = await asyncio.wait_for(q.get(), timeout=15.0)
                        yield f"data: {json.dumps(rec)}\n\n"
                        if state.finished and q.empty():
                            yield (f"event: done\ndata: "
                                   f"{json.dumps({'return_code': state.return_code})}\n\n")
                            return
                    except asyncio.TimeoutError:
                        # Heartbeat keeps proxies + EventSource alive.
                        yield ": ping\n\n"
            finally:
                if q in state.listeners:
                    state.listeners.remove(q)
        else:
            yield (f"event: idle\ndata: "
                   f"{json.dumps({'message': 'no run started'})}\n\n")

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "X-Accel-Buffering": "no"})


@app.get("/healthz")
def healthz():
    return {"ok": True, "reciters": len(RECITERS)}
