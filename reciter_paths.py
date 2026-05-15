"""
Per-reciter path layout. The legacy reciter (161 = Tunaiji) uses the
flat root paths to preserve all existing data and demos. Any other
reciter is namespaced under reciters/r<id>/.

Usage:
    from reciter_paths import paths_for
    P = paths_for(7)
    audio_mp3 = P.audio_mp3(surah=1)
    P.api_json(surah=1)
    P.wx_json(surah=1)
    ...
"""
from pathlib import Path

ROOT = Path(__file__).parent
LEGACY_RECITER_ID = 161  # Tunaiji -- keep flat layout for back-compat


class ReciterPaths:
    def __init__(self, reciter_id: int, slug: str = ""):
        self.reciter_id = reciter_id
        self.slug = slug or f"r{reciter_id}"
        if reciter_id == LEGACY_RECITER_ID:
            self.audio_dir = ROOT / "audio"
            self.data_dir = ROOT / "data"
        else:
            base = ROOT / "reciters" / f"r{reciter_id}"
            self.audio_dir = base / "audio"
            self.data_dir = base / "data"
        self.wx_dir = self.data_dir / "whisperx"
        self.wx_healed_dir = self.data_dir / "whisperx_healed"
        self.corrected_dir = self.data_dir / "corrected_v2"
        self.reports_dir = self.data_dir / "reports"
        for d in (self.audio_dir, self.data_dir, self.wx_dir,
                  self.wx_healed_dir, self.corrected_dir, self.reports_dir):
            d.mkdir(parents=True, exist_ok=True)

    def audio_mp3(self, surah: int) -> Path:
        return self.audio_dir / f"surah_{surah:03d}.mp3"

    def audio_wav(self, surah: int) -> Path:
        return self.audio_dir / f"surah_{surah:03d}.16k.wav"

    def api_json(self, surah: int) -> Path:
        # legacy filename for Tunaiji vs uniform name for new reciters
        if self.reciter_id == LEGACY_RECITER_ID:
            return self.data_dir / f"surah_{surah}_tunaiji.json"
        return self.data_dir / f"surah_{surah}_api.json"

    def verses_json(self, surah: int) -> Path:
        return self.data_dir / f"surah_{surah}_verses.json"

    def wx_json(self, surah: int) -> Path:
        return self.wx_dir / f"surah_{surah}_force_v2.json"

    def wx_healed_json(self, surah: int) -> Path:
        return self.wx_healed_dir / f"surah_{surah}.json"

    def corrected_json(self, surah: int) -> Path:
        return self.corrected_dir / f"surah_{surah}_corrected.json"

    def diff_json(self, surah: int) -> Path:
        return self.corrected_dir / f"surah_{surah}_diff.json"

    def qul_csv(self, surah: int) -> Path:
        return self.corrected_dir / f"surah_{surah}_qul.csv"


def paths_for(reciter_id: int, slug: str = "") -> ReciterPaths:
    return ReciterPaths(reciter_id, slug)
