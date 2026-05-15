"""
Transcribe Classical Arabic audio with word-level timestamps using WhisperX.

Pipeline:
    1. Ensure audio is 16 kHz mono WAV (convert with ffmpeg if not).
    2. Transcribe with faster-whisper backend (large-v3, float16, CUDA).
    3. Free GPU memory.
    4. Align with elgeish/wav2vec2-large-xlsr-53-arabic.
    5. Free GPU memory.
    6. Write result["segments"] to JSON.

Usage:
    python whisperx_align.py <input_audio> <output_json>
"""
import argparse
import gc
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

T0 = time.monotonic()


def log(msg: str):
    """Timestamped, line-flushed status print."""
    elapsed = time.monotonic() - T0
    print(f"[{elapsed:7.1f}s] {msg}", flush=True)


def fail(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr, flush=True)
    sys.exit(code)


def gpu_mem_str():
    try:
        import torch
        if not torch.cuda.is_available():
            return "(no cuda)"
        free, total = torch.cuda.mem_get_info()
        used = total - free
        return f"GPU mem: used {used/2**30:.2f} GB / total {total/2**30:.2f} GB"
    except Exception as e:
        return f"(gpu mem query failed: {e})"


def ensure_16k_mono_wav(input_path: Path) -> Path:
    """Return a path to a 16 kHz mono WAV. Converts via ffmpeg if needed."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        fail("ffmpeg/ffprobe not found on PATH")

    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "a:0",
         "-show_entries", "stream=codec_name,sample_rate,channels:format=duration,bit_rate",
         "-of", "default=nw=1:nk=0",
         str(input_path)],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        fail(f"ffprobe failed on {input_path}: {probe.stderr.strip()}")

    info = {}
    for line in probe.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            info[k.strip()] = v.strip()

    size_mb = input_path.stat().st_size / 2**20
    dur = float(info.get("duration", 0) or 0)
    log(f"Audio: {input_path.name}  codec={info.get('codec_name')}  "
        f"sr={info.get('sample_rate')}Hz  ch={info.get('channels')}  "
        f"dur={dur:.1f}s  size={size_mb:.1f} MiB")

    is_wav = input_path.suffix.lower() == ".wav" and info.get("codec_name") == "pcm_s16le"
    is_16k = info.get("sample_rate") == "16000"
    is_mono = info.get("channels") == "1"
    if is_wav and is_16k and is_mono:
        log("Audio already 16 kHz mono WAV; skipping conversion")
        return input_path

    out_path = input_path.with_suffix(".16k.wav")
    log(f"Converting -> {out_path.name} (16 kHz mono)...")
    t = time.monotonic()
    conv = subprocess.run(
        ["ffmpeg", "-y", "-i", str(input_path),
         "-ar", "16000", "-ac", "1", str(out_path)],
        capture_output=True, text=True,
    )
    if conv.returncode != 0:
        fail(f"ffmpeg conversion failed: {conv.stderr.strip()[-500:]}")
    log(f"Conversion done in {time.monotonic()-t:.1f}s "
        f"({out_path.stat().st_size/2**20:.1f} MiB)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input_audio", help="path to input audio file")
    ap.add_argument("output_json", help="path to output JSON")
    args = ap.parse_args()

    input_path = Path(args.input_audio)
    output_path = Path(args.output_json)

    log(f"Input:  {input_path}")
    log(f"Output: {output_path}")

    if not input_path.exists():
        fail(f"audio file not found: {input_path}")
    if not input_path.is_file():
        fail(f"not a file: {input_path}")

    log("Importing torch...")
    try:
        import torch
    except ImportError as e:
        fail(f"failed to import torch: {e}")
    log(f"torch {torch.__version__}  cuda_available={torch.cuda.is_available()}  "
        f"cuda_runtime={torch.version.cuda}")

    if not torch.cuda.is_available():
        fail("CUDA is not available; this script requires an NVIDIA GPU")
    log(f"GPU: {torch.cuda.get_device_name(0)}  {gpu_mem_str()}")

    log("Importing whisperx...")
    try:
        import whisperx
    except ImportError as e:
        fail(f"failed to import whisperx (pip install whisperx): {e}")
    log(f"whisperx {getattr(whisperx, '__version__', '?')}")

    # Tell HF Hub where to cache & whether to show its progress bars
    cache_dir = os.environ.get("HF_HOME") or os.environ.get("TRANSFORMERS_CACHE")
    log(f"HF cache: {cache_dir or '(default)'}")

    audio_path = ensure_16k_mono_wav(input_path)

    device = "cuda"
    compute_type = "float16"
    batch_size = 16
    language = "ar"

    # 1. Transcribe ----------------------------------------------------------
    log(f"=== Phase 1: load whisper large-v3 ({compute_type}, {device}) ===")
    log("(first run downloads ~3 GB; cached afterwards)")
    t = time.monotonic()
    try:
        model = whisperx.load_model(
            "large-v3",
            device=device,
            compute_type=compute_type,
            language=language,
        )
    except Exception as e:
        fail(f"failed to load whisper large-v3: {e}")
    log(f"Whisper loaded in {time.monotonic()-t:.1f}s.  {gpu_mem_str()}")

    log(f"Loading audio waveform from {audio_path.name}...")
    t = time.monotonic()
    audio = whisperx.load_audio(str(audio_path))
    log(f"Audio loaded in {time.monotonic()-t:.1f}s "
        f"({len(audio)} samples @ 16k = {len(audio)/16000:.1f}s)")

    log(f"=== Phase 2: transcribe (batch_size={batch_size}, language={language}) ===")
    t = time.monotonic()
    try:
        result = model.transcribe(audio, batch_size=batch_size, language=language)
    except Exception as e:
        fail(f"transcription failed: {e}")
    transcribe_time = time.monotonic() - t
    n_seg = len(result.get("segments", []))
    n_chars = sum(len(s.get("text", "")) for s in result.get("segments", []))
    audio_dur = len(audio) / 16000
    rtf = transcribe_time / audio_dur if audio_dur > 0 else 0
    log(f"Transcribed in {transcribe_time:.1f}s  ->  {n_seg} segments, {n_chars} chars")
    log(f"Real-time factor: {rtf:.3f}x  (audio {audio_dur:.1f}s / wall {transcribe_time:.1f}s)")
    if n_seg > 0:
        first = result["segments"][0]
        last = result["segments"][-1]
        log(f"first seg: [{first.get('start',0):.2f}..{first.get('end',0):.2f}] "
            f"{first.get('text','')[:60]!r}")
        log(f"last  seg: [{last.get('start',0):.2f}..{last.get('end',0):.2f}] "
            f"{last.get('text','')[:60]!r}")

    log("Freeing whisper model from GPU...")
    del model
    gc.collect()
    torch.cuda.empty_cache()
    log(f"After free.  {gpu_mem_str()}")

    # 2. Align ---------------------------------------------------------------
    align_model_name = "jonatasgrosman/wav2vec2-large-xlsr-53-arabic"
    log(f"=== Phase 3: load alignment model {align_model_name} ===")
    log("(first run downloads ~1.2 GB; cached afterwards)")
    t = time.monotonic()
    try:
        align_model, align_metadata = whisperx.load_align_model(
            language_code=language,
            device=device,
            model_name=align_model_name,
        )
    except Exception as e:
        fail(f"failed to load alignment model {align_model_name}: {e}")
    log(f"Alignment model loaded in {time.monotonic()-t:.1f}s.  {gpu_mem_str()}")

    log(f"=== Phase 4: align (return_char_alignments=False) ===")
    t = time.monotonic()
    try:
        result = whisperx.align(
            result["segments"],
            align_model,
            align_metadata,
            audio,
            device,
            return_char_alignments=False,
        )
    except Exception as e:
        fail(f"alignment failed: {e}")
    align_time = time.monotonic() - t
    n_seg = len(result.get("segments", []))
    n_words = sum(len(s.get("words", [])) for s in result.get("segments", []))
    log(f"Aligned in {align_time:.1f}s  ->  {n_seg} segments, {n_words} words")

    log("Freeing alignment model from GPU...")
    del align_model
    gc.collect()
    torch.cuda.empty_cache()
    log(f"After free.  {gpu_mem_str()}")

    # 3. Write output --------------------------------------------------------
    log(f"=== Phase 5: write {output_path} ===")
    segments = result["segments"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(segments, f, ensure_ascii=False, indent=2)
    out_size_kb = output_path.stat().st_size / 1024
    log(f"Wrote {out_size_kb:.1f} KiB to {output_path}")

    log("=== DONE ===")
    print(f"segments: {len(segments)}")
    print(f"words:    {n_words}")


if __name__ == "__main__":
    main()
