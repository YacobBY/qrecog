# [Audio Timing] Mishary al-Afasy (recitation_id 7) — Surah 82 verses 9-19 are off by 1-2

## Summary

For reciter 7 (Mishari Rashid al-`Afasy), the per-verse `timestamp_from`
/ `timestamp_to` values served by `GET /api/v4/chapter_recitations/7/82?segments=true`
are misaligned for verses 9, 10, 11, 12, 13, 16, and 19 of Surah
Al-Infitar (82). Each of these verses' API span actually plays one or
two verses earlier in the recitation. The translation column on
quran.com therefore displays the wrong English/translation while the
audio plays for these verses.

## Audible verification (please reproduce)

Audio file: https://download.quranicaudio.com/qdc/mishari_al_afasy/murattal/82.mp3

| Seek to | API says you should hear | You actually hear (verse) |
|---------|--------------------------|----------------------------|
| **48.46 s** | verse **10** "وَإِنَّ عَلَيْكُمْ لَحَـٰفِظِينَ" | verse **9**  "كَلَّا بَلْ تُكَذِّبُونَ بِٱلدِّينِ" |
| **53.95 s** | verse **11** "كِرَامًۭا كَـٰتِبِينَ" | verse **10** "وَإِنَّ عَلَيْكُمْ لَحَـٰفِظِينَ" |
| **62.54 s** | verse **13** "إِنَّ ٱلْأَبْرَارَ لَفِى نَعِيمٍۢ" | verse **12** "يَعْلَمُونَ مَا تَفْعَلُونَ" |
| **78.06 s** | verse **16** "وَمَا هُمْ عَنْهَا بِغَآئِبِينَ" | verse **14** "إِنَّ ٱلْأَبْرَارَ لَفِى نَعِيمٍۢ" (off by 2) |
| **98.36 s** | verse **19** "يَوْمَ لَا تَمْلِكُ نَفْسٌۭ..." | verse **18** "ثُمَّ مَآ أَدْرَىٰكَ مَا يَوْمُ ٱلدِّينِ" |

## Programmatic verification

Whisper large-v3 transcription of each API span, compared to the
canonical `text_uthmani` for that verse and its neighbours via
character-level longest-common-subsequence (length-normalized; 1.00 =
exact match after diacritic stripping):

| API verse | API span (ms) | Whisper transcribed | sim vs *claimed* | sim vs *true* (offset) |
|-----------|---------------|---------------------|-----------------:|-----------------------:|
| 82:9  | 42 840 - 48 460 | "ما شاء ركبك" | 0.23 | **0.64** (-1) |
| 82:10 | 48 460 - 53 950 | "لا بل تكذبون بالدين" | 0.40 | **0.97** (-1) |
| 82:11 | 53 950 - 58 260 | "وان عليكم لحافظين" | 0.40 | **0.97** (-1) |
| 82:12 | 58 260 - 62 540 | "كراما" | 0.21 | **0.67** (-1) |
| 82:13 | 62 540 - 67 840 | "يعلمون ما تفعلون" | 0.27 | **0.86** (-1) |
| 82:16 | 78 060 - 84 750 | "إن الفجار لفي جحيم" | 0.31 | **0.97** (-2) |
| 82:19 | 98 360 - 111 630 | "ثم ما أدراك ما يوم الدين" | 0.38 | **0.92** (-1) |

Reproduction script:
```
.venv/Scripts/python.exe verify_with_whisper.py --reciter-id 7 \
    --model-size large-v3 --verbose 82
```

## Suggested fix

The shift starts at verse 9 and continues; the audio chunks themselves
appear correct (Mishary recites all 19 verses cleanly), so the fix is
to shift each affected verse's `timestamp_from` and `timestamp_to`
later by the duration of one verse. Most cleanly done by re-running the
forced-aligner on this surah with the canonical text and writing the
result to `data/raw_segments/7/timing/82.csv`.

## Methodology

* WhisperX forced alignment with `jonatasgrosman/wav2vec2-large-xlsr-53-arabic`
  agrees with the Whisper-transcription cross-check on all 7 listed
  verses (median per-word score 0.85+).
* Both signals are independent: the wav2vec2 model is a CTC aligner
  (uses canonical text), Whisper is a sequence-to-sequence transcriber
  (does not). Their agreement means the issue is in the API timing
  data, not in any single model's output.
* `Audio::Recitation.find_by(reciter_id: 7)` -- please advise on
  `segment_locked` status if the fix needs editorial coordination
  before bulk re-import.

## Related (separate issues, similar pattern)

The same cross-check methodology found additional shifts in Mishary
recitation 7 that I'll file separately if helpful:

* **Surah 37 verses ~85-135**: sustained +1 shift across ~50 verses
  (API verse N plays verse N+1's audio). Largest cluster found.
* **Surah 78 verses 7 and 22**: isolated -1 shifts.
