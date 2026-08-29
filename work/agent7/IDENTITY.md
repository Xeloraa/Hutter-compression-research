# Idea 1 identity cache — oracle on 3 MB DIC lastCW stream

391,028 in-dict tokens (44,515 vocab). 20,946 first occurrences; 370,082 repeats.

## Kill: unbounded γ(gap) pointer

Always-pointer (escape+γ(gap) or uniform id) **loses 2.16 Mbits** to a unigram. Forced recency cache at any K also loses. γ(large gap) is worse than frequency.

## Mixed oracle min(unigram, 1+γ(gap))

Saves **305,486 bits (7.41%)** vs unigram, **75,262** pointer wins.

| bucket | n | mix save vs uni |
|---|---:|---:|
| hapax | 6,621 | 0 |
| count 2–5 | 22,977 | 27,920 |
| count 6–20 | 44,732 | 58,696 |
| count >20 | 316,698 | **218,871** |

**72% of the mixed saving is frequent words (count>20)** — the same mass fxcm word streams already price. That is not a new identity expert; it is a worse coding of what `worcxt` does.

Rare and **gap>256**: **zero** mixed wins. For those tokens 1+γ(gap) is never cheaper than the unigram (~16–18 bits). Distant rare ids are **not** a γ-pointer residual vs frequency.

## Verdict

Do **not** spend a 3 MB pipeline on a γ-gap cache. Idea 1 as specified is falsified as a large independent lever.

Leftover (not run): a **log₂|recent-set|** code for *rare* ids only (not γ of file position), compared to fxcm’s existing word hashes — still likely E19-class. Park until E30/E35 report.
