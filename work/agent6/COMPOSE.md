# AGENT 6 — Composition

Incumbent (LOCKED): fxcm26 + tree-head BD-LSTM **92c/3L/b=4/initMul=0.5/forgetBias=1**, mixer inputs 544/545 only, tree-head **SGD**. Archive **517,996** (+0.614% vs 521,198), 38.5 h, 3.9 h margin.

Do not re-run LSTM × depth × blocks × initMul. Those four are already one model.

Gate in flight: E30d (fb=1 control) vs E30e (fb=0). Zero CPU. A “win” is E30e beating E30d by **>50 B** (E13 was 18 B noise). Tie or loss ⇒ fb stays 1.

---

## Verdict (read this first)

| If E30e (forgetBias=0) … | First composition to run | Config |
|---|---|---|
| **WINS 3 MB** | **fb=0 + mixer-slot fill** | `92c/3L/b=4/initMul=0.5/fb=0` + `fxcm26_slots.cpp` (n[546..549]) |
| **LOSES 3 MB** | **mixer-slot fill alone** | locked incumbent `fb=1` + `fxcm26_slots.cpp` (n[546..549]) |

Either way: **one new axis**. Do not fold in tree-head Adam on the same run.

**Override if E30 is a wash:** E35 (`stretch(bp)/2` on `mxInputs2.n[17]`) is a closer replica of fx2-cmix than E32 slots 547–549. Prefer E35 as COMPOSE-1 when E32’s 546 is known collinear. Still one axis; still ~free CPU.

Why this pair: forgetBias retunes LSTM *gate dynamics*; mixer fill changes how fxcm *consumes* the LSTM and a few flags. No shared parameters. If both work they should add. Mixer is ~free CPU (four stores); it does not spend the 3.9 h margin.

---

## What each item actually is

| item | status | information | CPU |
|---|---|---|---|
| LSTM itself | locked +0.614% | new inductive bias vs fxcm CMs | paid (fits) |
| depth > width | locked (3L) | same LSTM, capacity axis | paid |
| blocks=4 | locked (b=8 lost at 3 MB) | same LSTM, recurrent topology | paid (saves) |
| initMul=0.5 | locked; real +0.016% at 72c, noise at 76c | same LSTM, Xavier scale | free |
| forgetBias=0 | standalone only; 3 MB in flight | same LSTM, **one** forget-gate bias (overwrites last weight after Xavier) | free |
| mixer 546–559 | coded, not run | mixer *inputs* (not LSTM internals). **Implemented fill is 546–549 only; 550–559 stay 0** | ~free |
| tree-head Adam | coded, not run | same tree output, SGD→Adam | small extra (moments + per-bit ops) |

Locked cluster **L** = LSTM + 3L + b=4 + initMul=0.5. Pairwise tests inside L are done.

Live knobs **not** in L: fb=0, mixer fill, tree-Adam.

---

## Mixer fill internals (do not treat as one information source)

`ncount=560` is SIMD padding (`n == ((n+15)&-16)`). Incumbent zeros n[544..559] then writes only 544/545. `fxcm26_slots.cpp` additionally writes:

| slot | value | vs existing info |
|---|---|---|
| 544 | `stretch(bp)` | LSTM logit (locked) |
| 545 | `stretch((bp+2048)>>1)` | damped LSTM p (locked) |
| **546** | `bp-2048` | **SAME bp**, linear. CMs already pair stretch(p) with (p−2048). E14 ceiling (~0.14%) applies. |
| **547** | `(bpos-3)*400` | bit index as **input**. Mixer 4/7 already put bpos in **context**. Partial overlap. |
| **548** | `isMatch ±2047` | match flag as **input**. Match CMs + mixer cxt already see isMatch. Partial. |
| **549** | `c1>=0x80 ±2047` | dict-code vs literal as **input**. Mixer 8 `deccode` / lastCW / word types nearby. Partial. |
| 550–559 | still 0 | wasted mixer weights; filling them is a later experiment, not this composition |

So the coded bundle is one cheap 3 MB run, but **546 will not add independently of 544/545**. The composition bet is 547–549 (side flags as mixer *inputs*) plus recovering 4 of 14 zero pads. If the bundle **loses** vs the no-fill parent, split: retry **547–549 without 546** before killing mixer fill. Do not kill 547–549 on a 546-dilution failure.

LSTM-as-mixer-**context** (fx2-cmix: expected byte in `mxA[].cxt`) is **not** E32. Complementary to input fill; run later, not in the first composition.

---

## Pairwise matrix

Legend: **C** complementary (should add if both work) · **S** same source (won’t add; don’t compose) · **W** weak/partial overlap · **done** already composed in the incumbent.

|  | LSTM | depth | b=4 | initMul | **fb=0** | **mixer fill** | **tree-Adam** |
|---|---|---|---|---|---|---|---|
| **LSTM** | — | done | done | done | C (dynamics of that LSTM) | C (produce vs consume) | C (head optimizer) |
| **depth** | | — | done | done | C / W | C | C |
| **b=4** | | | — | done | C / W (both affect state lifetime; different mechanism) | C | C |
| **initMul** | | | | — | **W, already stacked in E30 standalone** | C | C (Xavier on layers vs Adam on tree_w_=0) |
| **fb=0** | | | | | — | **C (orthogonal A+B)** | **C** |
| **mixer fill** | | | | | | 546=**S** with 544/545; 547–549=**W** with mixer cxt | **W** on 546 only; **C** on 547–549 |
| **tree-Adam** | | | | | | | — |

### Pairs that share information (will not add)

1. **LSTM × depth × blocks × initMul** — one neural expert. Locked. No factorial.
2. **Mixer 546 × slots 544/545** — same `bp`, stretch vs linear. Same class as E14 mixing of existing p.
3. **Mixer 547 × mixer-4/7 bpos context** — same bit index, input vs context. Small residual possible, not a new source.
4. **Mixer 548 × match-model inputs / isMatch cxt** — same match bit.
5. **Mixer 549 × deccode / lastCW / dict-code paths** — same code-vs-literal bit.
6. **initMul × forgetBias** — both init. Distinct parameters (forget **overwrites** the bias after Xavier), and E30 already measured fb=0 **on** initMul=0.5. Do not sweep a 2-D init grid.
7. **tree-Adam × mixer 546** — both squeeze more from the same tree output (better-trained p vs extra views of p).
8. **SSE / extra squash of LSTM p × any of 544–546** — E14: oracle recalibration ≤0.136%. Dead class.

### Pairs that are complementary (should compose)

1. **forgetBias=0 × mixer fill (esp. 547–549)** — **primary A+B.** Gate init vs mixer inputs. No shared weights. 547–549 do not even read LSTM p.
2. **forgetBias=0 × tree-head Adam** — forget gate vs 256×hsize output head. Compose **after** mixer reports (Adam costs CPU; mixer does not).
3. **mixer 547–549 × tree-Adam** — flags vs head optimizer.
4. **mixer fill × locked L** — consume-side, independent of how L was trained.
5. **tree-Adam × locked L** — SGD on `tree_w_` is the odd one out (layers already Adam). Unlocks existing LSTM, not a new corpus signal.
6. **fb=0 × depth/blocks** — already at 3L/b=4; E30 standalone used that stack. No extra compose run.

Weak but acceptable: **blocks=4 × fb=0** both change how cell state persists (sparse hidden mixing vs forget). Mechanisms differ; E30 standalone already used b=4 + fb=0. Pipeline A/B is the transfer test, not a new pairing.

---

## A+B protocol

Rule: **do not compose two untested knobs.** Compose a **pipeline winner** with the next **orthogonal cheap** knob.

```
E30e fb=0 vs E30d fb=1     ← in flight (A)
        │
        ├─ A wins  → COMPOSE-1: A + mixer fill     (skip mixer-alone; trust orthogonality)
        │              if COMPOSE-1 > A  → keep; next = + tree-Adam if margin
        │              if COMPOSE-1 ≤ A  → revert to A; split mixer (547–549, drop 546)
        │
        └─ A loses → COMPOSE-1: mixer fill on locked fb=1
                       if fill wins → COMPOSE-2: fill + tree-Adam
                       if fill loses → split 547–549; if still dead → tree-Adam alone
```

Do **not** run fb=0 + mixer + tree-Adam in one shot (two untested axes if A just landed; three if A lost).

Do **not** spend the 3.9 h margin on width/4th-layer/more-blocks until these ~free compose runs report. 96c was worse than 92c; b=8 lost; 4th layer is a new arch screen, not a composition of known winners.

---

## Exact first-run configs

### If forget=0 wins 3 MB

```
COMPOSE-WIN-1
  cells=92 layers=3 blocks=4 initMul=0.5 forgetBias=0  horizon=50 lr=0.03
  tree head: SGD (no TREE_ADAM)
  mixer: fxcm26_slots.cpp  n[544..549] written, n[550..559]=0, ncount=560
  vs parent: E30e (same LSTM, slots 544/545 only)
  accept if archive < parent − 50 B
```

Sources: `lstm_forget0.cpp` + `fxcm26_slots.cpp` + stock `btl-bd.cpp` (TREE_ADAM off).

### If forget=0 loses 3 MB

```
COMPOSE-LOSE-1
  cells=92 layers=3 blocks=4 initMul=0.5 forgetBias=1  horizon=50 lr=0.03
  tree head: SGD (no TREE_ADAM)
  mixer: fxcm26_slots.cpp  n[544..549] written, n[550..559]=0, ncount=560
  vs parent: locked 517,996 (E30d)
  accept if archive < 517,996 − 50 B
```

Sources: locked LSTM (`lstm_forget1.cpp` / default FORGET_BIAS) + `fxcm26_slots.cpp`.

### Explicitly not first

- tree-head Adam (`btl_adam.cpp`) — complementary to both, but **costs CPU** and is untested. Composition #2.
- 100c / 4th layer / b=8 — not compositions of independent info; 100c is 54 B with 0.28 h margin; b=8 already lost.
- LSTM expected-byte as mixer **context** — orthogonal to input fill; implement after E32 reports.
- Filling 550–559 with more flags — separate from the coded 546–549 bundle.

---

## Expected additivity (if both work)

ForgetBias standalone shrank 0.044 → 0.030 bpb from 200→400 KB; initMul transferred at ~1/10 of the offline hint. Pipeline fb=0 is likely **tens to low hundreds of bytes**, not another +0.6%. Mixer 547–549 is a gate/feature, not a new expert: likely **≤ E14’s 0.14%** and probably much less (partial overlap with existing cxt). Sum-if-independent is the right prior; overlap should be small because they do not share parameters. If COMPOSE-WIN-1 ≈ A, mixer is redundant given a better LSTM p (mixer already has 544/545). That is still a useful kill.
