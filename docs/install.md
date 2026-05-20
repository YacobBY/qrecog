# Installation

`qrfix` runs a forced-alignment + transcription pipeline that needs
Python 3.10+, ffmpeg, and an NVIDIA GPU with CUDA. Tested on Windows 11
+ RTX 4090 + CUDA 13.2 and on Linux + CUDA 12.x.

## 1. System prerequisites

- **Python 3.10 or newer.** `python --version` should report ≥ 3.10.
- **ffmpeg + ffprobe** on `PATH`.
  - Windows: `winget install Gyan.FFmpeg`
  - macOS: `brew install ffmpeg`
  - Debian/Ubuntu: `sudo apt install ffmpeg`
- **NVIDIA GPU + CUDA-capable PyTorch.** The Whisper-verify step needs
  ~3 GB VRAM for `medium`, ~6 GB for `large-v3`. The wav2vec2 alignment
  step needs ~2 GB. CPU mode is theoretically possible but Whisper-verify
  on the full Quran would take days.

## 2. Clone

```bash
git clone https://github.com/USER/qrfix.git
cd qrfix
```

## 3. Virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

## 4. Install PyTorch first (CUDA-matched wheel)

This one isn't optional and the order matters — `pip install -r
requirements.txt` will pull a CPU-only torch by default if you skip
this step.

Find your CUDA version:
```bash
nvidia-smi    # look at "CUDA Version" in the top-right
```

Install the matching wheel:

```bash
# CUDA 12.1
pip install --index-url https://download.pytorch.org/whl/cu121 \
    torch torchvision torchaudio

# CUDA 12.4
pip install --index-url https://download.pytorch.org/whl/cu124 \
    torch torchvision torchaudio

# CUDA 13.x
pip install --index-url https://download.pytorch.org/whl/cu130 \
    torch torchvision torchaudio
```

If you don't see your CUDA version in
<https://pytorch.org/get-started/locally/>, download the matching CUDA
toolkit from <https://developer.nvidia.com/cuda-downloads> first, or
fall back to CPU-only (`pip install torch torchvision torchaudio`).

Verify:
```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
Expected output, e.g.:
```
2.11.0+cu130 True NVIDIA GeForce RTX 4090
```

## 5. Install qrfix and its Python deps

```bash
pip install -e .
```

This installs:

- `whisperx` (which pulls in faster-whisper, ctranslate2, transformers,
  pyannote-audio)
- `openai-whisper` (the verify step uses this directly)
- `huggingface_hub`, `soundfile`, `numpy`

…and registers console-script shortcuts:

```text
qrfix-analyze-tunaiji
qrfix-fetch
qrfix-align
qrfix-heal
qrfix-fix
qrfix-detect
qrfix-verify
qrfix-summarize
qrfix-status
```

You can also just `python <script>.py` from the repo root — the entry
points are convenience aliases.

## 6. Hugging Face model cache

WhisperX and faster-whisper download model weights on first use into
`~/.cache/huggingface/`. The first run pulls about 4 GB:

| model | size |
|-------|------|
| `large-v3` (Whisper) | ~3 GB |
| `jonatasgrosman/wav2vec2-large-xlsr-53-arabic` | ~1.2 GB |
| `Systran/faster-whisper-large-v3` (auto-pulled by whisperx) | ~3 GB |
| `pyannote/segmentation` (VAD) | ~30 MB |

You can pre-warm the cache:

```bash
python -c "import whisperx; whisperx.load_align_model(language_code='ar', device='cuda')"
python -c "import whisper;  whisper.load_model('large-v3')"
```

Or set `HF_HOME=/path/to/big/disk` if your home partition is small.

## 7. Smoke test

```bash
python analyze_tunaiji.py --skip-whisper-verify
```

A clean run prints a status table at the start, then runs steps 1-5,
then prints the aggregated table. On a 4090 this is ~15 minutes the
first time (including audio downloads ≈ 1.2 GB) and ~10 seconds on
subsequent runs (skip-existing kicks in for every step).

If everything works:

```bash
python analyze_tunaiji.py    # adds the slow Whisper-verify pass
```

…and you'll get the full report at `reports/tunaiji_findings.md`.

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `torch.cuda.is_available() == False` | Wrong PyTorch wheel — re-install with the matching `cu*` index URL |
| `ffmpeg not found` | ffmpeg not on PATH; check `which ffmpeg` / `where ffmpeg` |
| Whisper download stalls | HF rate-limit; just re-run, the cache resumes |
| Out-of-memory on align step | Lower `CHUNK_TARGET_S` in `force_align.py` (default 30) |
| Out-of-memory on Whisper-verify | Use `--whisper-model medium` instead of `large-v3` |
| `UnicodeEncodeError` printing Arabic | Set `PYTHONIOENCODING=utf-8` (Windows console) |

For deeper detail on each step, see [manual.md](manual.md). For *why*
each step is the way it is, see [methodology.md](methodology.md).
