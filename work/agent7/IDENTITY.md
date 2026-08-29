# Idea 1 identity cache — lastCW oracles on 3 MB DIC

391,028 in-dict tokens (44,515 vocab). 20,946 first occurrences; 370,082 repeats.

## Kill: unbounded gamma(gap) pointer

Always-pointer (escape+gamma(gap) or uniform id) **loses 2.16 Mbits** to a unigram. Forced recency cache at any K also loses. gamma(large gap) is worse than frequency.

## Mixed oracle min(unigram, 1+gamma(gap))

Saves **305,486 bits (7.41%)** vs unigram, **75,262** pointer wins.

| bucket | n | mix save vs uni |
|---|---:|---:|
| hapax | 6,621 | 0 |
| count 2–5 | 22,977 | 27,920 |
| count 6–20 | 44,732 | 58,696 |
| count >20 | 316,698 | **218,871** |

**72% of the mixed saving is frequent words (count>20)** — the same mass fxcm word streams already price.

Rare and **gap>256**: **zero** mixed gamma wins.

## Recode: LRU membership, cost 1+log2(|cache|) — also killed

The gamma kill could have been a **coding** failure: 1+gamma(gap) is ~2 log2(gap) and loses at gap>256 vs a ~16–18 bit unigram, even if the id is still in a recent set.

`work/agent7/rare_lru_oracle.py` (`RARE_LRU.md`): LRU of last K distinct ids, hit cost **1+log2(K)** (independent of file distance).

| cache | save vs uni | of which cnt>20 | cnt2-5 | far-rare hits (gap>256, count<=5) |
|---|---:|---:|---:|---:|
| all-id K=64 | 412,480 (2.84% DIC-file) | **306,880** | 30,663 | 4 / 11,489 |
| all-id K=256 | 342,898 | 225,115 | 34,196 | 596 / 11,489 |
| rare-only K=256 (causal count<=5) | 120,316 (0.83% DIC-file) | 20,077 | **44,125** | 1,873 / 11,489 |

Save **falls** as K grows because 1+log2(K) gets more expensive (K=64 is 7 bits; K=65536 is 17 bits ≈ rare unigram). The large K=64 number is still **frequent words** (worcxt). Rare-only cnt2-5 is **44 kbit ≈ 0.30% of DIC-file bits ≈ 0.18% of raw 3 MB file bits**, below the original 0.4% of file-bits kill.

far-rare: at K=64 almost none are still in cache; at huge K they are in cache but the index is as expensive as the unigram.

## Verdict

Do **not** spend a 3 MB pipeline on a lastCW recency cache, gamma **or** LRU-index. The hypothesis is wrong as a large independent lever, not merely mis-coded. Frequent-word overlap with `worcxt` is the mass; rare distant ids are not a cheap pointer residual vs frequency.

**Live identity leftover is OOV letter-runs of length >=6 after DIC**, not lastCW (see `DIC_OOV.md` / `DIC_OOV_LEFTOVER.md`).
