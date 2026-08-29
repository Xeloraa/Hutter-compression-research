# O2 first-template byte-mass gate (enwik8.3m, no fxcm)

pages=384 page_text_bytes=2828254
repeating DF>=2 templates=27 bytes on those pages=1714331 (57.14% of file)

## Split: schema vs hatnote (the 60% figure is not Taxobox)
- schema infobox/taxobox/coor repeating-class pages: 405110 (13.50% of file)
- hatnote otheruses/spoiler/wiktionary/... repeating-class pages: 914882 (30.50% of file)
- other repeating first-templates: 394339 (13.14% of file)

Grouping on first-template **including hatnotes** clumps unrelated articles that happen to start with {{otheruses}}. That is not schema locality.
Modified O2: key = first infobox/taxobox/coor template, else empty, original index. Inverse still free via <id>.
Kill unmodified O2 as a codec run. Keep schema-only O2 as the leftover ordering experiment (still no 3MB fxcm until 10MB).

| template | kind | DF | page-text bytes | % of file |
|---|---|---:|---:|---:|
| `otheruses` | hatnote | 11 | 283661 | 9.46 |
| `taxobox` | schema | 9 | 69230 | 2.31 |
| `disambig` | other | 7 | 16020 | 0.53 |
| `imdb name` | other | 4 | 25827 | 0.86 |
| `spoiler` | hatnote | 4 | 89531 | 2.98 |
| `coor dm` | schema | 4 | 107619 | 3.59 |
| `r from camelcase` | hatnote | 3 | 131 | 0.00 |
| `otheruses1` | hatnote | 3 | 64328 | 2.14 |
| `wiktionary` | hatnote | 3 | 19038 | 0.63 |
| `featured article` | hatnote | 3 | 125415 | 4.18 |
| `infobox_country` | schema | 3 | 114011 | 3.80 |
| `mergefrom` | other | 3 | 92839 | 3.09 |
| `wikiquote` | hatnote | 3 | 47037 | 1.57 |
| `redirect` | hatnote | 3 | 152100 | 5.07 |
| `infobox_philosopher` | schema | 2 | 72069 | 2.40 |
| `sect-stub` | other | 2 | 49026 | 1.63 |
| `protected` | other | 2 | 67219 | 2.24 |
| `wiktionarypar` | hatnote | 2 | 4085 | 0.14 |
| `for` | hatnote | 2 | 19995 | 0.67 |
| `compu-stub` | other | 2 | 1091 | 0.04 |
