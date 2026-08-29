# Agent 1 — architecture screens (not width copies of E25–E29)

Isolated copies of the tree-head LSTM stack live in this directory. **Do not
edit `work/src`.** Incumbent (LOCKED, 3 MB pipeline): **92c / 3L / blocks=4 /
initMul=0.5 / horizon=50 / lr=0.03 / tree-head SGD**. forgetBias 0 vs 1 is on
the live 3 MB machine (`cmp_fb1.exe`). Tree-head Adam is already in
`work/src/btl_adam.cpp` and `tools/lstm_stand_adam.exe` — do not recompile.

This file is **not** another 80/84/88/92/96/100-cell sweep, **not** another
blocks∈{2,4,8,20} rerun at 100c, **not** another 1L/2L/3L width trade at 96c,
and **not** an initMul-only retune at forgetBias=1. Those are E25–E29.

Standalone rankings on 50–200 KB **kill** candidates; they do **not** promote
to the 3 MB pipeline (E28: b=8 won at 200 KB and lost at 3 MB).

---

## Run log (this agent)

| item | result |
| --- | --- |
| `cmp_fb1.exe` | **DECOMPRESSING** after compress **518095** in 2121 s (MinGW; not the Linux lock) |
| 50 KB `lstm_stand` 72c/3L/b=4/fb=0 vs 64c/4L/b=4 | **SKIPPED** — code-only rule while the pipeline job owns the core |
| `lstm_stand.exe` / `lstm_stand_adam.exe` | exist; not invoked |
| `work/src` | untouched |

**Next screen (run as soon as `cmp_fb1.exe` is gone):** S1 below, 50 KB DIC,
both arms forgetBias=0. Record bpb. Promote only if 4L is clearly better
(see kill rule). Do not start S2–S5 until S1 returns.

```
# from repo root, after confirming Get-Process cmp_fb1 is empty
$exe = "C:\Users\vivi\hutter\tools\lstm_stand.exe"
$in  = "C:\Users\vivi\hutter\data\dic200k.bin"
& $exe $in 51200 72 3 4 0.5 0.0 0.03 50   # control, ~E30 geometry
& $exe $in 51200 64 4 4 0.5 0.0 0.03 50   # 4L probe
```

50 KB is a **warmup-hostile** slice (E15: LSTM gain rises with warmth). 4L has
more parameters and will look worse than it is. Kill 4L at 50 KB only if it
loses by **> 0.05 bpb**. A photo-finish → rerun 200 KB, still standalone.

---

## What the incumbent actually is

`LstmLayer` is **CIFG**, not a 4-gate LSTM: forget, candidate (`input_node_`),
output. `input_gate = 1 - forget`. RMS-norm (no mean subtract) + Adam on gates.
Recurrent weights are **block-diagonal** (`g_blocks=4`); the lower-layer
pathway stays dense. Forget-gate last weight is hardcoded to `g_forgetBias`
**after** Xavier×`initMul` (so initMul does not scale the forget bias).

Tree head: `PBit(c0) = σ(tree_w[c0] · hidden)`, `hidden` has a trailing `1`,
so every tree node already has its own bias. SGD on `tree_w` (Adam variant
exists, unrun). `c0` is the byte prefix `1..255`.

### Forward hidden affine MACs / byte (3 gates; one-hot lookups ignored)

`C` cells, `L` layers, `B` blocks:

```
layer0:     3 × (C/B + 1)                 # blocked rec + bias
layer 1..L-1: 3 × (C/B + C + 1)           # blocked rec + dense below + bias
total     = 3L(C/B + 1) + 3(L−1)C
tree head = 8 × (C·L + 1)
```

| config | hidden affine | tree | vs 72c/3L hidden |
| --- | ---: | ---: | --- |
| 72c/3L/b=4 | 603 | 1736 | control |
| 56c/4L/b=4 | 684 | 1800 | +13% hidden, tree ≈ matched |
| 64c/4L/b=4 | 780 | 2056 | +29% hidden, +18% tree |
| 48c/4L/b=4 | 588 | 1544 | ≈ matched hidden, cheaper tree |
| 92c/3L/b=4 | 768 | 2216 | incumbent |

BPTT still walks a **dense C²** transpose for recurrent error even when
forward skips off-block indices (`lstm-layer-bd.cpp` BackwardPass ~210–217).
That makes 56c/4L *cheaper* on the C² term than 72c/3L (4×3×56² = 37632 vs
3×3×72² = 46656). Do not treat 64c/4L as “free depth”; it is a modest
compute *increase*. 56c/4L is the closer MAC match and should be S1b if 64c
is mixed.

---

## Ranked screens

Rank = expected bits / implementation cost, given E23 (depth > width at
matched cost), E26 (initMul<1), E27–E28 (blocks=4 is a regulariser, b=8 did
not transfer), E30 (forgetBias=0 beats 1, monotonic, gap shrinks with data).

### S1 — 4 layers at 56–64 cells  *(next)*

**Why this is not E25.** E25 compared 1L/2L/3L and then **widened 3L**.
Nobody has stacked a 4th layer. Depth was the winning axis at equal compute.

**Hypothesis.** A 4th layer buys a longer causal feature hierarchy on DIC
word-identity (E11: dict codes are 40% of bytes / 69% of bits) without
going back to the E29 width curve.

**Protocol (standalone, `lstm_stand.exe`, no new code).**

| arm | cells | L | B | initMul | fb | n |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A control | 72 | 3 | 4 | 0.5 | 0 | 51200 |
| B | 64 | 4 | 4 | 0.5 | 0 | 51200 |
| C (if B mixed or CPU free later) | 56 | 4 | 4 | 0.5 | 0 | 51200 or 200000 |
| D MAC-match (optional) | 48 | 4 | 4 | 0.5 | 0 | 200000 |

Same lr=0.03, horizon=50, srand(0). Report bpb and us/byte (us/byte is
machine-local; do not project Hutter hours from it).

**Kill.** 64c/4L worse than 72c/3L by >0.05 bpb at 50 KB, **and** 56c/4L
also worse at 200 KB → depth-4 is done. Do not “fix” it by widening 4L
(that is an E29 copy). Residual skip (add layer-input to hidden) is the
only allowed follow-up if 4L is slightly worse and gradients look dead.

**Promote.** 4L wins by ≥0.02 bpb at 200 KB → queue a 3 MB pipeline run
*after* E30d/e, at 56c or 64c (whichever won), fb=0, b=4, initMul=0.5.
Expect +15–30% LSTM wall time vs 72c/3L; incumbent 92c/3L has 3.9 h
margin, so 64c/4L may still fit where 96c/3L did not.

---

### S2 — forgetBias=0 × initMul, jointly

**Why this is not E26.** E26 swept initMul **at forgetBias=1**. E30 swept
forgetBias **at initMul=0.5**. The forget last-weight is written *after*
Xavier×initMul, so the two knobs are independent in code and coupled in
dynamics: sigmoid(0)=0.5 vs sigmoid(1)≈0.73 changes how large random
weights need to be before RMS-norm.

**Hypothesis.** initMul=0.5 is optimal only because a +1 forget bias was
fighting topic-shift turnover (E30). At fb=0 the scale optimum moves.

**Protocol.** No new code. Grid at **72c/3L/b=4** (cheap) then confirm
winner at **92c/3L/b=4**. n=200000 once CPU is free; 50 KB is too noisy
for a 0.01-scale effect.

```
# fb fixed at 0; sweep initMul
foreach ($m in @("0.15","0.25","0.35","0.50","0.75","1.00")) {
  & $exe $in 200000 72 3 4 $m 0.0 0.03 50
}
```

Optional 2-point check that fb=0 still beats fb=1 at the new initMul
(do not re-sweep the whole E30 bias table).

**Kill.** All fb=0 curves still pick initMul∈{0.35,0.50} within 0.005 bpb
of E30’s 3.0861 → keep 0.5, do not spend pipeline time on initMul.
**Promote.** A new initMul wins by ≥0.015 bpb at 200 KB on 92c → ship with
whatever forgetBias E30e locks.

Zero extra CPU in the compressor. Highest EV/effort after S1 because it
unlocks the E30 candidate properly.

---

### S3 — bit-position bias on the tree logit (8 params)

**Why this is not a width change.** Adds `float bit_bias[8]`, not cells.

**Gap.** `PBit` is `σ(w_{c0}·h)`. The trailing `1` in `hidden` already
gives a **per-node** bias (256 numbers). LSB nodes `c0∈[128,255]` see
1/128 of the bit stream each and warm slowly. Bit **depth** is shared:
MSB of DIC bytes is the dict-code flag (E11: codes ≥0x80 are ~40% of
bytes). An 8-param depth prior pools that base rate.

```
# in PBit / LearnBit; k = 0..7 is MSB-first index already used in lstm_stand
z += bit_bias[k];
bit_bias[k] -= learning_rate * (p - bit);   # SGD; or Adam with tree-head Adam
```

Init at 0 (same as `tree_w_`) **or** at `logit(empirical P(bit=1 | depth))`
measured once on `dic200k.bin` (offline, not shipped). Prefer init=0 for
the first screen so the only change is the extra degree of freedom.

**MAC:** +8 adds/byte. Code: ~15 lines in a private copy of `btl-bd.cpp`
under `work/agent1/src/` (do not touch `work/src`). Keep tree SGD first;
do not combine with unrun tree-Adam.

**Protocol.** 72c/3L/b=4/fb=0/initMul=0.5, n=200000, ± the 8 biases.
**Kill.** Δbpb > −0.005 (noise). Per-node bias already ate the effect.
**Promote.** ≥0.015 bpb at 200 KB → 3 MB; S1 cost is 8 floats and no
timing risk.

If it wins, a later probe is **tied tree rows at the same depth**
(share `w` across sibling nodes, not just the scalar bias). That is a
different screen; do not fold it in.

---

### S4 — GRU / MGU vs CIFG-LSTM at matched MAC

**Why this is not E25.** Same (or larger) width, **different recurrence**.
cmix ships LSTM; a win here is a new inductive bias, which is the only
class that has moved the real pipeline (E15–E24).

This stack is already CIFG (3 affines). Vanilla **GRU is also 3 affines**
(update `z`, reset `r`, candidate `h̃`). So **GRU at the same C/L/B is
already MAC-matched** on the hidden path. Do not widen GRU to “make up”
for a 4-gate LSTM that we do not have.

**MGU** (one forget/update gate + candidate) is 2 affines. Match hidden
MAC to 92c/3L/b=4 LSTM (768):

```
2L(C/B+1) + 2(L−1)C = 768   →   3L/B=4:  5.5 C + 6 = 768  →  C ≈ 138
```

Screen MGU **138c/3L/b=4** vs LSTM **92c/3L/b=4**, and a cheap pair
MGU **108c/3L/b=4** vs LSTM **72c/3L/b=4**. Tree head grows with `C·L`;
MGU pays more there. If MGU wins on bpb but blows us/byte, shrink cells
until us/byte matches, then re-read bpb (quality-at-matched-time).

**Implementation notes (agent1 copies only).**

- Keep aux=0, RMS-norm, Adam, block-diag on the *recurrent* factor, tree
  head, horizon=50, lr=0.03, initMul and forgetBias analogues.
- GRU candidate uses `r ⊙ h` *before* the recurrent multiply — the
  block-diag fast path still applies to `U_h`, not to the reset.
- Forget-bias lesson: GRU update-gate bias should be **swept**, not
  copied from LSTM fb=0. Start update-bias at 0.
- Do not implement peepholes, 4-gate LSTM, or layer-norm-with-mean.

**Protocol.** Code GRU layer in `work/agent1/src/`, wire a
`lstm_stand_gru.cpp`. First run: 72c/3L/b=4/fb=0 LSTM vs 72c/3L/b=4 GRU,
n=50000 (kill) then 200000. Then MGU 108c if GRU is within 0.02 bpb
(maybe the 3rd affine is wasted).

**Kill.** GRU/MGU within 0.01 bpb of LSTM at matched MAC on 200 KB →
CIFG-LSTM stays; the extra code is not worth S1 risk.
**Promote.** ≥0.02 bpb at 200 KB at matched us/byte → 3 MB after E30.

E30 says Wikipedia wants **faster state turnover**. GRU’s interpolating
update is a different stickiness profile than CIFG `c ← f⊙c + (1−f)⊙g`.
That is the actual bet.

---

### S5 — low-rank recurrence vs blocks=4

**Why this is not E27/E28.** E27–E28 chose **which sparsity pattern**
(block count) on a dense `C×C` recurrency. Low-rank replaces that matrix
with `U Vᵀ` (`C×r`, `C×r`). Every cell can mix with every cell through a
thin bottleneck; blocks **forbid** cross-block mixing.

Match **forward recurrent MACs** per gate to b=4: `2 C r = C² / B` →
`r = C / (2B)`.

| cells | B | rank r |
| ---: | ---: | ---: |
| 72 | 4 | 9 |
| 92 | 4 | 12 (use 11 or 12; 92/8=11.5) |

Keep the dense inter-layer path. Apply low-rank only where `MaskBlocks`
currently zeros weights (`output_size + j` for `j < C`).

**Protocol.** Implement in agent1 `lstm-layer-bd.cpp` copies. Compare
three arms at 72c/3L, n=200000, fb=0, initMul=0.5:

| arm | recurrent |
| --- | --- |
| A | blocks=4 (incumbent structure) |
| B | rank r=9, B=1 (low-rank replaces blocks) |
| C | rank r=6 **inside** each of 4 blocks (hybrid; optional) |

**Kill.** B and C ≥ A (low-rank does not beat the regulariser we already
have). Do not then sweep rank 4..32 — that is the E28 block-count
mistake in a different costume.
**Promote.** B beats A by ≥0.015 bpb → 3 MB at 92c with r=12, **or**
measure 92c standalone first (E28 transfer failure).

Backward of low-rank is `O(Cr)` instead of the dense C² transpose the
block path still pays. A bpb-neutral low-rank could still win on **time**
and buy cells. If bpb is tied within 0.01, compare us/byte and only then
consider a width increase — and that width increase is a *follow-up*,
not this screen.

---

## Explicitly out of scope (do not run)

- Width-only: 80c, 84c, 88c, 96c, 100c, 120c at 3L/b=4.
- Block-count rerun at fixed 100c.
- 1L vs 2L vs 3L at 96c / 160c (E23/E25).
- initMul at forgetBias=1.
- Negative forgetBias (E30b killed).
- Recompiling `btl_adam.cpp` / `lstm_stand_adam.exe`.
- `cmp_fb*.exe` or any 3 MB pipeline job.
- Horizon/lr sweeps (queued elsewhere as E31/E33; not architecture).

---

## Suggested order once the core is free

1. **S1** 50 KB: 72c/3L/fb=0 vs 64c/4L/fb=0. Then 56c/4L if needed.
2. **S2** 200 KB initMul grid at fb=0 (no code).
3. **S3** 8-param bit bias (tiny patch in agent1 `btl-bd.cpp`).
4. **S4** GRU at same 72c, then MGU at matched MAC.
5. **S5** low-rank r=9 vs b=4.

S2 and S3 are cheaper than S4/S5; they sit after S1 only because S1 is
the one experiment this agent was asked to run first and because E23’s
depth result is the strongest unused architectural axis.
