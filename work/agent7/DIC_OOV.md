# DIC-stream OOV copy oracle

Pipeline input: `data/enwik8.3m.dic`. Residual OOV = maximal `a-z` runs whose exact string is **not** an `english.dic` word (substring leftovers stay OOV).

MatchModel2 (`fxcm26_slots.cpp`): shortest candidate hash is **LEN1=5**, then 7 and 9. The raw-text E38 test used a 3-byte prefix and **overstated** match overlap.

## Stream
- dic_bytes=1814514 residual_letter_bytes=136891 (7.54% of DIC file)
- letter_runs=34177 exact_dic_word_runs=784 oov_runs=33393 oov_repeats=22267
- oov_types=11126 in_dic_run_types=267

## Copy vs 8-bit spelling of residual OOV runs
- spell_bits=1072624 mix_gamma_bits=805444 save=267180
- save vs DIC-file bits: 1.841% (33398 bytes-equivalent)
- save vs raw 3MB bits: 1.113%
- copy_wins=13754 save_on_wins=267180
- gap_tokens median=25 mean=795.2 p90=1331
- gap_bytes median=1157 mean=41962.7 p90=70760
- length histogram (run bytes, top): 2:10366, 1:5534, 3:3959, 6:2235, 7:2159, 5:2136, 4:1953, 8:1698, 9:1263, 10:835, 11:515, 12:299

## MatchModel2 prefix overlap on OOV repeats
| L | last-occ prefix | any prior occ prefix |
|---:|---:|---:|
| 3 | 8843/22267 (39.7%) | 13683/22267 (61.4%) |
| 5 | 6048/22267 (27.2%) | 10552/22267 (47.4%) |
| 7 | 2729/22267 (12.3%) | 6692/22267 (30.1%) |
| 9 | 1865/22267 (8.4%) | 5011/22267 (22.5%) |

LEN=3 is **not** a MatchModel2 candidate length. LEN=5 is the honest kill test.

## Leftover after removing last-occ LEN=5 matches
- unmatched_repeats=16219 leftover_spell=354152 leftover_mix=147476 leftover_save=206676 wins=10258
- leftover save vs DIC-file bits: 1.424%

## Modified coding: LRU rank (γ(rank)), not γ(file-gap)
- LRU K=64 bits=827092 save=245532 (1.691% DIC-file) hits=13939 wins_vs_spell=12394
- LRU K=256 bits=807574 save=265050 (1.826% DIC-file) hits=18110 wins_vs_spell=13860
- LRU K=1024 bits=802464 save=270160 (1.861% DIC-file) hits=20696 wins_vs_spell=14286
- LRU K=4096 bits=798966 save=273658 (1.885% DIC-file) hits=21849 wins_vs_spell=14659

## Order-3 KT on residual letter bytes (full-stream context)
- ppm3_bits=843472 on 136891 residual letters (6.162 bpb)
- vs 8-bit: save 251656 bits (1.734% DIC-file)
- pointer-gamma vs ppm3 (not a joint code): mix_gamma=805444 vs ppm3=843472 (ppm scores ALL residual letters including first occurrences)
- 8-bit all residual OOV letters=1072624; PPM is a tighter *baseline for spelling*, not for identity pointers.

## Verdict gate
Kill if leftover after LEN=5 last-occ match is <0.15% of DIC-file bits, or if LEN=5 any-prior overlap ≥80%.
Survive (ceiling only) if leftover is large **and** LEN=5 overlap stays well below 80%. Still not a pipeline result: CMs also model letter n-grams; PPM4 is that check.
