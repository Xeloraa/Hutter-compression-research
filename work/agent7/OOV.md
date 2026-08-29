# OOV copy oracles

## E38 — raw 3 MB prefix (letters, before DIC)

- raw_bytes=3000000 alpha_tokens=427892 dic_words=44515
- oov_tokens=39447 oov_repeats=27008 copy_wins=15578
- spell_bits=1408920 mix_bits=1039482 save=369438 (1.539% of raw file bits vs 8-bit spelling)
- 3-byte preceding prefix match on repeats: 8544 / 27008 (31.6%)

That 3-byte test **overstated** MatchModel2 overlap. Shortest MatchModel2 hash is **LEN1=5** (`fxcm26_slots.cpp`).

## E38b — DIC stream (what fxcm actually sees)

Residual OOV = maximal `a-z` runs in `enwik8.3m.dic` whose exact string is not an `english.dic` word (substring leftovers stay OOV).

- dic_bytes=1814514 residual_letter_bytes=136891 (7.54% of DIC file)
- oov_runs=33393 oov_repeats=22267 copy_wins=13754
- copy vs 8-bit: save 267180 bits = **1.841% of DIC-file bits** (33398 bytes-equivalent). Not an archive size.

MatchModel2 prefix overlap on OOV repeats:

| L | last-occ | any prior occ |
|---:|---:|---:|
| 3 | 39.7% | 61.4% |
| **5** | **27.2%** | **47.4%** |
| 7 | 12.3% | 30.1% |
| 9 | 8.4% | 22.5% |

LEN=5 any-prior is **47.4%, not 80%**. Kill-by-match-overlap fails.

Order-3 KT on residual letters with full-stream context: **6.162 bpb**. These are not cheap English n-grams.

## Leftover after MatchModel2-faithful overlap, by run length

`DIC_OOV_LEFTOVER.md`

After dropping repeats that have **any prior** LEN=5 prefix match:

| band | n | save vs 8-bit | % DIC-file |
|---|---:|---:|---:|
| len 1-2 (DIC crumbs) | 6976 | 20726 | 0.143 |
| len 3-5 | 2911 | 46278 | 0.319 |
| **len >=6** | **1828** | **100564** | **0.693** (~12.6 KB equivalent) |

len 1-2 is not a name expert (8–16 bit spellings). **len>=6 unmatched by LEN=5** is the identity residual: ~12.6 KB ceiling vs spelling, after the match-overlap that actually exists.

Still not a pipeline result. fxcm CMs + LSTM already spend bits on those letters. A mixer OOV-index is justified only after E30/E35, as one axis, on **len>=6** tokens, not all letter-runs.

## Verdict

- lastCW gamma/LRU: **killed** (`IDENTITY.md`).
- raw OOV vs 3-byte match: **misleading evaluation** (wrong match length).
- DIC OOV len>=6 vs LEN=5: **survives as a ceiling**. Do not wire 3 MB yet. Next implementation sketch: causal map of recent OOV strings of length>=6, mixer expert only on those bytes, zero shipped data.
