# AGENT 5 — Compute / allocation

Hours below are **Xeon 1-core @ 2.1 GHz, real DIC→fxcm26 pipeline**, scaled at 605M DIC bytes to the 42.48 h cap (252 µs/DIC byte). The Windows box is ~2× slower (E30: 205 vs 94 µs/byte); **its wall times are not Hutter hours** and are not used here. No compressor was run for this note.

**Immediate next pipeline run (free):** locked 92c/3L/b=4/initMul=0.5 with **forgetBias=0**.

**Single next *compute* pipeline config (this agent's pick):**

```
fxcm26 MEMDIV=8, tree-head BD LSTM
76c / 4L / b=4 / initMul=0.5 / forgetBias=0 / horizon=50 / lr=0.03
mixer slots 544/545 only (do not fill 546–559 in this run)
```

---

## 1. Pareto frontier, archive vs projected hours (E17–E29)

Minimize archive **and** hours. A point is dominated if another is smaller on both axes. Times are the log's Xeon projections, not Windows.

### 1.1 All real-pipeline points (3 MB DIC, baseline 521,198)

| config | archive | proj h | margin | fits | Pareto? |
|---|---:|---:|---:|---|---|
| softmax 64c/1L | 519,263 | 35.0 | 7.5 | yes | yes (fastest LSTM) |
| tree 192c/1L aux=0 | 518,670 | 35.4 | 7.1 | yes | yes |
| 72c/3L dense | 518,366 | 37.2 | 5.3 | yes | no — beaten by init0.5 |
| **72c/3L dense init0.5** | **518,283** | **36.7** | **5.8** | yes | **yes** |
| 76c/3L dense | 518,191 | 42.4 | 0.08 | tight | no — 92c BD better on both |
| **92c/3L b=4 init0.5 (LOCKED)** | **517,996** | **38.5** | **3.9** | yes | **yes** |
| 96c/3L b=4 | 518,026 | 40.6 | 1.9 | yes | **no — worse than 92c on both** |
| 100c/3L b=8 | 518,125 | 40.2 | 2.3 | yes | no — worse than 92c on both |
| **100c/3L b=4** | **517,942** | **42.2** | **0.28** | yes, thin | **yes** |
| tree 120c (E21, dead aux still on) | 519,092 | 40.0 | 2.5 | yes | no |
| softmax 96c/1L | 518,846 | 47.3 | — | **NO** | no |
| **120c/3L b=4** | **517,464** | **53.9** | — | **NO** | **yes among over-budget** |
| 96c/3L dense | 517,789 | 58.0 | — | **NO** | **no — 120c BD better on both** |
| softmax 128c/1L | 518,320 | 59.3 | — | **NO** | no |

**In-budget frontier (the only legal one):**

```
519,263 @ 35.0h   softmax 64c/1L
518,670 @ 35.4h   tree 192c/1L
518,283 @ 36.7h   72c/3L dense init0.5
517,996 @ 38.5h   92c/3L b=4          ← LOCKED, 3.9 h margin
517,942 @ 42.2h   100c/3L b=4         ← 0.28 h margin
```

96c/3L dense at 517,789 / 58 h is the best *dense* compressor and is **not** on the frontier: 120c/3L b=4 is 325 bytes smaller and 4.1 h cheaper. 96c BD is strictly dominated by locked 92c (slower *and* 30 bytes worse).

### 1.2 Bytes per Hutter-hour along the in-budget frontier

| step | Δ bytes (3 MB) | Δ h | B/h |
|---|---:|---:|---:|
| 64c softmax → 192c/1L | 593 | 0.4 | 1,480 |
| 192c/1L → 72c/3L init0.5 | 387 | 1.3 | 298 |
| 72c/3L → 92c/3L b=4 | 287 | 1.8 | 159 |
| **92c → 100c** | **54** | **3.7** | **14.6** |

The frontier has flattened. The last legal step (92c→100c) is 54 bytes for the entire remaining budget. At enwik9 scale that is ~0.010% ≈ 11 KB of a ~110 MB archive, paid with 3.7 h and only 0.28 h left. E20/E25/E28: every cost model so far has been optimistic in the same direction; 0.28 h cannot absorb decompression variance or judging-T. 100c dtime was 527 s vs 456 s ctime in E28 (possibly contention, but the margin cannot eat a 15% d/c split). **100c is on the Pareto curve and is not a submission candidate.**

Locked 92c (38.5 h / 517,996 / 3.9 h margin) is the right base. The 3.9 h is an asset to spend on a *new axis*, not on more cells.

---

## 2. Q1 — Is forgetBias=0 the right first use of the 3.9 h?

**Yes — and it does not spend the 3.9 h.** forgetBias=0 is a single init constant (last forget-gate weight). Same MACs, same RSS, same 38.5 h. The margin is still 3.9 h after it.

E30 (standalone, quality only — **do not take those µs as hours**):

- strictly monotonic: smaller bias better; 0 beats negatives
- 92c, 200 KB DIC: 3.1046 → 3.0603 bpb
- 92c, 400 KB DIC: 2.9767 → 2.9469 (−0.0298); gap shrinks with data but does not vanish

Transfer risk is E26-class (free retune, offline overstated; 72c real +83 B, 76c slightly negative). That is still the correct first action: expected bytes are non-negative at **0.00 h**, and a regression is cheap to revert. Spending the 3.9 h on 92c→100c instead would buy a measured 54 B and destroy the buffer *before* the free knob is measured.

Do not combine forgetBias with a width/depth change in the same 3 MB run. One variable.

---

## 3. Q2 — After forget=0, what uses the remaining 3.9 h?

Four options. Only one of them both (a) can legally consume ~hours and (b) has a positive bytes/hour case.

### More cells — no

Width is non-monotonic (E29): 96c is *worse* than 92c at higher cost. 100c is +54 B / +3.7 h = 14.6 B/h and leaves 0.28 h. There is no 93–95c hunt worth a pipeline run; 92 vs 96 is 30 B, noise-scale. Width is exhausted as a use of margin.

### More blocks — no

More blocks **frees** time, it does not spend it. E28 real pipeline: 100c b=8 is 40.2 h / 518,125 vs b=4 42.2 h / 517,942 — **−183 B** for −2.0 h. Standalone 200 KB ranked b=8 first; it did not transfer. b=20 was worse even standalone.

Fewer blocks (b=2 / dense) *would* spend hours and is the wrong quality direction: standalone 100c b=2 3.1070 > b=4 3.0948, and 96c/3L dense is 58 h (OVER) and dominated by 120c BD. FLOP-scale 92c b=2 ≈ 1.27× LSTM ≈ 45 h, over cap. Do not move toward dense.

### Extra mixer inputs — not a margin spend

Locked `ncount=560` already; slots 546–559 are zeros; mixer width is paid. Filling them with extra views of `bp` (or isMatch / dict-code flags) is ~0 LSTM CPU. E14: oracle recalibration of the *same* information ≤ 0.136%. Extra linear transforms of the two LSTM mixer inputs already present (544/545) are nearly collinear. E4 control / E19 buckets: extra mixer capacity without a new inductive bias is ≤ tens of bytes in this regime. Fine as a later free add-on; **it does not use the 3.9 h** and must not displace a depth run.

Do **not** restore the 256-wide LSTM aux block (cmix `SetInput`). That is what E22 removed for a 2.7–3.9× speedup. Filling it would spend far more than 3.9 h.

### 4th layer — yes, at reduced width

E23: depth beats width at equal compute (96c/2L crushed 160c/1L). Real pipeline agreed: 192c/1L 518,670 @ 35.4 h → 72c/3L 518,366 @ 37.2 h, then init0.5 to 518,283 @ 36.7 h. 2L→3L still paid. 3L→4L is the unpaid axis. 92c/4L does **not** fit (below).

Gate-MAC model from the BD fast path (3 gates; L0 input is `1+C`, upper layers `1+2C`; recurrent `C/B`; lower-layer path dense):

| config | relative LSTM MACs vs 92c/3L b=4 | LSTM h (from 23.6 h) | + fxcm 14.9 h | vs cap |
|---|---:|---:|---:|---|
| 92c/3L b=4 (measured) | 1.00 | 23.6 | **38.5** | 3.9 h under |
| 92c/4L b=4 | 1.455 | 34.3 | **49.2** | OVER ~6.6 h |
| 80c/4L b=4 | 1.101 | 26.0 | **40.9** | ~1.6 h under |
| **76c/4L b=4** | **0.994** | **23.5** | **38.4** | **~4.1 h under** |
| 92c/3L b=2 | 1.27 | 30.0 | ~44.9 | OVER |
| 100c/3L b=4 | measured | — | **42.2** | 0.28 h |

76c/4L is an **equal-FLOP swap** of +1 layer for −16 cells. That is the same move that historically had 159–298 B/h, not 14.6. The 3.9 h is kept as a **4L integration buffer**, not burned on width: E25/E28 standalone→pipeline understated multi-layer cost by ~1.38×; those errors were from *standalone* timing, not from scaling one measured pipeline 3L point. Residual risk is extra per-layer overhead on the order of tens of µs. +20 µs ≈ +3.4 h → ~41.9 h, still in. +40 µs would go over — that is what the 3.9 h is for, and why 80c/4L (1.6 h mean margin) is the wrong *first* 4L run.

---

## 4. Q3 — Single next real-pipeline run besides forget=0, best B/h

**76c / 4L / b=4 / initMul=0.5 / forgetBias=0.**

Expected bytes/hour ranking of the four axes, besides forget=0:

| candidate | Δh vs locked 38.5 | E[ΔB @ 3 MB] | B/h | why |
|---|---|---|---|---|
| **76c/4L b=4** | **~0 mean, 0–4 if 4L tax** | **+100…+400 if 3L→4L is even ~¼ of 2L→3L** | **best unpaid axis** | equal-FLOP depth; width already non-monotonic |
| 100c/3L b=4 | +3.7 measured | +54 measured | 14.6 | already measured; kills margin |
| 96c/3L b=4 | +2.1 | **−30** | negative | dominated |
| b=8 at 92c | ~−2 | negative (E28) | negative | more blocks lost |
| fill mixer 546–559 | ~0 | +0…+80, E14-capped | high iff any bytes, **low EV** | not new information |
| 92c/4L | +~11 | unknown | illegal | OVER |
| 120c/3L b=4 | +15.4 | +532 measured | 34.5 but OVER | 53.9 h |

2L→3L at matched cost was the largest remaining step after aux-removal. Even a heavily diminished 3L→4L (say ¼ of that real-pipeline depth step, ~100 B) at ~0 extra hours beats 100c's 54 B / 3.7 h. If 4L is a no-op, 76c may give back some of the 92c-vs-72c width gain (~hundreds of bytes in the dense era) and we kill 4L after one run. That is a cheap negative.

**Do not** put mixer extras in this run. If 76c/4L lands ≤41 h and beats 517,996, the leftover margin is for 80c/4L (same depth, +4 cells), not for 92c-width 4L.

Abort: if 3 MB `us/B` on the **Xeon** implies >42 h (`us/B > 252`), stop; do not project from the Windows box. Fallback is not more cells; it is “4L does not fit, keep 92c/3L + forgetBias=0”.

---

## 5. Recommended next pipeline config (one)

```
DIC + fxcm26 (MEMDIV 8)
tree-head block-diagonal LSTM
cells=76  layers=4  blocks=4
initMul=0.5  forgetBias=0  horizon=50  lr=0.03
mixer: n[544], n[545] only; ncount=560 unchanged
```

Prerequisite, already the right first 3 MB run and **not** this config: locked 92c/3L/b=4 with only `forgetBias` 1→0. Measure both directions; Hutter is per-program, c and d each < 42.48 h.

Do not use Windows µs to accept or reject 76c/4L against 42.48 h.
