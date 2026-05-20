# Khalifah Al Tunaiji (reciter id 161) — full timing analysis

Comprehensive audit of the per-verse audio-to-translation timing data served by `api.quran.com/api/v4/chapter_recitations/161/<surah>` for every surah in the recitation.

- **Whole-verse shifts** are flagged when Whisper-large-v3 transcribes the API span and the result matches a *neighbour* verse with char-similarity ≥ 0.70 (and ≥ 0.20 better than the claimed verse). This is the most reliable signal — independent of CTC alignment.
- **Boundary drifts** are flagged when the silence-anchored hybrid fix moves the API verse-end by ≥ 150 ms (audibly perceptible).

**Every finding below is independently verifiable by clicking the 🔊 link** — it plays the exact disputed audio span in your browser via an HTML5 media-fragment URL (no player setup needed). The verse-page links open quran.com with this reciter preselected.

---

## Headline

- **39 confirmed whole-verse shifts** (across 6 surahs)
- **104 drifted boundaries** ≥ 150 ms (across 23 surahs)
- **26 surahs** have at least one issue; **88 surahs** are clean.

## Whole-verse shifts — per-surah summary

| surah | name | shifts | offsets | verses |
|------:|:-----|-------:|--------:|--------|
| 2 | Al-Baqarah | 1 | -1 | 150 |
| 5 | Al-Maidah | 1 | +3 | 44 |
| 10 | Yunus | 29 | +1, +2 | 28, 31-32, 43, 46-47, 51-52, 57, 64, 69, 72, 74-77, 80-81, 83-84, 88, 95, 98-99, 101-103, 107-108 |
| 13 | Ar-Rad | 4 | -1 | 2-5 |
| 14 | Ibrahim | 2 | +1 | 5, 36 |
| 34 | Saba | 2 | +1 | 48-49 |

## Whole-verse shifts — per-verse evidence

Each card below is one confirmed shift. The 🔊 link plays the exact API-claimed span; it should sound like the *Audio actually contains* verse, not the *API claims* verse.

### Surah 2 — Al-Baqarah (1 shift)

#### 2:150 (offset -1)
- API claims: [2:150](https://quran.com/2/150?reciter=161)
- Audio actually contains: [2:149](https://quran.com/2/149?reciter=161)
- 🔊 [Listen (53:58.87–54:34.61)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/2.mp3#t=3238.77,3274.71)
- char-similarity: vs claimed `0.49` · vs actual `0.74`
- Whisper heard: `ومنحيثخرجتفولوجهكشطرالمسجدالحراموليعلكمتهتدون`


### Surah 5 — Al-Maidah (1 shift)

#### 5:44 (offset +3)
- API claims: [5:44](https://quran.com/5/44?reciter=161)
- Audio actually contains: [5:47](https://quran.com/5/47?reciter=161)
- 🔊 [Listen (22:18.93–23:09.76)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/5.mp3#t=1338.83,1389.86)
- char-similarity: vs claimed `0.47` · vs actual `0.70`
- Whisper heard: `اناانزلناالتوراهفيهاهديونورومنلميحكمبماانزلاللهفاولئكهمالكافرون`


### Surah 10 — Yunus (29 shifts)

#### 10:28 (offset +1)
- API claims: [10:28](https://quran.com/10/28?reciter=161)
- Audio actually contains: [10:29](https://quran.com/10/29?reciter=161)
- 🔊 [Listen (12:22.74–12:50.61)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=742.64,770.71)
- char-similarity: vs claimed `0.32` · vs actual `0.74`
- Whisper heard: `وكفيباللهشهيدابينناوبينكمانا`

#### 10:31 (offset +1)
- API claims: [10:31](https://quran.com/10/31?reciter=161)
- Audio actually contains: [10:32](https://quran.com/10/32?reciter=161)
- 🔊 [Listen (13:26.01–13:58.04)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=805.91,838.14)
- char-similarity: vs claimed `0.29` · vs actual `0.79`
- Whisper heard: `فذلكماللهربكمالحقبعدالحقالاالضوء`

#### 10:32 (offset +1)
- API claims: [10:32](https://quran.com/10/32?reciter=161)
- Audio actually contains: [10:33](https://quran.com/10/33?reciter=161)
- 🔊 [Listen (13:58.04–14:11.10)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=837.94,851.20)
- char-similarity: vs claimed `0.43` · vs actual `0.78`
- Whisper heard: `كذلكحقتكلمهربكعليالذينفسقون`

#### 10:43 (offset +1)
- API claims: [10:43](https://quran.com/10/43?reciter=161)
- Audio actually contains: [10:44](https://quran.com/10/44?reciter=161)
- 🔊 [Listen (17:32.53–17:47.99)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1052.43,1068.09)
- char-similarity: vs claimed `0.45` · vs actual `0.89`
- Whisper heard: `اناللهلايظلمالناسشيئاولكنالناسانيتعلمون`

#### 10:46 (offset +1)
- API claims: [10:46](https://quran.com/10/46?reciter=161)
- Audio actually contains: [10:47](https://quran.com/10/47?reciter=161)
- 🔊 [Listen (18:24.75–18:42.72)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1104.65,1122.82)
- char-similarity: vs claimed `0.33` · vs actual `0.80`
- Whisper heard: `ولكلامهرسولفاذاجاءرسولهمقضيبينهما`

#### 10:47 (offset +1)
- API claims: [10:47](https://quran.com/10/47?reciter=161)
- Audio actually contains: [10:48](https://quran.com/10/48?reciter=161)
- 🔊 [Listen (18:42.72–18:58.65)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1122.62,1138.75)
- char-similarity: vs claimed `0.35` · vs actual `0.98`
- Whisper heard: `ويقولونمتيهذاالوعدانكنتمصادقين`

#### 10:51 (offset +1)
- API claims: [10:51](https://quran.com/10/51?reciter=161)
- Audio actually contains: [10:52](https://quran.com/10/52?reciter=161)
- 🔊 [Listen (19:51.78–20:09.36)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1191.68,1209.46)
- char-similarity: vs claimed `0.34` · vs actual `0.80`
- Whisper heard: `وقدكنتمبهتستعجلونثمقيلللذينظلمواذوقواعذابالخلدهلتجزونالابماكنتم`

#### 10:52 (offset +1)
- API claims: [10:52](https://quran.com/10/52?reciter=161)
- Audio actually contains: [10:53](https://quran.com/10/53?reciter=161)
- 🔊 [Listen (20:09.36–20:23.34)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1209.26,1223.44)
- char-similarity: vs claimed `0.29` · vs actual `0.75`
- Whisper heard: `ويستنبئونكاحقهوقلايوربديانهلحق`

#### 10:57 (offset +1)
- API claims: [10:57](https://quran.com/10/57?reciter=161)
- Audio actually contains: [10:58](https://quran.com/10/58?reciter=161)
- 🔊 [Listen (21:33.33–21:55.09)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1293.23,1315.19)
- char-similarity: vs claimed `0.45` · vs actual `0.73`
- Whisper heard: `وشفاءلمافيالصدوروهداورحمهللمؤمنينقلبفضلاللهوبرحمتهفبذلكفليفرحواهوخيرممايجمعون`

#### 10:64 (offset +1)
- API claims: [10:64](https://quran.com/10/64?reciter=161)
- Audio actually contains: [10:65](https://quran.com/10/65?reciter=161)
- 🔊 [Listen (24:06.07–24:23.13)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1445.97,1463.23)
- char-similarity: vs claimed `0.45` · vs actual `1.00`
- Whisper heard: `ولايحزنكقولهمانالعزهللهجميعاهوالسميعالعليم`

#### 10:69 (offset +1)
- API claims: [10:69](https://quran.com/10/69?reciter=161)
- Audio actually contains: [10:70](https://quran.com/10/70?reciter=161)
- 🔊 [Listen (25:50.19–25:59.52)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1550.09,1559.62)
- char-similarity: vs claimed `0.45` · vs actual `0.87`
- Whisper heard: `الينامرجعهمثمنذيقهمالعذابالشديدبماكانوايكفرون`

#### 10:72 (offset +1)
- API claims: [10:72](https://quran.com/10/72?reciter=161)
- Audio actually contains: [10:73](https://quran.com/10/73?reciter=161)
- 🔊 [Listen (27:00.99–27:21.47)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1620.89,1641.57)
- char-similarity: vs claimed `0.38` · vs actual `0.79`
- Whisper heard: `فكذبوهفنجيناهومنمعهفيالفلكوجعلناهمخلائفواغرقناالذينكذبوابايه`

#### 10:74 (offset +1)
- API claims: [10:74](https://quran.com/10/74?reciter=161)
- Audio actually contains: [10:75](https://quran.com/10/75?reciter=161)
- 🔊 [Listen (27:45.42–28:11.26)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1665.32,1691.36)
- char-similarity: vs claimed `0.40` · vs actual `0.71`
- Whisper heard: `بماكذبوابهمنقبلكذلكنطبععليقلوبالمعتدينثمبعثنامنبعدهمموسيوهاروناليفرعونوملئهبايات…`

#### 10:75 (offset +1)
- API claims: [10:75](https://quran.com/10/75?reciter=161)
- Audio actually contains: [10:76](https://quran.com/10/76?reciter=161)
- 🔊 [Listen (28:11.26–28:29.47)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1691.16,1709.57)
- char-similarity: vs claimed `0.37` · vs actual `0.97`
- Whisper heard: `فلماجاءهمالحقمنعندناقالواانهذالسحرمبين`

#### 10:76 (offset +1)
- API claims: [10:76](https://quran.com/10/76?reciter=161)
- Audio actually contains: [10:77](https://quran.com/10/77?reciter=161)
- 🔊 [Listen (28:29.47–28:44.33)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1709.37,1724.43)
- char-similarity: vs claimed `0.41` · vs actual `0.97`
- Whisper heard: `قالموسياتقولونللحقلماجاءكماسحرهذاولايفلحالساحرون`

#### 10:77 (offset +1)
- API claims: [10:77](https://quran.com/10/77?reciter=161)
- Audio actually contains: [10:78](https://quran.com/10/78?reciter=161)
- 🔊 [Listen (28:44.33–29:00.87)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1724.23,1740.97)
- char-similarity: vs claimed `0.40` · vs actual `0.77`
- Whisper heard: `قالوااجئتنالتلفتناعماوجدناعليهاباءناوتكونلكمالكبريا`

#### 10:80 (offset +1)
- API claims: [10:80](https://quran.com/10/80?reciter=161)
- Audio actually contains: [10:81](https://quran.com/10/81?reciter=161)
- 🔊 [Listen (29:30.44–29:46.84)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1770.34,1786.94)
- char-similarity: vs claimed `0.44` · vs actual `0.91`
- Whisper heard: `فلماالقواقالموسيماجئتمبهالسحراناللهسيبطلهاناللهلايصلحعمله`

#### 10:81 (offset +1)
- API claims: [10:81](https://quran.com/10/81?reciter=161)
- Audio actually contains: [10:82](https://quran.com/10/82?reciter=161)
- 🔊 [Listen (29:46.84–30:05.54)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1786.74,1805.64)
- char-similarity: vs claimed `0.38` · vs actual `0.77`
- Whisper heard: `ويحقاللهالحقبكلماتهولوكرهالمجرمونفماامنلموسيالاذريا`

#### 10:83 (offset +1)
- API claims: [10:83](https://quran.com/10/83?reciter=161)
- Audio actually contains: [10:84](https://quran.com/10/84?reciter=161)
- 🔊 [Listen (30:14.42–30:41.54)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1814.32,1841.64)
- char-similarity: vs claimed `0.45` · vs actual `0.97`
- Whisper heard: `وقالموسيياقومانكنتمامنتمباللهفعليهتوكلواانكنتممسلمين`

#### 10:84 (offset +1)
- API claims: [10:84](https://quran.com/10/84?reciter=161)
- Audio actually contains: [10:85](https://quran.com/10/85?reciter=161)
- 🔊 [Listen (30:41.54–30:59.83)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1841.44,1859.93)
- char-similarity: vs claimed `0.46` · vs actual `0.99`
- Whisper heard: `فقالواعلياللهتوكلناربنالاتجعلنافتنهللقومالظالمين`

#### 10:88 (offset +1)
- API claims: [10:88](https://quran.com/10/88?reciter=161)
- Audio actually contains: [10:89](https://quran.com/10/89?reciter=161)
- 🔊 [Listen (31:43.15–32:15.49)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1903.05,1935.59)
- char-similarity: vs claimed `0.39` · vs actual `0.87`
- Whisper heard: `قالقداجيبالدعوتكمافاستقيماولاتتبعنسبيلالذينلايعلمونوجاوزنابيك`

#### 10:95 (offset +2)
- API claims: [10:95](https://quran.com/10/95?reciter=161)
- Audio actually contains: [10:97](https://quran.com/10/97?reciter=161)
- 🔊 [Listen (34:36.51–34:48.21)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2076.41,2088.31)
- char-similarity: vs claimed `0.42` · vs actual `0.94`
- Whisper heard: `ولوجاءتهمكلايهحتييرواالعذابالاولي`

#### 10:98 (offset +1)
- API claims: [10:98](https://quran.com/10/98?reciter=161)
- Audio actually contains: [10:99](https://quran.com/10/99?reciter=161)
- 🔊 [Listen (35:08.66–35:33.53)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2108.56,2133.63)
- char-similarity: vs claimed `0.44` · vs actual `0.81`
- Whisper heard: `الحياهالدنياومتعناهماليحينولوشاءربكلامنمنفيالارضكلهمجميعاافانتتكرهالناسحتييكونوا…`

#### 10:99 (offset +1)
- API claims: [10:99](https://quran.com/10/99?reciter=161)
- Audio actually contains: [10:100](https://quran.com/10/100?reciter=161)
- 🔊 [Listen (35:33.53–35:52.76)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2133.43,2152.86)
- char-similarity: vs claimed `0.42` · vs actual `1.00`
- Whisper heard: `وماكانلنفسانتؤمنالاباذناللهويجعلالرجسعليالذينلايعقلون`

#### 10:101 (offset +1)
- API claims: [10:101](https://quran.com/10/101?reciter=161)
- Audio actually contains: [10:102](https://quran.com/10/102?reciter=161)
- 🔊 [Listen (36:08.12–36:23.53)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2168.02,2183.63)
- char-similarity: vs claimed `0.44` · vs actual `0.86`
- Whisper heard: `مثلايامالذينحلوامنقبلهمقلفانتظرواانيمعكممنالمنتظرين`

#### 10:102 (offset +1)
- API claims: [10:102](https://quran.com/10/102?reciter=161)
- Audio actually contains: [10:103](https://quran.com/10/103?reciter=161)
- 🔊 [Listen (36:23.53–36:42.78)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2183.43,2202.88)
- char-similarity: vs claimed `0.45` · vs actual `0.98`
- Whisper heard: `ثمننجيرسلناوالذينامنواكذلكحقاعليناننجيالمؤمنين`

#### 10:103 (offset +1)
- API claims: [10:103](https://quran.com/10/103?reciter=161)
- Audio actually contains: [10:104](https://quran.com/10/104?reciter=161)
- 🔊 [Listen (36:42.78–36:56.18)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2202.68,2216.28)
- char-similarity: vs claimed `0.41` · vs actual `0.70`
- Whisper heard: `اذاكنتمفيشكمندينيفلااعبدالذينتعبدونمندوناللهولكناعبدالله`

#### 10:107 (offset +1)
- API claims: [10:107](https://quran.com/10/107?reciter=161)
- Audio actually contains: [10:108](https://quran.com/10/108?reciter=161)
- 🔊 [Listen (37:50.81–38:21.27)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2270.71,2301.37)
- char-similarity: vs claimed `0.34` · vs actual `0.83`
- Whisper heard: `قلياايهاالناسقدجاءكمالحقمنربكمفمناهتدافانمايهتديلنفسهومنضلفانمايضل`

#### 10:108 (offset +1)
- API claims: [10:108](https://quran.com/10/108?reciter=161)
- Audio actually contains: [10:109](https://quran.com/10/109?reciter=161)
- 🔊 [Listen (38:21.27–38:48.41)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2301.17,2328.51)
- char-similarity: vs claimed `0.37` · vs actual `0.83`
- Whisper heard: `ومااناعليكمبوكيلواتبعمايوحياليكواصبرحتييحكماللهوهوخيرالحاكمين`


### Surah 13 — Ar-Rad (4 shifts)

#### 13:2 (offset -1)
- API claims: [13:2](https://quran.com/13/2?reciter=161)
- Audio actually contains: [13:1](https://quran.com/13/1?reciter=161)
- 🔊 [Listen (0:00.00–0:35.21)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=0.00,35.31)
- char-similarity: vs claimed `0.41` · vs actual `0.75`
- Whisper heard: `الفلامميمراتلكاياتالكتابوالذيانزلاليكمنربكالحقولكناكثرالناسلايؤمنونالذيرفعالسماو…`

#### 13:3 (offset -1)
- API claims: [13:3](https://quran.com/13/3?reciter=161)
- Audio actually contains: [13:2](https://quran.com/13/2?reciter=161)
- 🔊 [Listen (0:35.21–1:03.76)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=35.11,63.86)
- char-similarity: vs claimed `0.44` · vs actual `0.83`
- Whisper heard: `ثماستويعليالعرشوسخرالشمسوالقمركليجريلاجلمسمييدبرالامريفصلالاياتلعلكمبلقاءربكمتوق…`

#### 13:4 (offset -1)
- API claims: [13:4](https://quran.com/13/4?reciter=161)
- Audio actually contains: [13:3](https://quran.com/13/3?reciter=161)
- 🔊 [Listen (1:03.76–1:42.00)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=63.66,102.09)
- char-similarity: vs claimed `0.43` · vs actual `0.85`
- Whisper heard: `وهوالذيمدالارضوجعلفيهارواسيوانهاراومنكلالثمراتجعلفيهازوجيناثنينيغشيالليلالنهاران…`

#### 13:5 (offset -1)
- API claims: [13:5](https://quran.com/13/5?reciter=161)
- Audio actually contains: [13:4](https://quran.com/13/4?reciter=161)
- 🔊 [Listen (1:42.22–2:19.71)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=102.12,139.81)
- char-similarity: vs claimed `0.39` · vs actual `0.73`
- Whisper heard: `وزرعونخيلصنوانوغيرصنوانيسقيبماءواحدونفضلبعضهاعليبعضفيالاكلانفيذلكلاياتلقوميعقلون…`


### Surah 14 — Ibrahim (2 shifts)

#### 14:5 (offset +1)
- API claims: [14:5](https://quran.com/14/5?reciter=161)
- Audio actually contains: [14:6](https://quran.com/14/6?reciter=161)
- 🔊 [Listen (1:26.96–2:11.63)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=86.86,131.73)
- char-similarity: vs claimed `0.38` · vs actual `0.78`
- Whisper heard: `واذقالموسيلقومهاذكروانعمهاللهعليكماذانجاكممنالعمرهيسومونكمسوءالعذابويذبحونابناءك…`

#### 14:36 (offset +1)
- API claims: [14:36](https://quran.com/14/36?reciter=161)
- Audio actually contains: [14:37](https://quran.com/14/37?reciter=161)
- 🔊 [Listen (12:51.99–13:29.68)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=771.89,809.78)
- char-similarity: vs claimed `0.41` · vs actual `0.73`
- Whisper heard: `ربناانياسكنتمنذريتيبوادغيرذيزرععندبيتكالمحرمربناليقيمالصلاهفاجعلافكارك`


### Surah 34 — Saba (2 shifts)

#### 34:48 (offset +1)
- API claims: [34:48](https://quran.com/34/48?reciter=161)
- Audio actually contains: [34:49](https://quran.com/34/49?reciter=161)
- 🔊 [Listen (16:16.72–16:25.99)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/34.mp3#t=976.62,986.09)
- char-similarity: vs claimed `0.41` · vs actual `0.93`
- Whisper heard: `قلجاءالحقومايبداالباطلومايعيد`

#### 34:49 (offset +1)
- API claims: [34:49](https://quran.com/34/49?reciter=161)
- Audio actually contains: [34:50](https://quran.com/34/50?reciter=161)
- 🔊 [Listen (16:25.99–16:41.45)](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/34.mp3#t=985.89,1001.55)
- char-similarity: vs claimed `0.36` · vs actual `0.85`
- Whisper heard: `3-قلانضللتفانمااضلعلينفسيواناهتديتفبمايوحياليربي`


## Boundary drifts — per-surah summary

| surah | name | drifts | max |Δ| (ms) | direction |
|------:|:-----|-------:|--------------:|:----------|
| 1 | Al-Fatihah | 2 | 430 | LATE (api flips after voice) |
| 4 | An-Nisa | 8 | 355 | EARLY (api flips before voice) |
| 10 | Yunus | 20 | 1309 | mixed |
| 13 | Ar-Rad | 24 | 2491 | mixed |
| 14 | Ibrahim | 12 | 1456 | mixed |
| 17 | Al-Isra | 1 | 311 | EARLY (api flips before voice) |
| 19 | Maryam | 1 | 374 | EARLY (api flips before voice) |
| 24 | An-Nur | 1 | 290 | EARLY (api flips before voice) |
| 33 | Al-Ahzab | 2 | 280 | mixed |
| 38 | Sad | 1 | 364 | EARLY (api flips before voice) |
| 41 | Fussilat | 1 | 230 | EARLY (api flips before voice) |
| 43 | Az-Zukhruf | 4 | 330 | EARLY (api flips before voice) |
| 44 | Ad-Dukhan | 3 | 344 | EARLY (api flips before voice) |
| 52 | At-Tur | 1 | 211 | EARLY (api flips before voice) |
| 53 | An-Najm | 1 | 267 | EARLY (api flips before voice) |
| 55 | Ar-Rahman | 7 | 331 | EARLY (api flips before voice) |
| 68 | Al-Qalam | 1 | 276 | EARLY (api flips before voice) |
| 72 | Al-Jinn | 5 | 949 | LATE (api flips after voice) |
| 75 | Al-Qiyamah | 1 | 226 | EARLY (api flips before voice) |
| 79 | An-Nazi'at | 5 | 333 | EARLY (api flips before voice) |
| 89 | Al-Fajr | 1 | 276 | EARLY (api flips before voice) |
| 91 | Ash-Shams | 1 | 404 | EARLY (api flips before voice) |
| 111 | Al-Masad | 1 | 235 | EARLY (api flips before voice) |

## Boundary drifts — per-verse evidence

Each entry below is one verse-end boundary that the hybrid silence + WhisperX fix moved by ≥ 150 ms. The 🔊 link plays a 3-second window around the boundary so you can hear the recitation crossing the originally-claimed time.

### Surah 1 — Al-Fatihah (2 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [1:4](https://quran.com/1/4?reciter=161) | 0:21.42 | 0:21.12 | -297 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/1.mp3#t=19.62,22.92) |
| [1:6](https://quran.com/1/6?reciter=161) | 0:33.00 | 0:32.57 | -430 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/1.mp3#t=31.07,34.50) |


### Surah 4 — An-Nisa (8 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [4:30](https://quran.com/4/30?reciter=161) | 16:53.67 | 16:53.88 | +205 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=1012.17,1015.38) |
| [4:39](https://quran.com/4/39?reciter=161) | 20:58.69 | 20:58.94 | +251 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=1257.19,1260.44) |
| [4:42](https://quran.com/4/42?reciter=161) | 21:42.08 | 21:42.43 | +353 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=1300.58,1303.93) |
| [4:43](https://quran.com/4/43?reciter=161) | 22:47.07 | 22:47.32 | +250 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=1365.57,1368.82) |
| [4:45](https://quran.com/4/45?reciter=161) | 23:15.80 | 23:16.04 | +244 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=1394.30,1397.54) |
| [4:70](https://quran.com/4/70?reciter=161) | 32:58.53 | 32:58.88 | +355 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=1977.03,1980.38) |
| [4:95](https://quran.com/4/95?reciter=161) | 45:33.02 | 45:33.37 | +350 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=2731.52,2734.87) |
| [4:98](https://quran.com/4/98?reciter=161) | 46:38.56 | 46:38.83 | +273 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/4.mp3#t=2797.06,2800.33) |


### Surah 10 — Yunus (20 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [10:1](https://quran.com/10/1?reciter=161) | 0:11.23 | 0:10.91 | -315 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=9.41,12.73) |
| [10:2](https://quran.com/10/2?reciter=161) | 0:40.46 | 0:40.03 | -430 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=38.53,41.96) |
| [10:3](https://quran.com/10/3?reciter=161) | 1:13.45 | 1:12.84 | -610 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=71.34,74.95) |
| [10:4](https://quran.com/10/4?reciter=161) | 1:45.11 | 1:44.41 | -697 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=102.91,106.61) |
| [10:5](https://quran.com/10/5?reciter=161) | 2:14.39 | 2:13.35 | -1037 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=131.85,135.89) |
| [10:6](https://quran.com/10/6?reciter=161) | 2:30.25 | 2:29.02 | -1228 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=147.52,151.75) |
| [10:29](https://quran.com/10/29?reciter=161) | 13:04.35 | 13:05.14 | +794 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=782.85,786.64) |
| [10:38](https://quran.com/10/38?reciter=161) | 16:18.79 | 16:19.42 | +629 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=977.29,980.92) |
| [10:39](https://quran.com/10/39?reciter=161) | 16:39.71 | 16:39.01 | -697 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=997.51,1001.21) |
| [10:62](https://quran.com/10/62?reciter=161) | 23:58.99 | 23:59.80 | +814 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1437.49,1441.30) |
| [10:63](https://quran.com/10/63?reciter=161) | 24:06.07 | 24:05.41 | -658 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1443.91,1447.57) |
| [10:79](https://quran.com/10/79?reciter=161) | 29:30.44 | 29:31.52 | +1076 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1768.94,1773.02) |
| [10:82](https://quran.com/10/82?reciter=161) | 30:14.42 | 30:15.49 | +1068 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1812.92,1816.99) |
| [10:87](https://quran.com/10/87?reciter=161) | 31:43.15 | 31:44.28 | +1128 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1901.65,1905.78) |
| [10:90](https://quran.com/10/90?reciter=161) | 33:11.02 | 33:11.44 | +417 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1989.52,1992.94) |
| [10:91](https://quran.com/10/91?reciter=161) | 33:21.52 | 33:21.12 | -401 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=1999.62,2003.02) |
| [10:92](https://quran.com/10/92?reciter=161) | 33:38.16 | 33:39.47 | +1309 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2016.66,2020.97) |
| [10:98](https://quran.com/10/98?reciter=161) | 35:33.53 | 35:34.13 | +603 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2132.03,2135.63) |
| [10:101](https://quran.com/10/101?reciter=161) | 36:23.53 | 36:24.35 | +820 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2182.03,2185.85) |
| [10:106](https://quran.com/10/106?reciter=161) | 37:50.81 | 37:49.99 | -824 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/10.mp3#t=2268.49,2272.31) |


### Surah 13 — Ar-Rad (24 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [13:13](https://quran.com/13/13?reciter=161) | 5:37.46 | 5:39.95 | +2491 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=335.96,341.45) |
| [13:14](https://quran.com/13/14?reciter=161) | 6:07.16 | 6:09.50 | +2344 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=365.66,371.00) |
| [13:15](https://quran.com/13/15?reciter=161) | 6:21.58 | 6:23.75 | +2171 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=380.08,385.25) |
| [13:16](https://quran.com/13/16?reciter=161) | 7:12.18 | 7:13.94 | +1761 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=430.68,435.44) |
| [13:17](https://quran.com/13/17?reciter=161) | 8:03.43 | 8:05.42 | +1991 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=481.93,486.92) |
| [13:18](https://quran.com/13/18?reciter=161) | 8:34.70 | 8:36.15 | +1451 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=513.20,517.65) |
| [13:19](https://quran.com/13/19?reciter=161) | 8:53.56 | 8:55.29 | +1735 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=532.06,536.79) |
| [13:20](https://quran.com/13/20?reciter=161) | 9:03.09 | 9:04.68 | +1588 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=541.59,546.18) |
| [13:21](https://quran.com/13/21?reciter=161) | 9:20.59 | 9:22.16 | +1570 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=559.09,563.66) |
| [13:22](https://quran.com/13/22?reciter=161) | 9:49.43 | 9:51.09 | +1656 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=587.93,592.59) |
| [13:23](https://quran.com/13/23?reciter=161) | 10:12.42 | 10:13.99 | +1571 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=610.92,615.49) |
| [13:24](https://quran.com/13/24?reciter=161) | 10:21.64 | 10:23.03 | +1395 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=620.14,624.53) |
| [13:25](https://quran.com/13/25?reciter=161) | 10:52.62 | 10:53.81 | +1191 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=651.12,655.31) |
| [13:26](https://quran.com/13/26?reciter=161) | 11:10.96 | 11:12.08 | +1119 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=669.46,673.58) |
| [13:27](https://quran.com/13/27?reciter=161) | 11:34.60 | 11:35.59 | +990 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=693.10,697.09) |
| [13:28](https://quran.com/13/28?reciter=161) | 11:51.42 | 11:52.37 | +953 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=709.92,713.87) |
| [13:29](https://quran.com/13/29?reciter=161) | 12:00.88 | 12:01.39 | +509 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=719.38,722.89) |
| [13:30](https://quran.com/13/30?reciter=161) | 12:39.41 | 12:40.18 | +771 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=757.91,761.68) |
| [13:31](https://quran.com/13/31?reciter=161) | 13:31.63 | 13:32.30 | +670 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=810.13,813.80) |
| [13:32](https://quran.com/13/32?reciter=161) | 13:46.65 | 13:46.99 | +343 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=825.15,828.49) |
| [13:33](https://quran.com/13/33?reciter=161) | 14:29.26 | 14:29.71 | +450 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=867.76,871.21) |
| [13:39](https://quran.com/13/39?reciter=161) | 16:39.04 | 16:38.86 | -177 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=997.36,1000.54) |
| [13:41](https://quran.com/13/41?reciter=161) | 17:12.50 | 17:12.29 | -210 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=1030.79,1034.00) |
| [13:42](https://quran.com/13/42?reciter=161) | 17:30.99 | 17:30.68 | -307 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/13.mp3#t=1049.18,1052.49) |


### Surah 14 — Ibrahim (12 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [14:2](https://quran.com/14/2?reciter=161) | 0:35.63 | 0:35.40 | -230 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=33.90,37.13) |
| [14:8](https://quran.com/14/8?reciter=161) | 3:36.79 | 3:36.23 | -556 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=214.73,218.29) |
| [14:14](https://quran.com/14/14?reciter=161) | 5:58.65 | 5:57.45 | -1201 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=355.95,360.15) |
| [14:18](https://quran.com/14/18?reciter=161) | 7:11.39 | 7:12.85 | +1456 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=429.89,434.35) |
| [14:20](https://quran.com/14/20?reciter=161) | 7:59.79 | 7:59.62 | -167 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=478.12,481.29) |
| [14:23](https://quran.com/14/23?reciter=161) | 9:32.09 | 9:31.46 | -630 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=569.96,573.59) |
| [14:27](https://quran.com/14/27?reciter=161) | 10:34.33 | 10:33.38 | -950 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=631.88,635.83) |
| [14:34](https://quran.com/14/34?reciter=161) | 12:33.36 | 12:34.59 | +1231 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=751.86,756.09) |
| [14:42](https://quran.com/14/42?reciter=161) | 14:58.63 | 14:59.93 | +1303 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=897.13,901.43) |
| [14:43](https://quran.com/14/43?reciter=161) | 15:33.48 | 15:33.66 | +184 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=931.98,935.16) |
| [14:45](https://quran.com/14/45?reciter=161) | 16:04.17 | 16:02.94 | -1231 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=961.44,965.67) |
| [14:47](https://quran.com/14/47?reciter=161) | 16:30.63 | 16:30.93 | +305 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/14.mp3#t=989.13,992.43) |


### Surah 17 — Al-Isra (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [17:110](https://quran.com/17/110?reciter=161) | 30:19.90 | 30:20.21 | +311 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/17.mp3#t=1818.40,1821.71) |


### Surah 19 — Maryam (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [19:97](https://quran.com/19/97?reciter=161) | 18:43.74 | 18:44.11 | +374 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/19.mp3#t=1122.24,1125.61) |


### Surah 24 — An-Nur (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [24:6](https://quran.com/24/6?reciter=161) | 2:25.08 | 2:25.37 | +290 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/24.mp3#t=143.58,146.87) |


### Surah 33 — Al-Ahzab (2 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [33:15](https://quran.com/33/15?reciter=161) | 5:20.31 | 5:20.03 | -280 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/33.mp3#t=318.53,321.81) |
| [33:64](https://quran.com/33/64?reciter=161) | 24:52.28 | 24:52.53 | +250 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/33.mp3#t=1490.78,1494.03) |


### Surah 38 — Sad (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [38:39](https://quran.com/38/39?reciter=161) | 8:28.67 | 8:29.03 | +364 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/38.mp3#t=507.17,510.53) |


### Surah 41 — Fussilat (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [41:10](https://quran.com/41/10?reciter=161) | 2:42.78 | 2:43.01 | +230 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/41.mp3#t=161.28,164.51) |


### Surah 43 — Az-Zukhruf (4 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [43:53](https://quran.com/43/53?reciter=161) | 12:11.56 | 12:11.72 | +164 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/43.mp3#t=730.06,733.22) |
| [43:54](https://quran.com/43/54?reciter=161) | 12:23.60 | 12:23.93 | +330 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/43.mp3#t=742.10,745.43) |
| [43:61](https://quran.com/43/61?reciter=161) | 13:48.99 | 13:49.24 | +250 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/43.mp3#t=827.49,830.74) |
| [43:69](https://quran.com/43/69?reciter=161) | 15:28.25 | 15:28.48 | +230 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/43.mp3#t=926.75,929.98) |


### Surah 44 — Ad-Dukhan (3 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [44:21](https://quran.com/44/21?reciter=161) | 3:18.32 | 3:18.63 | +314 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/44.mp3#t=196.82,200.13) |
| [44:28](https://quran.com/44/28?reciter=161) | 4:16.40 | 4:16.74 | +344 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/44.mp3#t=254.90,258.24) |
| [44:35](https://quran.com/44/35?reciter=161) | 5:27.75 | 5:27.94 | +188 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/44.mp3#t=326.25,329.44) |


### Surah 52 — At-Tur (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [52:39](https://quran.com/52/39?reciter=161) | 5:27.16 | 5:27.37 | +211 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/52.mp3#t=325.66,328.87) |


### Surah 53 — An-Najm (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [53:14](https://quran.com/53/14?reciter=161) | 1:02.95 | 1:03.22 | +267 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/53.mp3#t=61.45,64.72) |


### Surah 55 — Ar-Rahman (7 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [55:14](https://quran.com/55/14?reciter=161) | 1:26.04 | 1:26.31 | +275 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=84.54,87.81) |
| [55:32](https://quran.com/55/32?reciter=161) | 3:47.87 | 3:48.20 | +331 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=226.37,229.70) |
| [55:38](https://quran.com/55/38?reciter=161) | 4:57.96 | 4:58.26 | +296 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=296.46,299.76) |
| [55:42](https://quran.com/55/42?reciter=161) | 5:40.18 | 5:40.42 | +236 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=338.68,341.92) |
| [55:60](https://quran.com/55/60?reciter=161) | 8:15.67 | 8:15.94 | +275 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=494.17,497.44) |
| [55:61](https://quran.com/55/61?reciter=161) | 8:24.45 | 8:24.65 | +200 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=502.95,506.15) |
| [55:68](https://quran.com/55/68?reciter=161) | 9:20.46 | 9:20.62 | +163 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/55.mp3#t=558.96,562.12) |


### Surah 68 — Al-Qalam (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [68:21](https://quran.com/68/21?reciter=161) | 2:34.81 | 2:35.09 | +276 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/68.mp3#t=153.31,156.59) |


### Surah 72 — Al-Jinn (5 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [72:12](https://quran.com/72/12?reciter=161) | 2:19.82 | 2:19.50 | -318 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/72.mp3#t=138.00,141.32) |
| [72:13](https://quran.com/72/13?reciter=161) | 2:37.22 | 2:36.80 | -420 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/72.mp3#t=155.30,158.72) |
| [72:14](https://quran.com/72/14?reciter=161) | 2:53.00 | 2:52.39 | -610 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/72.mp3#t=170.89,174.50) |
| [72:15](https://quran.com/72/15?reciter=161) | 3:00.26 | 2:59.63 | -625 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/72.mp3#t=178.13,181.76) |
| [72:17](https://quran.com/72/17?reciter=161) | 3:23.54 | 3:22.59 | -949 | LATE | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/72.mp3#t=201.09,205.04) |


### Surah 75 — Al-Qiyamah (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [75:8](https://quran.com/75/8?reciter=161) | 0:42.54 | 0:42.77 | +226 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/75.mp3#t=41.04,44.27) |


### Surah 79 — An-Nazi'at (5 drifted boundaryies)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [79:1](https://quran.com/79/1?reciter=161) | 0:04.08 | 0:04.41 | +333 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/79.mp3#t=2.58,5.91) |
| [79:17](https://quran.com/79/17?reciter=161) | 1:16.10 | 1:16.33 | +228 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/79.mp3#t=74.60,77.83) |
| [79:29](https://quran.com/79/29?reciter=161) | 2:16.05 | 2:16.27 | +223 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/79.mp3#t=134.55,137.77) |
| [79:41](https://quran.com/79/41?reciter=161) | 3:22.11 | 3:22.27 | +161 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/79.mp3#t=200.61,203.77) |
| [79:43](https://quran.com/79/43?reciter=161) | 3:33.16 | 3:33.35 | +192 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/79.mp3#t=211.66,214.85) |


### Surah 89 — Al-Fajr (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [89:7](https://quran.com/89/7?reciter=161) | 0:24.73 | 0:25.01 | +276 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/89.mp3#t=23.23,26.51) |


### Surah 91 — Ash-Shams (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [91:4](https://quran.com/91/4?reciter=161) | 0:15.20 | 0:15.60 | +404 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/91.mp3#t=13.70,17.10) |


### Surah 111 — Al-Masad (1 drifted boundary)

| verse-end | old `to` | new `to` | Δ ms | direction | listen |
|----------:|---------:|---------:|-----:|:----------|:-------|
| [111:2](https://quran.com/111/2?reciter=161) | 0:12.72 | 0:12.96 | +235 | EARLY | [🔊](https://download.quranicaudio.com/qdc/khalifah_taniji/murattal/111.mp3#t=11.22,14.46) |


## Method

Every claim above can be reproduced from this repository:

```bash
python analyze_tunaiji.py            # end-to-end pipeline
python experiments/build_tunaiji_analysis.py  # rebuild this report
```

Confidence basis (see `experiments/AB_RESULTS.md` for the A/B sweep that compared three Whisper variants):

- **Recall** (large-v3 baseline on the AB ground-truth set): 73 %
- **Precision**: 92 % (one false positive at threshold 0.70 across the AB set)
- **Cross-check**: a Quran-fine-tuned Whisper variant (`tarteel-ai/whisper-base-ar-quran`) hit 100 % precision on the same AB set, raising the *avg* best-match similarity on true shifts from 0.81 → 0.85. Re-running the verify step on Tunaiji with that model would tighten precision further; the shifts reported here are conservative.

## Filing path

The data lives in QUL (`Audio::Segment` records keyed by recitation id 161). Either route:

- File a GitHub issue at <https://github.com/TarteelAI/quranic-universal-library/issues> with the per-surah `data/corrected_v2/surah_<N>_qul.csv` and a screen-recording of the demo player from `build_demo.py`.
- Or click *Send Access Request* at <https://qul.tarteel.ai/tools> for the *Audio Segments* resource and edit directly.

_Generated by `experiments/build_tunaiji_analysis.py`._
