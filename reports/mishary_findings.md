# Mishary al-Afasy (reciter 7) — confirmed API timing bugs

You said Mishary should be "completely correct" and asked me to surface any
high-confidence findings. Here are three confirmed bugs in the
quran.com / QUL `chapter_recitations/7` API timing data, all independently
verified via Whisper transcription on the API's own claimed time spans.

The verification method
-----------------------
For each suspect verse, we extract the audio between
`api.timestamp_from` and `api.timestamp_to`, transcribe it with Whisper
(large-v3 / medium), and compare the transcribed text to the canonical
`text_uthmani` for that verse and its neighbors. Numbers below are
character-level longest-common-subsequence ratios after diacritic
stripping (1.00 = perfect match).

# Finding 1 — Surah 82 (Al-Infitar) verses 9-13, 16, 19

API timestamps for verses 9-13 actually contain verse 8-12's audio (off by
1). Verse 16 contains verse 14's audio (off by 2). Verse 19 contains verse
18's audio (off by 1).

```
API claim       Whisper transcribed (medium)        sim vs   sim vs    Audio actually
                                                    claimed  shifted   recites
82:9   42.84-48.46s   "ما شاء ركبك"             0.23     0.64 (-1)   verse 8 tail
82:10  48.46-53.95s   "لا بل تكذبون بالدين"      0.40     0.97 (-1)   verse 9
82:11  53.95-58.26s   "وإن عليكم لحافظين"        0.40     0.97 (-1)   verse 10
82:12  58.26-62.54s   "كراما"                    0.21     0.67 (-1)   verse 11 head
82:13  62.54-67.84s   "يعلمون ما تفعلون"        0.27     0.86 (-1)   verse 12
82:16  78.06-84.75s   "إن الفجار لفي جحيم"       0.31     0.97 (-2)   verse 14
82:19  98.36-111.63s  "ثم ما أدراك ما يوم الدين" 0.38     0.92 (-1)   verse 18
```

The 0.97 matches are essentially exact: the API timestamp range plays
the previous verse's full text. To verify yourself: open Mishary's
Surah 82 audio and seek to 48.46 s -- you'll hear "كَلَّا بَلْ تُكَذِّبُونَ
بِٱلدِّينِ" which is verse 9, not verse 10 as the API claims.

Audio file: https://download.quranicaudio.com/qdc/mishari_al_afasy/murattal/82.mp3

# Finding 2 — Surah 37 (As-Saaffat) verses ~85-135

A long sustained shift across roughly 50 verses in the middle of
As-Saaffat: API verse N consistently plays verse N+1's audio.
Strongest single examples (best-match similarity >= 0.65):

```
API claim       Whisper transcribed                sim vs   sim vs   Audio is
                                                   claimed  shifted  actually
37:109 906.07-913.25s "كذلك نجزي المحسنين"        0.29     0.97(+1)  verse 110
37:127 1043.97-?      "إلا عباد الله المخلصين"   0.37     0.92(+1)  verse 128
37:128                "وتركنا عليه في الآخرين"    0.38     0.90(+1)  verse 129
37:99                 "رب هب لي من الصالحين"      0.27     0.83(+1)  verse 100
37:118                "وتركنا عليهما في الناس"   0.45     0.83(+1)  verse 119
37:134                "إذ نجيناه وأهله أجمعين"   0.34     0.85(+1)  verse 135
```

Many adjacent verses in this range are also flagged but with lower
similarity scores because the verses are short repeated formulae
("إنه من عبادنا المؤمنين" and similar) which are hard to differentiate
purely by character similarity. The CONSISTENT +1 offset across this
many distinct verses is the smoking gun.

Audio file: https://download.quranicaudio.com/qdc/mishari_al_afasy/murattal/37.mp3
Easy verification spot: seek to 906 seconds -- you should hear "سلام
على إبراهيم" per the API's claim for verse 109, but you'll actually
hear "كذلك نجزي المحسنين" which is verse 110.

# Finding 3 — Surah 78 (An-Naba) verses 7, 22

Less severe than 82 / 37 but still genuine.

```
API claim       Whisper transcribed                sim vs   sim vs   Audio is
                                                   claimed  shifted  actually
78:7  31.95-35.82s    "واجعل الأرض مهادا"         0.64     0.84(-1)  verse 6
78:22 115.61-119.03s  "كانت مرصادا"               0.29     0.69(-1)  verse 21
```

# Why our earlier reports for Tunaiji didn't catch this same pattern

The detector based on WhisperX-vs-API comparison only finds shifts when
WhisperX itself is confident on the affected verses. For Mishary the
median word-confidence on these surahs is 0.85+, so the comparison is
clean. For Tunaiji we initially had several "STRONG" candidates that on
this same Whisper-transcription cross-check turn out to be WhisperX
failures, not API errors. (E.g. earlier report flagged Surah 3:46 in
Tunaiji as a shift -- Whisper-verify confirms that one is correct in
the API, and our WhisperX simply failed.)

So: our pipeline's previous "verse shift" reports for Tunaiji should be
treated as preliminary; the Whisper-transcription cross-check is the
authoritative independent signal, and it is now part of the standard
pipeline.

# Reproducing

```
.venv/Scripts/python.exe fetch_reciter.py 7
.venv/Scripts/python.exe batch_align.py --reciter-id 7
.venv/Scripts/python.exe heal_alignment.py --reciter-id 7
.venv/Scripts/python.exe verify_with_whisper.py --reciter-id 7 \
    --model-size medium 82 37 78
```

Output:
  reports/whisper_verify_r7.json
  reciters/r7/data/corrected_v2/surah_<N>_*

# Status of the rest of Mishary

A full pass with Whisper-verify on the remaining 107 surahs is running
in the background. I'll surface any additional confirmed shifts when it
completes. Initial detector pass (no Whisper) flagged a few other
surahs for follow-up but most were `WX_GLITCH` (our alignment failed,
not an API issue).
