# All off-timestamp findings — Khalifah Al Tunaiji (reciter 161)

**97 unique inter-verse boundaries off** across 24 of 114 surahs. Other 90
surahs are clean within the ±150 ms detection floor.

Direction:
  * **68 EARLY** (API flips translation BEFORE the verse audibly ends)
  * **29 LATE** (translation lags into the next verse)

Magnitude buckets:

```
                LATE   EARLY
  150-200 ms:     1      6
  200-300 ms:     4     24
  300-500 ms:     8     15
  500-1000 ms:   12     10
  1000-1500 ms:   4     11
  >=1500 ms:      0      2
```

## Per-surah summary

| #bnd | Surah | Affected verses | Max correction | Median correction | Direction |
|-----:|------:|:----------------|---------------:|------------------:|:----------|
|   20 |    10 | 10:1 → 10:106    |   +1309 ms     |    +51 ms         | EARLY (mixed) |
|   15 |    13 | 13:20 → 13:42    |   +1574 ms     |   +953 ms         | EARLY (sustained) |
|   12 |    14 | 14:2 → 14:47     |   +1456 ms     |   -280 ms         | mixed |
|    8 |     4 | 4:30 → 4:98      |    +355 ms     |   +262 ms         | EARLY |
|    7 |    55 | 55:14 → 55:68    |    +331 ms     |   +275 ms         | EARLY |
|    5 |    72 | 72:12 → 72:17    |    -949 ms     |   -610 ms         | LATE |
|    5 |    79 | 79:1 → 79:43     |    +333 ms     |   +223 ms         | EARLY |
|    4 |    43 | 43:53 → 43:69    |    +330 ms     |   +240 ms         | EARLY |
|    3 |     1 | 1:4 → 1:6        |    -434 ms     |   -430 ms         | LATE  (user-reported) |
|    3 |    44 | 44:21 → 44:35    |    +344 ms     |   +314 ms         | EARLY |
|    2 |    33 | 33:15 → 33:64    |    -280 ms     |    -15 ms         | mixed |
|    1 |    17 | 17:110           |    +311 ms     |                   | EARLY |
|    1 |    19 | 19:97            |    +374 ms     |                   | EARLY |
|    1 |    24 | 24:6             |    +290 ms     |                   | EARLY |
|    1 |    38 | 38:39            |    +364 ms     |                   | EARLY |
|    1 |    41 | 41:10            |    +230 ms     |                   | EARLY |
|    1 |    52 | 52:39            |    +211 ms     |                   | EARLY |
|    1 |    53 | 53:14            |    +267 ms     |                   | EARLY |
|    1 |    68 | 68:21            |    +276 ms     |                   | EARLY |
|    1 |    75 | 75:8             |    +226 ms     |                   | EARLY |
|    1 |    78 | 78:29            |    +208 ms     |                   | EARLY |
|    1 |    89 | 89:7             |    +276 ms     |                   | EARLY |
|    1 |    91 | 91:4             |    +404 ms     |                   | EARLY |
|    1 |   111 | 111:2            |    +235 ms     |                   | EARLY |

## Standout cases

### Surah 13 — sustained EARLY drift cluster (clearest evidence)
12 consecutive verses (20-31) with API timestamps 670-1574 ms before the
real boundary, gradually decaying back to zero. Three more isolated
corrections (33, 39, 41-42).

```
13:20  api_to= 543090 -> new_to= 544528  delta= +1438 ms
13:22  api_to= 589430 -> new_to= 591004  delta= +1574 ms
13:23  api_to= 612420 -> new_to= 613938  delta= +1518 ms
13:24  api_to= 621640 -> new_to= 623035  delta= +1395 ms
13:25  api_to= 652620 -> new_to= 653811  delta= +1191 ms
13:26  api_to= 670960 -> new_to= 672079  delta= +1119 ms
13:27  api_to= 694600 -> new_to= 695590  delta=  +990 ms
13:28  api_to= 711420 -> new_to= 712373  delta=  +953 ms
13:29  api_to= 720880 -> new_to= 721574  delta=  +694 ms
13:30  api_to= 720880 -> new_to= 760181  delta=  +771 ms
13:31  api_to= 759410 -> new_to= 812300  delta=  +670 ms
13:33  api_to= 869260 -> new_to= 869710  delta=  +450 ms
13:42  api_to=1032500 -> new_to=1050683  delta=  -307 ms
```

### Surah 10 — many smaller drifts in second half
Mostly EARLY (translation flips ~600 ms before the verse ends), with
some LATE outliers. Concentrated 10:79-10:107, with a separate
LATE cluster early at 10:1-10:7.

```
10:5   api_to= 134390 -> new_to= 133353  delta= -1037 ms (LATE)
10:6   api_to= 150250 -> new_to= 149022  delta= -1228 ms (LATE)
10:79  api_to=1770440 -> new_to=1771516  delta= +1076 ms (EARLY)
10:82  api_to=1814420 -> new_to=1815488  delta= +1068 ms (EARLY)
10:87  api_to=1903150 -> new_to=1904278  delta= +1128 ms (EARLY)
10:92  api_to=2018160 -> new_to=2019469  delta= +1309 ms (EARLY)
```

### Surah 14 — bidirectional, large
Both directions, up to 1.5 s. Worst single offsets:

```
14:14  api_to= 358650 -> new_to= 357449  delta= -1201 ms (LATE)
14:18  api_to= 431390 -> new_to= 432846  delta= +1456 ms (EARLY)
14:34  api_to= 753360 -> new_to= 754591  delta= +1231 ms (EARLY)
14:42  api_to= 898630 -> new_to= 900023  delta= +1393 ms (EARLY)
14:45  api_to= 964170 -> new_to= 962939  delta= -1231 ms (LATE)
14:27  api_to= 634330 -> new_to= 633380  delta=  -950 ms (LATE)
14:8   api_to= 216790 -> new_to= 216234  delta=  -556 ms (LATE)
```

### Surah 72 — short LATE cluster
5 consecutive boundaries running 318-949 ms LATE in verses 12-17.

```
72:13  api_to= 139820 -> new_to= 139502  delta=  -318 ms
72:14  api_to= 157220 -> new_to= 156800  delta=  -420 ms
72:15  api_to= 173000 -> new_to= 172390  delta=  -610 ms
72:16  api_to= 190710 -> new_to= 179635  delta=  -625 ms (chain)
72:17  api_to= 203540 -> new_to= 202591  delta=  -949 ms
```

### Surah 1 — user-reported, smallest cluster
The original report. Verses 4-6 LATE by 147/284/280 ms.

```
1:4  api_to= 21420 -> new_to= 21123  delta= -297 ms
1:5  api_to= 27720 -> new_to= 27286  delta= -434 ms
1:6  api_to= 33000 -> new_to= 32570  delta= -430 ms
```

## Where to find the raw data

  * Per-verse diffs: `data/corrected_v2/surah_<N>_diff.json`
  * Corrected timestamps in API shape: `data/corrected_v2/surah_<N>_corrected.json`
  * QUL-style CSVs: `data/corrected_v2/surah_<N>_qul.csv`
  * A/B audio demos: `demo/surah_<N>_v2.html`
