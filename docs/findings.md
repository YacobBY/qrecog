# Findings

Confirmed mistimings in the quran.com / QUL recitation API per
reciter, accumulated as the qrfix pipeline ran across all 12 reciters
on quran.com. Two categories:

1. **Whole-verse shift** — the API span for verse N actually contains a
   different verse's audio. Confirmed by Whisper-transcribing the API
   span with `large-v3` and seeing the result match a *different*
   canonical verse with character-similarity ≥ 0.70.
2. **Boundary drift** — the verse identity is right, but the boundary
   timestamp is off by ≥ 150 ms. Caught by silence-anchored fix
   generator.

## Headline numbers

| reciter | id | confirmed shifts | drifted boundaries |
|---------|---:|-----------------:|-------------------:|
| Sudais (Abdur-Rahman as-) | 3 | 157 | (in progress) |
| Tunaiji (Khalifah Al) | 161 | 39 | 104 |
| Mishary al-Afasy | 7 | 23 | (in progress) |
| AbdulBaset (alt) | 2 | 13 | (in progress) |
| Shatri (Abu Bakr) | 4 | 7 | (in progress) |
| Hani ar-Rifai | 5 | 5 | (in progress) |
| Minshawi (alt) | 9 | 3 | (in progress) |
| Tablawi (Mohamed al-) | 11 | 2 | (in progress) |

Reciters not yet fully scanned: Husary (id 6) — alignment finished but
verify pass interrupted; Husary alt (id 12), Sudais (id 3), AbdulBaset
(id 1), Minshawi (id 8 — quran.com gives a 404 on the audio URL).

## Mishary al-Afasy (id 7)

**Surah 82 (Al-Infitar) verses 9-19** — the cleanest case to file
upstream first. Mostly off by -1 (occasionally -2). Audibly verifiable
in 30 seconds with the demo player.

| API verse | Whisper transcribed | matches canonical verse | sim |
|-----------|---------------------|-------------------------|-----:|
| 82:10 | "لا بل تكذبون بالدين" | 82:9 | 0.97 |
| 82:11 | "وان عليكم لحافظين" | 82:10 | 0.97 |
| 82:13 | "يعلمون ما تفعلون" | 82:12 | 0.86 |
| 82:16 | "إن الفجار لفي جحيم" | 82:14 (off by -2) | 0.97 |
| 82:19 | "ثم ما أدراك ما يوم الدين" | 82:18 | 0.92 |

**Surah 37 (As-Saffat) verses 89-148** — sustained +1 shift across
~50 verses. Verses 89, 91, 94, 99, 109, 115, 118-119, 122, 127-128,
133-134, 139-141, 146, 148.

## Tunaiji (id 161)

**Surah 10 (Yunus)** — 29 confirmed whole-verse shifts (+1 or +2).
The largest cluster of any reciter:
verses 28, 31-32, 43, 46-47, 51-52, 57, 64, 69, 72, 74-77, 80-81,
83-84, 88, 95, 98-99, 101-103, 107-108.

**Surah 13 (Ar-Rad) verses 13-33** — sustained boundary drift, API
fires 0.5-2.5 s **early**. Worst single boundary 13:13→14 at +2.49 s.
Drift gradually decays back to zero by verse 34.

The early-Surah-13 verses 2-5 are *also* whole-verse shifts (-1
offset), confirmed by Whisper-verify.

**Surah 14 (Ibrahim) verses 5, 36** — whole-verse shifts (+1).

**Surah 34 (Saba) verses 48-49** — whole-verse shifts (+1).

**Other shifts**: 2:150 (-1), 5:44 (+3).

**Other surahs with boundary drift only** (verse identity ok):
1, 4, 17, 19, 24, 33, 38, 41, 43, 44, 52, 53, 55, 68, 72, 75, 78, 79,
89, 91, 111. Total 104 drifted boundaries across 23 surahs.

The full per-verse delta table is in `reports/all_corrections.md`.

## Sudais (id 3)

**157 high-confidence shifts** spread across Surahs 3, 4, 5, 28, 29
— by far the worst reciter on quran.com. Surah 4 alone has 42 shifts.
Mixed offsets (-3, -2, -1, +1, +2, +3) suggest the underlying QUL
data was generated from a different recitation source than what's
currently served.

Recommend filing this as one big QUL issue with the full table
attached, rather than per-surah issues.

## AbdulBaset AbdulSamad (alt, id 2)

**Surah 2 (Al-Baqarah) — 13 shifts** in verses 27, 30-31, 33, 38-41,
44-46, 48, 59. Mixed offsets (-3, -2, -1).

## Shatri (id 4)

- **Surah 10 verses 47, 78, 81, 95, 104, 108** — all +1 shifts.
- **Surah 2 verse 150** — -1 shift.

## Hani ar-Rifai (id 5)

- **Surah 16 verses 83, 99, 110, 122, 128** — all -1 shifts.

## Minshawi murattal (id 9)

- **Surah 4 verses 131, 168-169** — +1 shifts.

## Tablawi (id 11)

- **Surah 4 verses 121, 168** — -1 shifts.

## Methodology and reproducibility

Every entry above can be reproduced with the same single command:

```bash
python analyze_tunaiji.py                    # for Tunaiji
python process_reciter.py 7 --name "Mishary" # for any other reciter
```

The `reports/whisper_verify*.json` files preserve the per-verse
character-similarity numbers so anyone can audit the threshold or
re-run with a different similarity floor.

## Suggested upstream filing order

In approximate "easiest to defend first" order:

1. **Mishary 82:9-13** — small, contiguous, audibly obvious. Best
   first PR / issue.
2. **Tunaiji 1:4-6** — the original user-reported bug. Three
   boundaries, well-bounded.
3. **Mishary 37 cluster** — bigger but very consistent (~50 verses,
   all +1).
4. **Tunaiji 13:13-33** — boundary drift, not whole-verse shift —
   filing this requires explaining the methodology slightly.
5. **Sudais full surahs 3-5, 28-29** — only after the smaller fixes
   land and the methodology is accepted upstream.

A ready-to-paste issue body for case 1 is at
`reports/qul_issue_mishary_surah82.md`.

## Filing path

QUL FAQ #5 documents two methods:

- **GitHub issue** at
  <https://github.com/TarteelAI/quranic-universal-library/issues/new/choose>.
- **Direct edit access** by clicking "Send Access Request" at
  <https://qul.tarteel.ai/tools> for the Audio Segments resource.

Either way, attach the `surah_<N>_qul.csv` and link to a screen-
recording of the demo player from `build_demo.py`.
