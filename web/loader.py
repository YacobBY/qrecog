"""
Generic per-reciter results loader.

Reads the cached pipeline outputs (no GPU needed) and returns
shifts + drifts in a JSON-serializable shape the frontend can render.

Mirrors `experiments/build_tunaiji_analysis.py` but parameterised on
reciter id, and detects which `whisper_verify*.json` to read for any
reciter (including the legacy Tunaiji name).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from reciter_paths import paths_for, LEGACY_RECITER_ID  # noqa: E402

SHIFT_SIM_THRESHOLD = 0.70
DRIFT_MS_THRESHOLD = 150
SURAH_COUNT = 114

# id -> (display name, slug used by quranicaudio) -- the slug is only
# needed for fallback audio URL guessing; the API cache already carries
# the canonical url so we usually don't need it.
RECITERS: dict[int, str] = {
    1: "AbdulBaset (murattal)",
    2: "AbdulBaset (alt)",
    3: "Sudais",
    4: "Abu Bakr al-Shatri",
    5: "Hani ar-Rifai",
    6: "Husary",
    7: "Mishary al-Afasy",
    8: "Minshawi (mujawwad)",
    9: "Minshawi (murattal)",
    10: "Sa`ud ash-Shuraym",
    11: "Tablawi",
    12: "Husary (mu'allim)",
    161: "Khalifah Al Tunaiji",
}

SURAH_NAMES = {
    1: "Al-Fatihah", 2: "Al-Baqarah", 3: "Aal-Imran", 4: "An-Nisa",
    5: "Al-Maidah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
    9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
    13: "Ar-Rad", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
    17: "Al-Isra", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
    21: "Al-Anbya", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
    25: "Al-Furqan", 26: "Ash-Shu'ara", 27: "An-Naml", 28: "Al-Qasas",
    29: "Al-'Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
    33: "Al-Ahzab", 34: "Saba", 35: "Fatir", 36: "Ya-Sin",
    37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
    41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
    45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
    49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
    53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqi'ah",
    57: "Al-Hadid", 58: "Al-Mujadilah", 59: "Al-Hashr", 60: "Al-Mumtahanah",
    61: "As-Saff", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
    65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
    69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
    73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
    77: "Al-Mursalat", 78: "An-Naba", 79: "An-Nazi'at", 80: "Abasa",
    81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
    85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la", 88: "Al-Ghashiyah",
    89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
    93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-'Alaq",
    97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah", 100: "Al-'Adiyat",
    101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-'Asr", 104: "Al-Humazah",
    105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
    109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
    113: "Al-Falaq", 114: "An-Nas",
}


def reciter_name(rid: int) -> str:
    return RECITERS.get(rid, f"reciter-{rid}")


def verify_path(rid: int) -> Path:
    """Whisper-verify report. Tunaiji uses unsuffixed legacy name."""
    if rid == LEGACY_RECITER_ID:
        return ROOT / "reports" / "whisper_verify.json"
    return ROOT / "reports" / f"whisper_verify_r{rid}.json"


@dataclass
class CacheStatus:
    reciter_id: int
    name: str
    has_verify: bool
    has_diffs: bool
    n_api_cached: int
    n_diff_files: int
    n_verify_surahs: int
    completeness_pct: float  # rough: fraction of 114 surahs with diff JSON


def status_for(rid: int) -> CacheStatus:
    P = paths_for(rid)
    vp = verify_path(rid)
    n_api = sum(1 for s in range(1, SURAH_COUNT + 1) if P.api_json(s).exists())
    n_diff = sum(1 for s in range(1, SURAH_COUNT + 1) if P.diff_json(s).exists())
    n_verify_s = 0
    if vp.exists():
        try:
            data = json.loads(vp.read_text(encoding="utf-8"))
            n_verify_s = len([k for k in data if k.isdigit()])
        except Exception:
            pass
    return CacheStatus(
        reciter_id=rid,
        name=reciter_name(rid),
        has_verify=vp.exists(),
        has_diffs=n_diff > 0,
        n_api_cached=n_api,
        n_diff_files=n_diff,
        n_verify_surahs=n_verify_s,
        completeness_pct=round(100 * n_diff / SURAH_COUNT, 1),
    )


def all_statuses() -> list[CacheStatus]:
    return [status_for(r) for r in sorted(RECITERS.keys())]


# ---------------------------------------------------------------------------
# Result loading (mirrors build_tunaiji_analysis.py)
# ---------------------------------------------------------------------------
def _load_inputs(rid: int):
    P = paths_for(rid)
    vp = verify_path(rid)
    verify = {}
    if vp.exists():
        verify = json.loads(vp.read_text(encoding="utf-8"))

    api_cache: dict[int, Any] = {}
    for s in range(1, SURAH_COUNT + 1):
        ap = P.api_json(s)
        if ap.exists():
            try:
                api_cache[s] = json.loads(ap.read_text(encoding="utf-8"))
            except Exception:
                pass

    diffs: dict[int, list] = {}
    for s in range(1, SURAH_COUNT + 1):
        dp = P.diff_json(s)
        if dp.exists():
            try:
                diffs[s] = json.loads(dp.read_text(encoding="utf-8"))
            except Exception:
                pass

    return verify, api_cache, diffs


def _quran_url(rid: int, surah: int, verse: int) -> str:
    return f"https://quran.com/{surah}/{verse}?reciter={rid}"


def _audio_span(audio_url: str, start_ms: int, end_ms: int,
                pad_s: float = 0.10) -> str:
    if not audio_url:
        return ""
    s = max(0.0, start_ms / 1000.0 - pad_s)
    e = end_ms / 1000.0 + pad_s
    return f"{audio_url}#t={s:.2f},{e:.2f}"


def collect_shifts(rid: int, verify, api_cache) -> list[dict]:
    out = []
    for sk, payload in verify.items():
        try:
            surah = int(sk)
        except ValueError:
            continue
        af = api_cache.get(surah, {}).get("audio_file", {})
        audio_url = af.get("audio_url", "")
        for f in payload.get("flags", []):
            if not str(f.get("flag", "")).startswith("shift_"):
                continue
            best_sim = float(f.get("best_match_sim", 0) or 0)
            if best_sim < SHIFT_SIM_THRESHOLD:
                continue
            verse_key = f.get("verse_key", "")
            try:
                verse = int(verse_key.split(":")[1])
            except Exception:
                continue
            offset = int(f.get("best_match_offset", 0))
            api_from, api_to = (f.get("api_span_ms") or [0, 0])
            actual_v = verse + offset
            out.append({
                "surah": surah,
                "surah_name": SURAH_NAMES.get(surah, "?"),
                "verse": verse,
                "offset": offset,
                "actual_verse": actual_v,
                "sim_self": round(float(f.get("sim_self", 0) or 0), 3),
                "best_sim": round(best_sim, 3),
                "transcribed": (f.get("transcribed_normalized") or "")[:120],
                "api_from_ms": api_from,
                "api_to_ms": api_to,
                "claimed_url": _quran_url(rid, surah, verse),
                "actual_url": _quran_url(rid, surah, actual_v),
                "audio_url": _audio_span(audio_url, api_from, api_to),
            })
    out.sort(key=lambda s: (-s["best_sim"], s["surah"], s["verse"]))
    return out


def collect_drifts(rid: int, diffs, api_cache) -> list[dict]:
    out = []
    for surah, verse_list in diffs.items():
        af = api_cache.get(surah, {}).get("audio_file", {})
        audio_url = af.get("audio_url", "")
        for v in verse_list:
            delta = int(v.get("delta_to", 0) or 0)
            if abs(delta) < DRIFT_MS_THRESHOLD:
                continue
            verse_key = v.get("verse_key", "")
            try:
                vnum = int(verse_key.split(":")[1])
            except Exception:
                continue
            old_to = int(v.get("old_to", 0))
            new_to = int(v.get("new_to", 0))
            direction = "EARLY" if delta > 0 else "LATE"
            lo = min(old_to, new_to) - 1500
            hi = max(old_to, new_to) + 1500
            out.append({
                "surah": surah,
                "surah_name": SURAH_NAMES.get(surah, "?"),
                "verse": vnum,
                "old_to_ms": old_to,
                "new_to_ms": new_to,
                "delta_ms": delta,
                "abs_delta_ms": abs(delta),
                "direction": direction,
                "verse_url": _quran_url(rid, surah, vnum),
                "audio_url": _audio_span(audio_url, lo, hi, pad_s=0.0),
            })
    # Largest drift first -- the request was "sorted by largest drift".
    out.sort(key=lambda d: (-d["abs_delta_ms"], d["surah"], d["verse"]))
    return out


def load_verse(rid: int, surah: int, verse: int) -> Optional[dict]:
    """Per-verse text + word-level timing for the inline reader."""
    P = paths_for(rid)
    vp = P.verses_json(surah)
    ap = P.api_json(surah)
    if not (vp.exists() and ap.exists()):
        return None
    try:
        vdata = json.loads(vp.read_text(encoding="utf-8"))
        api = json.loads(ap.read_text(encoding="utf-8"))
    except Exception:
        return None
    verses = vdata.get("verses", []) if isinstance(vdata, dict) else vdata
    vrec = next((v for v in verses if v.get("verse_number") == verse), None)
    if not vrec:
        return None
    af = api.get("audio_file", {}) or {}
    ts_list = af.get("timestamps", []) or []
    ts = next((t for t in ts_list
               if t.get("verse_key") == f"{surah}:{verse}"), None)
    text = vrec.get("text_uthmani") or vrec.get("text_imlaei") or ""
    words = [w for w in text.split(" ") if w.strip()]
    segments = ts.get("segments", []) if ts else []
    # segments items: [1-based word_idx, start_ms_absolute, end_ms_absolute]
    word_times = []
    for i, w in enumerate(words):
        seg = segments[i] if i < len(segments) else None
        word_times.append({
            "i": i,
            "text": w,
            "start_ms": int(seg[1]) if seg else None,
            "end_ms": int(seg[2]) if seg else None,
        })
    translation = ""
    for tr in (vrec.get("translations") or []):
        if tr.get("text"):
            translation = tr["text"]
            break
    return {
        "verse_key": f"{surah}:{verse}",
        "surah": surah,
        "verse": verse,
        "text_uthmani": text,
        "translation": translation,
        "verse_from_ms": int(ts["timestamp_from"]) if ts else None,
        "verse_to_ms":   int(ts["timestamp_to"])   if ts else None,
        "audio_url": af.get("audio_url", ""),
        "words": word_times,
    }


def load_results(rid: int) -> dict:
    """Return everything the frontend needs in one shot."""
    verify, api_cache, diffs = _load_inputs(rid)
    shifts = collect_shifts(rid, verify, api_cache)
    drifts = collect_drifts(rid, diffs, api_cache)
    surahs_with_issue = sorted(
        {s["surah"] for s in shifts} | {d["surah"] for d in drifts}
    )
    return {
        "reciter_id": rid,
        "reciter_name": reciter_name(rid),
        "thresholds": {
            "shift_sim": SHIFT_SIM_THRESHOLD,
            "drift_ms": DRIFT_MS_THRESHOLD,
        },
        "headline": {
            "n_shifts": len(shifts),
            "n_drifts": len(drifts),
            "n_surahs_affected": len(surahs_with_issue),
            "n_surahs_clean": SURAH_COUNT - len(surahs_with_issue),
        },
        "shifts": shifts,
        "drifts": drifts,
        "status": asdict(status_for(rid)),
    }
