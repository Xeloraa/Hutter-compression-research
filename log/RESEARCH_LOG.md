# Hutter Prize — Research Log

Rules snapshot (verified 25 Aug 2026): S = len(comp9) + len(archive9).
Each program < 70,000/T hours CPU (T = judging machine Geekbench5; recent
judging used T=1648 → **42.48 h**), < 10 GB RAM, < 100 GB disk, 1 core, no GPU.
Published record: fx2-cmix 110,793,128. cmix-lex 109,671,639 pending.
Three further entries under adjudication → real target likely ≲ 106.5 MB.

Dev corpus: **enwik8, MD5 `a1fa5ffddb56f4953e226637dabbb36a` — matches the
official published checksum.** Slices enwik5/6/7/75 are exact prefixes.

Environment for these runs: 1 core Xeon @2.1 GHz, 3 GB RAM. Absolute sizes are
from `cm`, a mid-tier CM testbed at ~1.86 bpb, **not** a contender. All
*relative* conclusions are what transfer; every one must be re-measured against
fx2-cmix before being believed.

---

## E0 — Baseline testbed

**Implementation.** `src/cm.cpp`: 8 hashed context models (o1–o8 + 2 word
models) + verified match model → logistic mixer (2048 weight sets) → 2-stage
APM/SSE → binary arithmetic coder. Per-byte code length instrumentation
(`-cost`). Roundtrip verified byte-exact at 100 KB / 1 MB / 10 MB.

| corpus | archive | bpb | c-time | d-time | RSS | verified |
|---|---|---|---|---|---|---|
| enwik7 (10 MB, -mem 24) | 2,319,471 | 1.8556 | 28.6 s | 27.9 s | 536 MB | yes |
| enwik7 xz -9e | 2,720,256 | 2.1762 | — | — | — | — |
| enwik7 bzip2 -9 | 2,916,026 | 2.3328 | — | — | — | — |

Calibration: at this speed enwik9 would take ≈0.8 h. fx2-cmix uses ≈40 h.
**The testbed is ~50× under-spending the legal compute budget** — that factor is
where all real modelling capacity lives.

---

## E1 — Bit-attribution profile (enwik7, mem 24; gain% = mem 19→24)

| category | %file | %bits | bpb | gain% |
|---|---|---|---|---|
| T_PROSE | 46.7 | **51.0** | 2.027 | 6.9 |
| T_LINK | 18.6 | **19.9** | 1.980 | 8.8 |
| T_PUNCT | 2.6 | 5.1 | 3.595 | 4.4 |
| T_SPACE | 11.2 | 4.6 | 0.753 | 9.6 |
| T_TEMPLATE | 3.4 | 3.6 | 1.987 | 7.4 |
| T_URL | 2.4 | 3.1 | 2.374 | 7.0 |
| … | | | | |
| XML_STRUCT | 3.8 | 0.5 | 0.266 | 12.6 |

**Findings.**
1. **PROSE + LINK = 70.9 % of all bits.** Everything else is rounding error.
2. **All XML/structural markup is already almost free** (0.266 bpb). "Exploit
   Wikipedia's structure" is a spent lever.
3. **Cost is diffuse, not concentrated**: top 1 % of bytes hold 5.9 % of bits;
   top 10 % hold 37.4 %; top 25 % hold 70 %. → **Kills every
   "special-case the hard regions" strategy.** There is no hot spot.
4. Link content costs the same per byte as free prose (1.98 vs 2.03) despite
   being drawn from a title-like vocabulary → looked exploitable. See E2.

---

## E2 — H1: dedicated closed-vocabulary model for wiki-link targets — **KILLED**

**Hypothesis.** Link targets repeat; a token model over a shipped title
vocabulary should beat coding them as text.

**Measurement** (not a prototype — an information budget):

| scale | links | distinct | repeat | H0 | vocab spell-out | token total | bits/target byte |
|---|---|---|---|---|---|---|---|
| 1 MB | 8,945 | 6,804 | 1.31× | 0.11 Mb | 0.35 Mb | 0.46 Mb | 3.470 |
| 10 MB | 110,336 | 66,347 | 1.66× | 1.68 Mb | 3.15 Mb | 4.83 Mb | 3.276 |
| 30 MB | 294,438 | 156,049 | 1.89× | 4.76 Mb | 7.51 Mb | 12.27 Mb | 3.027 |
| 100 MB | 940,759 | 403,548 | 2.33× | 16.03 Mb | 19.54 Mb | 35.56 Mb | 2.691 |

CM already spends **3.69 Mbits** on those bytes at 10 MB vs the token model's
**4.83 Mbits**. The vocabulary is *open*: 81 % of distinct targets occur once.
The dictionary costs more than it saves at every scale, and bits/target-byte
falls only ~0.26 per 10× — far too slow to ever cross.

**Conclusion: dead at all scales.** Textbook "moved information from archive to
model". Generalises: closed-vocabulary schemes lose on enwik9 because the CM
already spells novel strings using statistics shared with surrounding prose.

---

## E3 — H2: article ordering, and the cost of shipping a permutation

**Precondition verified:** `<page>` ids are **strictly ascending** in original
order — 1,325/1,325 on enwik7 and 12,347/12,347 on enwik8. Therefore a decoder
that emits pages in *any* order can restore the original file by sorting on the
in-band `<id>`. **The inverse permutation is free.**

**enwik7, 1,325 pages, mem 24**

| order | archive | vs orig | permutation to ship |
|---|---|---|---|
| original | 2,319,465 | — | 0 |
| random | 2,331,719 | −0.53 % | — |
| **title (lexicographic)** | **2,308,355** | **+0.479 %** | **0** |
| title-reversed | 2,313,309 | +0.26 % | 0 |
| greedy minhash content | 2,312,077 | +0.319 % | 2,168 B (xz) |

**enwik75, 3,937 pages, mem 22 (higher memory pressure)**

| order | archive | vs orig |
|---|---|---|
| original | 6,888,487 | — |
| **title** | **6,843,522** | **+0.653 %** |
| TITLECAST (titles hoisted + bodies) | 6,847,272 | +0.598 % |

**Findings.**
1. A **free** title-lexicographic order beat a **paid** content order.
2. The gain **grows with scale/pressure**: +0.479 % → +0.653 %. Consistent with
   STARLIT's ~1.4 % at 243 k pages / 10 GB.
3. Hoisting titles into a separate stream *lost* 3,750 B — because the
   implemented variant paid the restructuring cost without the compensating
   gain (title-as-injected-context was not implemented). Incomplete, not
   disproven; re-test properly.

**What current entries pay.** STARLIT's shipped `new_article_order`:
173,361 entries, 1,131,233 B raw; **215,748 B delta+xz**; an arbitrary
permutation of that many items has a 345.9 KB entropy floor. Against
S ≈ 109.7 MB that is **0.14–0.26 % of the total submission, paid permanently**.
The file shows long runs of consecutive original ids — STARLIT's order is
largely block-preserving, so its marginal information over a good deterministic
order is smaller than its size suggests.

**Status: live, highest-confidence lever so far.** Value = eliminate ~150–215 KB
of permanent payload, *provided* a derived order is not materially worse than
Doc2Vec+TSP at 1 GB. Zero CPU, zero RAM, zero risk to the rest of the model.

---

## Kill list

- Closed-vocabulary link/title token model (E2) — loses at all scales.
- Special-casing expensive regions (E1.3) — cost is diffuse, no hot spot exists.
- Structural/XML modelling (E1.2) — already at 0.266 bpb, nothing left.

## Open queue (ranked by expected value ÷ effort)

1. **DERIVED-ORDER.** Formalise: encode pages sorted by a deterministic
   title-derived key, restore by `<id>` sort. Measure against STARLIT's actual
   order using fx2-cmix as the codec. Target: −150…215 KB with ordering quality
   ≥ STARLIT.
2. **ORDER-AS-PRIOR + correction.** If the derived order is worse than the
   optimal one, ship only the *deviation* from it, not the whole permutation.
   Cost scales with disagreement, not with n log n.
3. **TITLECAST done properly** — hoist titles, inject the title as a permanent
   context for its body. Decoder has it; costs zero side information.
4. Retrieval/kNN expert over previous contexts (untested).
5. Re-run E1 profile against fx2-cmix, not the testbed — everything above is
   ranked on a 1.86 bpb model and must be re-ranked on a 0.87 bpb one.

---

## E4 — H3: document-level context (title / heading / topic) — **superseded by E5**

**Hypothesis.** If grouping pages by title helps (E3), the title itself should be
a predictor. Add contexts scoped to the whole article, parsed causally from
already-decoded bytes → zero side data.

**Implementation.** `cm.cpp` NCTX 8→12. Causal `<title>` tracker (byte-matching
on the rolling 8-byte window), `\n==` heading tracker, and a 16-word page-topic
sketch. Contexts `H(titleHash, lastbyte)`, `H(titleHash, word)`,
`H(headHash, word)`, `H(topicHash, word)`.

**enwik7, mem 24** — every run roundtrip-verified byte-exact.

| variant | archive | vs base |
|---|---|---|
| baseline, 8 models | 2,319,471 | — |
| **CONTROL: 10 models, re-salted duplicates, no new information** | 2,318,575 | **0.039 %** |
| + title | 2,295,655 | 1.027 % |
| + title + heading | 2,293,730 | 1.110 % |
| + title + heading + topic | 2,290,275 | 1.259 % |

The control is the load-bearing row: extra model count and mixer capacity alone
buy 0.039 %, so **0.988 % is attributable to the title information itself**.

**Novelty check.** Pulled `kaitz/fxcm` (5,855 lines — the model inside the
pending record cmix-lex). No `<title>`, page, or document-scope context exists.
Its longest-lived text context is `firstWord`, **reset at every paragraph**
(lines 4199, 4489).

**THEN IT FAILED THE REGIME TEST.** RAM-fair gain, interpolating baseline onto
the same RSS:

| v4 RSS | data/RAM | RAM-fair gain |
|---|---|---|
| 101 MB | 0.099 | **−0.377 %** |
| 201 MB | 0.050 | +0.110 % |
| 403 MB | 0.025 | +0.618 % |
| 805 MB | 0.012 | +1.011 % |
| 1611 MB | 0.006 | +1.169 % |

enwik9 in a 10 GB cap has data/RAM = 0.100. **The headline +1.259 % was measured
8× less saturated than the target regime; at the real regime it is a loss.**

**Diagnosis.** `(title × word)` contexts are *single-use* — dead the moment the
article ends. They churn the hash table and evict long-lived contexts. The
information was right; the data structure was wrong.

---

## E5 — H3b: page-local models with bounded cardinality — **LIVE, best result**

**Implementation.** Keep 8 global models unchanged. Add 2 page-local counter
models on a **fixed 2 MB table** (2 × 2^17 slots × 8 B) with O(1) reset by
generation stamp, incremented on the causal `<page>` token. Keys: partial-word
hash, and prev-word+partial-word. Cardinality is bounded by one article, not by
|titles| × |words|.

**enwik7, all roundtrip-verified byte-exact**

| mem | data/RAM | baseline | v4 doc-ctx | **v5 page-local** | v5 gain | v4 gain |
|---|---|---|---|---|---|---|
| 21 | 0.149 | 2,391,360 | 2,381,433 | **2,360,705** | **+1.282 %** | +0.415 % |
| 22 | 0.075 | 2,359,093 | 2,342,479 | **2,330,589** | +1.208 % | +0.704 % |
| 23 | 0.037 | 2,335,097 | 2,311,578 | **2,308,003** | +1.160 % | +1.007 % |
| 24 | 0.019 | 2,319,471 | **2,290,275** | 2,293,058 | +1.139 % | +1.259 % |

v5's gain is flat-to-rising as saturation increases and is **largest at the
enwik9 regime** — exactly inverted from v4. v4 wins only at mem 24, the least
realistic point.

**Cost:** +2 MB fixed RAM (0.02 % of the 10 GB cap), +6 % CPU (23.4 s vs 22 s),
zero shipped bytes. RAM-fair gain at mem 21 ≈ **+1.23 %**.

**Scale check (30 MB, mem 22):** baseline 6,888,517 → v5 6,780,226 = **+1.572 %**,
*larger* than the +1.208 % at 10 MB with the same 2 MB table. The gain grows with
data volume because the global tables saturate while the page-local table cannot.

**Composition with free ordering (30 MB, mem 22):**

| | orig order | free order | ordering gain |
|---|---|---|---|
| baseline | 6,888,517 | 6,840,194 | +0.702 % |
| v5 page-local | 6,780,226 | **6,751,643** | +0.422 % |

**Combined +1.987 % (136,874 B)** vs sum-if-independent 2.274 % → overlap 0.287 %.
87 % additive.

## Current stack (all zero shipped bytes, all byte-exact verified)

1. free page ordering by `redir_title`, inverse by in-band `<id>` — +0.70 %
2. page-local bounded models — +1.57 % at 30 MB and rising with scale
3. combined **+1.99 %**, plus deletion of STARLIT's 215,748 B permutation

## Kill list (updated)

- Closed-vocabulary link/title token model (E2).
- Special-casing expensive regions (E1.3) — cost is diffuse.
- Structural/XML modelling (E1.2) — already 0.266 bpb.
- Length-bucketed ordering (E3) — actively harmful, −0.216 %.
- **Unbounded (title × word) global contexts (E4) — negative at target regime.**

## Next

1. Port the 2 page-local models into `fxcm.cpp` and measure marginal gain on the
   real model. fxcm has paragraph-scope `firstWord`; expect materially less than
   1.5 %. This is the decisive experiment. Needs ~10 GB and days of wall time.
2. Sweep page-table size (2^15…2^20) and the page-reset token under WIT preproc.
3. Re-run the E1 profile with v5 to see which categories it actually fixed.

---

## E6 — page-table size sweep (enwik7, mem 21)

| page tbl | RAM | archive | gain | marginal | 
|---|---|---|---|---|
| 2^15 | 0.52 MB | 2,370,659 | 0.866 % | — |
| 2^17 | 2.10 MB | 2,360,705 | 1.282 % | +0.184 % |
| 2^19 | 8.39 MB | 2,355,969 | 1.480 % | +0.078 % |
| 2^20 | 16.8 MB | 2,354,822 | 1.528 % | +0.048 % |
| 2^21 | 33.6 MB | 2,354,246 | 1.552 % | +0.024 % |

Plateau at 2^19–2^20, matching the predicted count of distinct in-page contexts.
**RAM efficiency:** 8.4 MB on the page table buys 1.480 %; the same 8.4 MB spent
enlarging the 8 global models buys 0.230 % — **6× more efficient**.

## E7 — fxcm built and running locally

`kaitz/fxcm` v25 (PLAINTEXT) builds on Linux after 4 patches: comment out
`<mem.h>` and `<windows.h>`, add `<stdint.h>/<string.h>/<stdlib.h>`, `-DUNIX`.
Needs `english.dic` in cwd. Stock build OOMs at 3.7 GB; scaling the 35
`.Init(N*4096*4096,…)` context-map arguments by 1/8 (all stay powers of 2) fits.

**fxcm(/8) on enwik6: 200,467 vs my testbed 255,255** — 21 % stronger, confirming
the testbed is mid-tier and fxcm is the real thing. Speed 68.8 s/MB, so full
enwik7 runs exceed the sandbox limit; fxcm work here is capped at ~1–2 MB.

A true port needs surgery on `mxA[i].Init(ctx, N, s, e)` input ranges — a
multi-hour task, not attempted.

## E8 — overlap with fxcm's paragraph-scope context (proxy for the port)

fxcm's closest analogue to a long-scope word context is `firstWord`, reset at
each paragraph. Simulated it in the testbed to estimate what survives the port.

| variant | archive | vs base |
|---|---|---|
| baseline (8 models) | 2,391,360 | — |
| + fxcm-style paragraph `firstWord` | 2,392,090 | −0.031 % |
| + page-local only | 2,360,705 | +1.282 % |
| + paragraph + page-local | 2,361,237 | +1.260 % |

**Page-local gain on top of paragraph-scope: +1.290 %, vs +1.282 % without it —
zero overlap.** The mechanisms differ: recurrence-counting inside a document vs
conditioning on a paragraph's first word.

*Weak point:* my `firstWord` contributed nothing on its own (−0.031 %), so it is
a poor stand-in for fxcm's real implementation. This estimates the overlap, it
does not measure it.

## E9 — re-profile after page-local (enwik7, mem 21): where the gain landed

Total 19.121 → 18.876 Mbits (+1.283 %).

| category | %bits | base bpb | v5 bpb | gain | Mbits saved |
|---|---|---|---|---|---|
| T_PROSE | 50.95 % | 2.087 | 2.053 | 1.63 % | 0.159 |
| T_LINK | 20.04 % | 2.055 | 2.027 | 1.36 % | 0.052 |
| **T_LINKPIPE** | 2.55 % | 2.098 | 2.018 | **3.82 %** | 0.019 |
| T_TEMPLATE | 3.61 % | 2.051 | 2.025 | 1.27 % | 0.009 |
| T_REDIRECT | 0.07 % | 0.954 | 0.924 | 3.15 % | 0.000 |
| T_ENTITY | 0.94 % | 0.995 | 1.009 | **−1.44 %** | −0.003 |
| T_PUNCT | 5.07 % | 3.667 | 3.673 | −0.17 % | −0.002 |

**Findings.** The gain lands exactly where predicted — on repeated content words
inside a document. Link *anchor text* (`T_LINKPIPE`, the display text after `|`)
improves 3.82 %, the best of any large category: anchor text restates words used
elsewhere in the same article, which is precisely page-local recurrence.

Small regressions in `T_ENTITY`, `T_PUNCT`, `T_SPACE` are mixer dilution — two
extra inputs slightly degrade categories the page models cannot help. That is
the expected cost and it is an order of magnitude smaller than the gain.

**T_DIGIT stays at 4.03 bpb (1.58 % of bits) and T_EMPH/T_PUNCT ~3.7–4.0 bpb and
did not move at all** — untouched by every idea tested so far. Next target.

---
## E10-E14 — REAL REGIME (DIC + fxcm26). All prior results superseded.

**Pipeline reproduced byte-exact.** cmix's own `dictionary.cpp` + `english.dic`
built standalone; fxcm v26 (non-PLAINTEXT), memory scaled 1/8 to fit 4 GB.
`enwik -> DIC -> fxcm26 -> fxcm26^-1 -> DIC^-1` verified **BYTE-EXACT** on 3 MB.
Baseline: 3,000,000 -> 1,814,514 DIC -> **521,198 = 1.3892 bpb**.
(PLAINTEXT was 1.5330; every earlier session measured the wrong pipeline.)

### E10 Ordering — DEAD
testbed +0.479% | fxcm PLAINTEXT +0.075% | **DIC+fxcm26 -0.006%**
(1,672,492 -> 1,672,597 at 10 MB / 1,325 pages). Goes negative as the pipeline
strengthens: DIC's word dictionary already captures cross-article redundancy.

### E11 Real-regime profile (1.3892 bpb)
prose 55.9% @1.688 | links 16.9% @1.395 | templates 5.6% @1.420 |
punct 4.3% @2.492 | digits 1.65% @3.128 | **XML 0.070** (structure exhausted).
DIC stream decomposition: **dict codes >=0x80 are 40% of bytes but 69% of bits
at 3.95 bits each**; escapes near-free (kQuote 0.137, kEscape 0.570).
The residual is word identity, not structure.

### E12 Long-range dependency — DEAD (was a memory artifact risk)
Recency profile looked huge: 20.8% of bits on words last seen >16k tokens ago
@12.5 bits vs 3.75 @distance 64-256; 17.3% on novel words @21.5 bits.
**Control:** halving memory (/8 -> /16) moved the total 0.14% and that bucket
0.20%. Extrapolating 3 further doublings: 12.543 -> 12.469 bits.
Distant-word cost is **intrinsic rarity, not model amnesia.** Memory is not
binding at this scale.

### E13 Anchored word-prefix models — IMPLEMENTED, DEAD
*Novelty check first:* fxcm's `h=word0*271` is ALWAYS combined with neighbouring
word context (`h+worcxt0.Word0(1)`, `h+firstWord*89`, `h+worcxt.Word(2)*83...`);
its char contexts are sliding windows. No context is keyed on the partial word
alone. Offline test: anchoring adds **+6.80%** over sliding order-4
(3.958 -> 3.689 bits/char on novel words).
Implemented 2 anchored-prefix CMs in fxcm26 (mixer slots 544/545, tables 2x16MB;
dictionary codes are >=0x80 so literals are unambiguous).
Tracker verified live: fires on 7.5% of DIC bytes (the literal word chars).

| variant | archive | vs base |
|---|---|---|
| baseline | 521,198 | - |
| anchored-prefix, ungated | 521,208 | -0.002% |
| anchored-prefix, gated when inactive | **521,180** | **+0.003%** |

18 bytes = noise. fxcm's existing contexts already capture anchoring.

### E14 Calibration ceiling — bounds a whole class of ideas
Recorded (p,y) for all 14,516,112 coded bits. **Perfect post-hoc recalibration
(an oracle, causally unachievable) gains only 0.1362%.** Predicted vs observed
agree within ~1% relative in every probability bucket.
=> No final-stage SSE/APM/mixing refinement can be worth more than ~0.14%.
   Improvement requires giving the model NEW INFORMATION.

## Kill list (real regime)
page-local models (+0.015%) | free ordering (-0.006%) | capital transform
(already in DIC: kUppercase/kEndUpper) | long-range memory (not binding) |
anchored word-prefix (+0.003%) | digits (~0.4% optimistic ceiling) |
structure/XML (0.070 bpb) | any recalibration/SSE work (<=0.136% oracle)

---
## E15-E18 — ONLINE LSTM: first VERIFIED improvement in the real regime

**Why this class.** The calibration ceiling (E14) proved better mixing of the same
information is worth <=0.136%. Every context variant tried was redundant. An
online-trained LSTM has a different inductive bias: it is *worse than fxcm alone*
(0.3605 vs 0.2946 bits/bit) yet still adds information. Weights are learned
online => nothing shipped => costs S1 code size only. Legal under Hutter rules.

### E15 Offline (p,y) harness
Recorded (p,y) for all 14,516,112 coded bits; candidate tested by generating p'
offline and training a 2-input logistic mixer against real outcomes. Gains:
LSTM 200c/2L +0.308% (rising with warmth: 0.261% -> 0.422% across 700 KB).
**CAVEAT (measured in E16): the harness UNDERSTATES gain ~6x** because it mixes
with a toy mixer while fxcm has an 18-mixer hierarchy + SSE. Use it only to kill
truly-redundant candidates, never for magnitudes.

### E16 Integration into fxcm26 — VERIFIED BYTE-EXACT
Baseline: DIC + fxcm26 (mem/8), 3 MB slice = **521,198**.

| config | archive | vs base | c-time | d-time | RSS | roundtrip |
|---|---|---|---|---|---|---|
| baseline | 521,198 | - | 161 s | 156 s | ~2.0 GB | EXACT |
| + LSTM 64c/1L | **519,263** | **+0.371%** | 378 s | 378 s | 2.21 GB | **EXACT** |
| + LSTM 128c/1L | **518,320** | **+0.552%** | 616 s | 590 s | 2.21 GB | **EXACT** |

**Scaling:** 10 MB (6,186,034 DIC B): 1,672,492 -> **1,665,907 = +0.394%**
(up from +0.371% at 3 MB). Gain GROWS as the LSTM warms.

**S1 accounting:** stripped+xz compressor 58,736 -> 84,620 B (**+25,884**).
At enwik9 scale 0.371% ~= 406,881 B saved => S1 repaid ~16x. Net positive on S.

### E17 Cost model and budget
`cost(us/byte) = 29.3 + 0.01439*cells^2` (33% fixed overhead; 32c->64c is only
2.0x slower for 4x MACs => overhead-dominated at small sizes).
enwik9 projection (605M DIC bytes; budget 42.48h = 252 us/DIC byte):
- 64c -> 29.6 h **FITS**, +0.394% verified
- 96c -> 42.0 h fits, marginal
- 128c -> 59.3 h **OVER**, +0.552% verified

### E18 Speed optimization attempt — NEGATIVE
Hypothesis: `output_layer_[e][i] = output_layer_[le][i]; ... -= lr*error*hidden_;`
allocates ~512 valarray temporaries per byte. Fused into an explicit loop with
identical arithmetic. Result: **identical output, 216.1 vs 224.1 us/byte — no
speedup.** libstdc++ valarray already uses expression templates; the compiler was
eliding them. Cost is genuine arithmetic, dominated by the O(output_size x cells)
= 256xH output-layer update and BPTT backprop. Reducing output_size is the only
real lever; horizon does not change amortized cost.

## STATUS
First verified, byte-exact, net-positive improvement under real constraints.
**But NOT a record:** cmix already contains Direct/DirectHash/Indirect/
IndirectHash/Match/PAQ8(word,sparse,record,nest,distance,dmc)/PPMD/
Lstm(256,256,200,2,100,0.03,10). My baseline is fxcm ALONE (~10% behind
cmix-lex), so this moves toward the record, not past it. Real entries sit at
96-99% of the time budget, so in a true submission this must be paid for by
removing models, as fx-cmix did.

---
## E19 — Dictionary-code bucket models — IMPLEMENTED, DEAD (+0.024%)

**Novelty check passed.** cmix's `english.dic` is deliberately ORDERED: modal
verbs together (`will,would,can,may`), pronouns together (`it,there,he,they`),
alphabetical topical runs later (`butane,butanol,byproduct,calcination`). fxcm
uses `lastCW` only for exact comparisons (cwISBN, cwHTTP) and hashes it whole
into `worcxt.Update(word0,c1,Type,whash,lastCW,..)`. **No bucketing of the code
index anywhere.** `cwbuf` is a U8 *byte* history, not word indices. So the
dictionary's curated proximity is discarded — a genuinely absent, ZERO-shipped-
byte information source (the dictionary is already in the pipeline).

**Offline signal was large.** Held-out bigram LM over 2,562,274 in-dictionary
tokens (80/20 split, enwik8 20 MB):

| model | bits/word |
|---|---|
| exact bigram + backoff | 11.1646 |
| bucket >>4 / >>6 / >>8 alone | 11.5650 / 11.6635 / 11.5924 |
| **MIX exact + bucket>>6 (lam=0.7)** | **10.1366 (+9.21%)** |

Bucket-alone is WORSE than exact yet the mix wins — same decorrelation signature
as the LSTM.

**Real pipeline: 521,198 -> 521,074 = +0.024%** (124 bytes), 149 s vs 161 s
(free CPU-wise). Model verified LIVE: 3,200,000 calls, 1,538,289 nonzero lastCW,
124,089 word transitions — the negative is genuine, not a no-op.

**Why it died:** fx2-cmix already added "a stemmer with grammatical word types
(article, conjunction, adposition, conjunctive adverb) and filtered word-stream
contexts by word type". That IS word clustering. My dictionary buckets are a
cruder version of a linguistic class system fxcm already has.

## E20 — LSTM curve completed + speed attempt

96c/1L: **518,846 (+0.451%)**, ctime 511 s, dtime 502 s, **DECOMP EXACT**.
Measured enwik9 projection 47.3 h — OVER the 42.48 h cap (my fitted cost model
said 42.0 h and was optimistic; measurement overrides).
**Only 64c fits: 35.0 h, +0.371% (3 MB) / +0.394% (10 MB).**

Speed attempt: fused the output-layer update (`output_layer_[e][i] = ...[le][i];
... -= lr*error*hidden_`) into an explicit loop to kill ~512 valarray temporaries
per byte. Result: **identical output, 216.1 vs 224.1 us/byte — NO speedup.**
libstdc++ valarray uses expression templates; the compiler already elided them.
Cost is genuine arithmetic in the O(output_size x cells)=256xH output-layer
update and BPTT backprop. Reducing output_size is the only remaining lever.

## SCOREBOARD — real regime, all byte-exact verified
| idea | gain | status |
|---|---|---|
| page-local models | +0.015% | dead |
| free page ordering | -0.006% | dead |
| anchored word-prefix | +0.003% | dead |
| dictionary-code buckets | +0.024% | dead |
| **online LSTM 64c/1L** | **+0.371%** | **ALIVE, fits budget** |

Five structural/information-source ideas, all <=0.024%. Only the model with a
different inductive bias adds. Consistent with the E14 calibration ceiling
(oracle recalibration of fxcm = 0.1362%).

---
## E21-E24 — BINARY-TREE HEAD + DEAD-AUX REMOVAL + DEPTH (real regime)

### E21 Binary-tree output head (`btl.h`/`btl.cpp`)
cmix's LSTM emits a 256-way softmax, but a binary arithmetic coder consumes ONE
probability per bit. P(byte)=prod_k P(bit_k|prefix) indexed by fxcm's own `c0` is
an exact balanced-tree factorisation, same parameter count, **8*H instead of
256*H per byte**. Adam, layer-norm and exact BPTT preserved: `LstmLayer` is used
verbatim; BPTT exactness kept by storing only the 8 weight rows touched per
timestep (`horizon*8*H` = 102 KB) instead of cmix's full per-epoch output-layer
copy. `output_layer_` (3.28 MB) dropped entirely.

Standalone: 64c **61.0 us/byte @ 3.1988 bpb** vs cmix softmax 64c 86.6 us @
3.186 bpb -> **1.42x faster, quality preserved**. (Softmax head was ~30% of LSTM
cost, NOT the 64% I projected - gates/BPTT dominate.)

Real pipeline, 120c: **519,092 = +0.404%**, 432 s, 2.21 GB, ROUNDTRIP EXACT,
40.0 h projected.

### E22 Dead auxiliary-input block — the big win
`layer_input_` is sized `input_size + 1 + num_cells*2` with hidden copied at
offset `input_size_`(=256). Those first 256 entries are the AUXILIARY input
block cmix fills via `SetInput` from its other models — **my integration never
calls it**, so every gate multiplied 256 zeros per cell. At 120 cells: 377
multiply-adds where 121 are needed.
Fix: pass `auxiliary_input_size = 0`, shrink `layer_input_`.
**3.9x at 64c (61.0 -> 15.7 us/byte), 2.7x at 128c (141.8 -> 51.7).**
(bpb shifted 3.1988 -> 3.2173 only because `sqrt(6/(input_size_+output_size_))`
changes the init scale when aux goes to 0 — not a semantic change.)
Not a cmix bug: dead weight created by how the LSTM was embedded.

Real pipeline, 192c/1L: **518,670 = +0.485%**, ctime 382 s, dtime 375 s,
2.21 GB, **ROUNDTRIP EXACT**, **35.4 h projected — FITS**.
Beats softmax 96c on size while using less time than softmax 64c.

### E23 Depth beats width at equal compute (standalone, 400 KB)
| config | us/byte | bpb | offline gain | proj h |
|---|---|---|---|---|
| 160c/1L | 83.1 | 3.1125 | 0.095% | 31.4 |
| 192c/1L | 108.4 | 3.1191 | 0.089% | 35.7 |
| **96c/2L** | 86.2 | 3.0549 | **0.121%** | 32.0 |
| 128c/2L | 150.8 | 3.0167 | 0.167% | 42.8 |
| 80c/3L | 110.0 | 3.0224 | 0.161% | 36.0 |
| **96c/3L** | 144.8 | 3.0015 | **0.177%** | 41.8 |
| 112c/3L | 205.6 | 2.9973 | 0.194% | 52.0 (OVER) |

At matched cost 96c/2L (3.0549) crushes 160c/1L (3.1125). cmix ships 2 layers
for a reason. Depth is the right axis; 3 layers better still.
NOTE: offline harness understates real gain ~5.4x (192c/1L: offline 0.089% ->
real 0.485%), so use it for RANKING only.

### E24 IN PROGRESS: 96c/3L in the real pipeline (proj 41.8 h, tight)
Fallback if over budget: 80c/3L (36.0 h, offline 0.161%).

## CURRENT BEST VERIFIED
**fxcm26 + tree-head LSTM 192c/1L = 518,670 vs 521,198 baseline = +0.485%**,
byte-exact both directions, 382 s / 375 s, 2.21 GB, 35.4 h projected,
S1 +25,884 B repaid ~16x at enwik9 scale.
Caveat unchanged: baseline is fxcm ALONE (~10% behind cmix-lex) and cmix already
has an LSTM. Verified improvement over a measurable baseline; NOT a record.

---
## E25 — Depth sweep in the REAL pipeline (all byte-exact verified)
Baseline 521,198. Budget 42.48 h = 252 us/DIC byte.

| config | archive | gain | ctime | us/B | proj h | fits | roundtrip |
|---|---|---|---|---|---|---|---|
| softmax 64c/1L | 519,263 | +0.371% | 378 | 208 | 35.0 | YES | EXACT |
| tree-head 192c/1L | 518,670 | +0.485% | 382 | 211 | 35.4 | YES | EXACT |
| tree-head 72c/3L | 518,366 | +0.543% | 402 | 222 | 37.2 | YES | EXACT |
| **tree-head 72c/3L init0.5** | **518,283** | **+0.559%** | 397 | 219 | **36.7** | YES | **EXACT** |
| **tree-head 76c/3L** | **518,191** | **+0.577%** | 458 | 252 | **42.4** | tight | **EXACT** |
| tree-head 76c/3L init0.5 | 518,235 | +0.568% | (contended) | - | - | - | pending |
| tree-head 96c/3L | 517,789 | +0.654% | 626 | 345 | 58.0 | **NO** | EXACT |

96c/3L is the best compressor but OVER budget. 76c/3L is best in-budget at +0.577%
with only 0.08 h margin. **72c/3L@init0.5 (+0.559%, 36.7 h) is the config with real
margin and is the recommended submission candidate.**

Projection error worth remembering: I predicted 96c/3L at 41.8 h from standalone
400 KB timings; actual 58.0 h. 3-layer integration overhead is ~111 us, not the
~15 us assumed. Standalone timings understate multi-layer cost badly.

## E26 — Init scale retune: works, but my reasoning was WRONG
Effective fan-in is 1 one-hot + cells + bias, so Xavier suggests
sqrt(6/(cells+2)) ~ 0.285 vs the actual sqrt(6/256)=0.153 => I predicted the
scale was ~1.9x TOO SMALL. **Larger was strictly worse**: multiplier 1.0/1.9/3.0
-> 3.0399/3.0643/3.0959 bpb. The optimum is BELOW 1.0.

| initMul | bpb (72c/3L, 400 KB) | offline gain |
|---|---|---|
| 0.15 | 3.0201 | 0.166% |
| **0.5** | **3.0192** | **0.175%** |
| 1.0 | 3.0399 | 0.144% |
| 1.3 / 1.9 / 3.0 | 3.0454 / 3.0643 / 3.0959 | - |

Free (zero CPU). Real-pipeline effect at 72c: +0.543% -> +0.559% (only +0.016%,
83 bytes) — far less than the offline harness implied (22% relative). At 76c it
was slightly NEGATIVE (+0.577% -> +0.568%), i.e. within noise. Offline harness
remains a RANKING tool only.

## E27 — Block-diagonal recurrent weights — PROMISING, cheaper AND better
Restrict each cell to read only its own block of the previous hidden state
(recurrent part only; the lower-layer pathway stays dense). Implemented by
masking off-block recurrent weights after init and after every Adam update, so
forward/backward stay consistent.

| blocks | bpb @200 KB | bpb @400 KB |
|---|---|---|
| 1 | 3.1627 | 3.0192 |
| **4** | **3.1301** | **3.0070** |

**Block-diagonal is BETTER, not just cheaper** — it acts as a regulariser at
these data scales. Holds at both 200 KB and 400 KB.

Cost implication (fast path NOT yet implemented — current build only masks, it
does not skip the multiplies): recurrent cost per gate per cell goes cells ->
cells/B. Layer 0: 73 -> ~19 ops (3.8x); layers 1-2: 145 -> 91 (1.6x, since the
dense lower-layer pathway remains). Overall ~2x, which would allow ~1.41x more
cells at equal cost, on top of the quality gain.

**NEXT: implement the block-diagonal fast path** (skip off-block indices in
ForwardPass and in the gradient accumulation), then re-sweep cells.

---
## E28 — Block-diagonal recurrent weights: FAST PATH + real pipeline

**Fast path implemented** in `lstm-layer-bd.cpp`: ForwardPass and the gradient
accumulation skip off-block recurrent indices (dense inter-layer pathway kept).
Two bugs found on the way:
1. First attempt was SLOWER (350 vs 202 us/byte) — `MaskAll()` had been placed
   inside the per-cell Adam loop, running num_cells times per horizon.
2. With the fast path, off-block gradients are exactly zero, so Adam never moves
   those weights => masking ONCE after init is sufficient. Moved to constructor.

Result at 72c/3L, 200 KB: **b=4 is 2.16x faster AND better** (94.0 us/byte,
3.1306 bpb) than b=1 (203.0 us/byte, 3.1627 bpb). Block-diagonal acts as a
regulariser at these data scales — cheaper and better simultaneously.

### Real pipeline (3 MB, baseline 521,198, budget 252 us/DIC byte)
| config | archive | gain | ctime | us/B | proj h | fits | roundtrip |
|---|---|---|---|---|---|---|---|
| **100c/3L b=4** | **517,942** | **+0.625%** | 456 | 251 | **42.2** | yes (thin) | **EXACT** |
| 100c/3L b=8 | 518,125 | +0.590% | 434 | 239 | 40.2 | yes | pending |
| 120c/3L b=4 | 517,464 | +0.716% | 582 | 321 | 53.9 | **NO** | not run |

### Block-count sweep at 100 cells (standalone, 200 KB)
| blocks | bpb |
|---|---|
| 2 | 3.1070 |
| 4 | 3.0948 |
| **8** | **3.0924** |
| 20 | 3.1078 |

**The standalone ranking did NOT transfer.** b=8 won at 200 KB but LOST in the
real 3 MB pipeline (+0.590% vs b=4's +0.625%). Same lesson as the timing
projections: small-slice measurements rank unreliably. b=4 is the choice.

### Projection error, 5th consecutive in the same direction
Predicted 120c/3L b=4 at 39.1 h; actual **53.9 h**. Standalone timings
systematically understate multi-layer/multi-block cost in the real pipeline.
No cost extrapolation of mine should be trusted — only measured pipeline runs.

## CURRENT BEST VERIFIED IN-BUDGET
**fxcm26 + tree-head block-diagonal LSTM 100c/3L b=4, initMul 0.5**
**517,942 vs 521,198 = +0.625%**, ctime 456 s, dtime 527 s, RSS 2.21 GB,
**ROUNDTRIP EXACT**, 42.2 h projected vs 42.48 h cap (0.28 h margin — thin).
Safer-margin alternative: 72c/3L init0.5 = +0.559% at 36.7 h, EXACT.
Best compression overall: 120c/3L b=4 = +0.716% but 53.9 h, OUT of budget.

Caveat unchanged: baseline is fxcm ALONE (~10% behind cmix-lex) and cmix already
ships an LSTM. Verified improvement over a measurable baseline; NOT a record.

## E29 — Mid-size width sweep, block-diagonal b=4, REAL PIPELINE ONLY
(no small-slice projections used for ranking, per lesson from E28)

| cells | archive | gain | ctime | us/B | proj h | margin | roundtrip |
|---|---|---|---|---|---|---|---|
| 92 | **517,996** | **+0.614%** | 416 | 229 | **38.5** | **3.9 h** | pending |
| 96 | 518,026 | +0.609% | 438 | 241 | 40.6 | 1.9 h | **EXACT** |
| 100 | **517,942** | **+0.625%** | 456 | 251 | 42.2 | 0.28 h | **EXACT** |
| 120 | 517,464 | +0.716% | 582 | 321 | 53.9 | OVER | - |

**The width curve is NON-MONOTONIC**: 92c compresses BETTER than 96c
(517,996 vs 518,026) while running FASTER (416 s vs 438 s). Consistent with the
block-diagonal regularisation result — capacity is not the binding factor at
this data scale, so more cells can hurt.

**Recommendation: 92c/3L b=4 initMul 0.5** — +0.614% with 3.9 h of margin,
vs 100c's +0.625% with only 0.28 h. Giving up 0.011% for 3.6 h of headroom is
the right trade for a submission.

---
## E30 — Forget-gate bias retune (standalone, 200 KB DIC)

**Hypothesis.** The forget-gate's last weight is hardcoded to 1 (cmix default).
Larger bias → forget gate starts closer to 1 → longer memory. Rare/novel words
are a large residual (E12); a stickier cell state might carry identity across
spans fxcm cannot. Zero extra CPU. Differs from E26 (initMul scales ALL
weights); this touches only the forget-gate bias input.

**Standalone harness reproduced E27 closely:** 72c/3L b=4 initMul=0.5
forgetBias=1.0 on 200 KB DIC → **3.1343 bpb** (E27 reported 3.1306). This
machine is ~2× slower than the Xeon (205 vs 94 µs/byte); use it for quality
ranking only, never for Hutter-hour projections.

DIC preprocessor reproduced exactly: 3,000,000 → **1,814,514** bytes,
roundtrip BYTE-EXACT. Locked sources MD5-matched except reconstructed
`lstm-layer-bd.h` and `dic/main.cpp`.

| forgetBias | bpb @200KB DIC | vs bias=1.0 |
|---|---|---|
| **0.0** | **3.0861** | **−0.0482** |
| 0.5 | 3.1157 | −0.0186 |
| **1.0 (cmix / locked)** | **3.1343** | — |
| 1.5 | 3.1480 | +0.0137 |
| 2.0 | 3.1693 | +0.0350 |
| 3.0 | 3.1826 | +0.0483 |
| 5.0 | 3.2002 | +0.0659 |

**Strictly monotonic: smaller is better.** The "longer memory" justification was
wrong, same class of error as E26. Wikipedia topic shifts want *faster* state
turnover. RMS-norm (no mean subtract) does not cancel a uniform +1 bias, so
bias=1 systematically sticks the forget gate.

This is free. Next: negative bias, confirm at 92c and 400 KB, then real pipeline
if it survives. Does NOT count as a candidate until DIC→fxcm roundtrip.

### E30b — negative bias + 92c confirmation (200 KB DIC)

| cells | forgetBias | bpb | vs locked-same-width |
|---|---|---|---|
| 72 | −1.0 | 3.1355 | worse than 0, ≈ bias 1 |
| 72 | −0.5 | 3.1054 | still worse than 0 |
| 72 | **0.0** | **3.0861** | **best** |
| 72 | 0.25 | 3.1012 | worse than 0 |
| 92 | 1.0 (locked) | 3.1046 | — |
| 92 | **0.0** | **3.0603** | **−0.0443 bpb** |

Optimum is at 0, not below. The 92c locked width still gains. Zero CPU.

### E30c — 400 KB DIC, 92c/3L b=4

| forgetBias | bpb | vs bias=1 |
|---|---|---|
| 1.0 | 2.9767 | — |
| **0.0** | **2.9469** | **−0.0298** |

Gap shrinks with more data (0.044 → 0.030) but does not vanish. Next: real 3 MB pipeline.

---
## E35/E36 — fx2-cmix LSTM consumption we do not have (coded, not run)

fx2-cmix `fxcmv1.cpp` after the cmix LSTM is attached:

- L1 mixer input `stretch(lstmpr)` — we have this at n[544]/n[545]
- **L2 mixer input `stretch(lstmpr)/2`** — we do not. `mxInputs2` N=32, only 17 filled.
- **mixer context `lstmex`** (argmax remaining byte) on their mixer 9

cmix `ByteModel::ex` is argmax over remaining softmax mass. For a binary-tree head the MAP byte is the greedy walk: `BtLstm::ExpectedByte` (added; unused by running `cmp_fb*`).

We must **not** overwrite `mxA[9]` (lastWT). Replica uses unused `mxA1[1]` (M=1, cxt=0).

| id | switch | parent |
|---|---|---|
| E35 | `-DLSTM_L2_INPUT=1` | locked or E30 winner; one axis |
| E36a | `-DLSTM_MEX_CXT=1` | after E35 reports |
| E32 | slots 546–549 | Agent 6; 546 collinear with 544 |

DIC 3 MB stream: **40.0% bytes ≥128**, high-byte runs mean **1.74** (max 4). Codes are 2–3 byte tokens interleaved with ASCII. ForgetBias=0 (faster turnover) is the blunt response; regime-reset at code boundaries is the sharp one (E37, after E30).

Shipped voyage/t-SNE article order is paid. Reverse-dict is already in fxcm26.

