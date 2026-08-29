# FRONTIER — Agent 10 (director)

**Do not run compressors from this note. Do not repeat E25–E29 width/block/init sweeps.**

E30d/e **DONE — STOP**. MinGW E30e **517905 EXACT** (−190 B vs E30d 518095). Not the Linux lock. Do not start E32/E35/E41 or another 3 MB `cmp`.

---

**Strategic reset:** do **not** start E41, E35, or E32 on 3 MB. E41 is Class C. Forget-bias series **stopped** at E30e. **A2** cheap-filtered on enwik8: **killed as megabyte** (`A2.md`). Next A is a Linux post-WRT tail autopsy, then `INTEGRATION.md` tree head **with** SetInput inside cmix-lex.

---

## G1 — learning-rate sweep (standalone, after E41 is queued or killed)

Not another width point. `lr=0.03` is cmix’s default for a *different* LSTM.

**Protocol (standalone first; 3MB only if it survives):**

1. Freeze architecture: 72c/3L/b=4/initMul=0.5, horizon=50, tree-head SGD (not `TREE_ADAM` until G4).
2. `forgetBias` = **winner of E30d/e**, not the standalone guess. If E30e loses, sweep at `fb=1`. If it wins, sweep at `fb=0`.
3. 200 KB DIC, `lr ∈ {0.008, 0.015, 0.03, 0.05, 0.08}`. Locked reference is `lr=0.03` at the same fb.
4. If a non-0.03 value is ≥ **0.015 bpb** better at 200 KB, confirm 92c / 400 KB DIC (same two-scale check as E30b/c).
5. 3MB real pipeline only if the 400 KB gap is still ≥ **0.010 bpb**. Rank on archive bytes, never on standalone µs or projected hours.
6. Kill if 200 KB is non-monotonic noise (<0.010 bpb) or if 400 KB gap shrinks below 0.010. Do not “try it on 3MB anyway.”

**Why this beats the already-coded E31 (tree Adam) as the immediate next run:** E31 as written (`btl_adam.cpp` / `TREE_ADAM`) uses vanilla Adam (β1=0.9, β2=0.999, step = full `learning_rate_`) on the tree while gates use cmix Adam (β1=0.025, α = lr·0.1/√…). That is a confounded A/B. lr is the unconfounded scale knob and is orthogonal to E30.

**Do not start E32’s 3MB job.** E35 (L2 skip of LSTM p) is a different experiment: L2 mixers currently see LSTM only through already-mixed L1 outputs. fx2-cmix adds `stretch(lstmpr)/2` as a raw L2 input. That is a residual path, not E14 recalibration and not E32’s isMatch/bpos flags.

Coded: `work/src/fxcm26_slots.cpp` `-DLSTM_L2_INPUT=1` and `BtLstm::ExpectedByte` for E36. One axis, after E30d/e. Do not compose with E32 in the same binary until E35 reports.

`tools/next_standalone.ps1` currently runs Adam *before* lr. Reverse that: **lr first**.

---

## Scoring

Score = `(U × P) / C`.

- **U** = point estimate of 3MB archive gain (% vs 517,996) *if the idea is real*.
- **P** = P(realized gain ≥ ~0.3·U after a real-pipeline check).
- **C** = expected effort in **3MB-pipeline units** (one compress+roundtrip ≈ 1.0), including the probability-weighted confirmation run. Standalone-only ranking is treated as a *kill filter*, not a magnitude (E15/E23/E28).

No cell counts in {72,76,92,96,100,120} at b=4. No block counts. No initMul. No forgetBias grid after E30d/e reports.

---

## Five gaps (nobody has run these)

### G1 — LSTM `lr` at winning forgetBias  —  **score 0.133**  ← NEXT

| | |
|---|---|
| U | 0.08% (~400 B at 3MB; ~0.08% of S at enwik9 if it transfers) |
| P | 0.50 |
| C | 0.30 (5×200 KB @72c + optional 400 KB; pipeline only if it survives) |
| Class | LSTM hyperparam |

**Hypothesis.** Every verified LSTM change (dead-aux, tree head, b=4, initMul 0.5, possibly fb=0) rescaled gradients. Donor `lr=0.03` is untested here. After fb=0, forget-gate starts at σ(0)=0.5 rather than σ(1)≈0.73, so BPTT carries more gradient; 0.03 may be too large (same *class* of error as E26/E30’s “bigger memory / bigger init” stories).

**Not done:** EXPERIMENTS.md E33 is queued, zero rows. E20/E17 used 0.03 only.

**Kill tests.** Flat 200 KB curve; 400 KB gap <0.010 bpb; 3MB gain ≤ noise (~50 B).

---

### G2 — Tiny residual aux into the LSTM (fxcm → LSTM)  —  **score 0.080**

| | |
|---|---|
| U | 0.18% |
| P | 0.40 |
| C | 0.90 (must be real pipeline; mixer p does not exist in `lstm_stand`) |
| Class | **Architecture — not LSTM hyperparams** |

**Hypothesis.** E22 zeroed a 256-wide aux of *literal zeros* and won 3.9× speed. That does **not** measure aux. cmix’s LSTM is a residual expert: `SetInput` from the other models. This integration never calls it. E14: mixing the *same* (p,y) is capped at 0.136%; feeding fxcm’s belief into the LSTM is *new x* for the LSTM, not SSE on fxcm’s p.

**Spec (keep it tiny or E22’s cost comes back):**

- `auxiliary_input_size = 4` (not 256). Extra MACs ≈ 4 × cells × 3 gates × 3 layers — small vs recurrent.
- Aux vector, causal, already-decoded:  
  `(stretch(p_fxcm)/2048, match_len_scaled, lastCW/44515, word_type_or_isCode)`.
- Same 92c/3L/b=4/initMul=0.5 / winning fb / lr=0.03-or-G1-winner.
- Control: aux size 4 but values **all zero** (proves the *information*, not the extra fan-in). E4’s 0.039% mixer-capacity control is the template.

**Why this is the highest *non-hyperparam* lever.** The only verified real-regime gains are “different inductive bias.” Aux is how cmix actually uses that bias. Width/depth/blocks/init/fb do not give the LSTM fxcm’s residual.

**Kill tests.** Zero-aux control within 50 B of live aux; any config that blows the 42.48 h projection on *measured* 3MB µs/byte (no standalone extrapolation — E28).

**Do not confuse with E32 as coded.** `fxcm26_slots.cpp` writes slots 546–549 as `bp-2048`, `(bpos-3)*400`, `isMatch`, `c1>=0x80`. Those are mixer *inputs* derived from signals fxcm already uses as mixer *contexts*. That is E14-class, not this gap.

---

### G3 — BPTT horizon (cmix 100 vs our 50)  —  **score 0.070**

| | |
|---|---|
| U | 0.06% |
| P | 0.35 (partly overlapping E30’s memory-length story) |
| C | 0.30 |
| Class | LSTM hyperparam (free CPU) |

**Hypothesis.** E18: horizon does not change *amortized* cost (BPTT window / period cancels). We shipped horizon **50**; cmix’s LSTM is **100**. Never swept. fb=0 wants faster turnover → **shorter** (16/25) may beat 50; cmix-fidelity says **100**. Both sides are untested; that is the IG.

**Protocol.** 200 KB, 72c, winning fb, lr frozen: `horizon ∈ {16, 25, 50, 100}`. Confirm 400 KB only if |Δ| ≥ 0.015 bpb vs 50. RAM for tree rows is `horizon×8×hsize` — still negligible.

**Kill tests.** 16 and 100 both worse than 50; or 3MB gap <50 B. Do not spend 3MB on 100 if 200 KB already lost — 3L integration overhead is not the question here, quality is.

---

### G4 — Tree-head optimizer = gate Adam (E31, but not as checked in)  —  **score 0.056**

| | |
|---|---|
| U | 0.07% |
| P | 0.28 (coded path is confounded; P rises to ~0.40 if Adam is *matched*) |
| C | 0.35 |
| Class | LSTM optimizer (output head only) |

**Hypothesis.** Gates: cmix Adam. Tree: SGD (`LearnBit` else-branch). Rare tree nodes (MSB prefixes of rare DIC bytes) get few updates; Adam is the standard fix. Zero extra MACs.

**Required fix before calling it E31.** Copy the *gate* Adam (`lstm-layer-bd.cpp`: β1=0.025, β2=0.9999, α = lr·0.1/√(5e-5 t+1)) onto `tree_w_`. Do not A/B SGD against vanilla Adam at full 0.03 — that tests lr×optimizer together.

**Protocol.** After the matched implementation: 200 KB 72c fb=winner, SGD vs matched-Adam, same lr. Pipeline iff ≥0.015 bpb.

**Kill tests.** Matched Adam worse or within 0.010 bpb at 200 KB. Then delete `TREE_ADAM`; do not “tune β.”

---

### G5 — LSTM input alphabet: lastCW / word identity, not only the DIC byte  —  **score 0.042**

| | |
|---|---|
| U | 0.12% |
| P | 0.30 |
| C | 0.85 (vocab change + 3MB; lastCW lives in fxcm) |
| Class | **Architecture — not LSTM hyperparams** |

**Hypothesis.** E11: dict codes ≥0x80 are ~40% of DIC *bytes* and **69% of bits** at ~3.95 bits each. The residual is word *identity*. `BtLstm` is constructed with `vocab=256` and `Perceive(x.c0&0xff)` — one-hot of the encoded byte. fxcm already has `lastCW ∈ [0, 44515)` from `decodeCodeWord`. E19 put lastCW *buckets into the mixer* and died (+0.024%) because fxcm already has grammatical word types. The LSTM has **neither** lastCW nor word type. That is a different place to inject the same unused identity.

**Spec (pick one, don’t combine with G2 in the first A/B):**

- **G5a (preferred, cheap params):** keep vocab=256; set `input_symbol = lastCW & 255` on codewords and `c0` on literals (or `input_symbol = (c>=0x80) ? 128+(lastCW%128) : c`). Tests identity vs byte.
- **G5b:** vocab=512, `input_symbol = c | (isCode<<8)` — only a 1-bit flag; weaker, but standalone-testable on `dic200k.bin` without fxcm.

**Control.** Shuffle lastCW (permute codes) so cardinality is identical and information is destroyed. If shuffled ≈ live, kill (mixer-style capacity, not identity).

**Why not digits / kNN / TITLECAST.** Digit ceiling was already bounded (~0.4% oracle, never implemented) and E1.3 killed hot-spot special cases. kNN/retrieval is still untested but C≫1. TITLECAST/ordering died in the real regime (E10). G5 is the leftover *identity* hypothesis aimed at the model that actually moves bits.

**Kill tests.** G5b standalone <0.010 bpb; G5a 3MB ≤ E19 (+0.024%) after S1; shuffled control matches live.

---

## Rank table

| rank | gap | U | P | C | (U×P)/C | after E30, run? |
|---|---|---:|---:|---:|---:|---|
| 1 | G1 lr @ winning fb | 0.08% | 0.50 | 0.30 | **0.133** | **YES — next** |
| 2 | G2 tiny fxcm aux | 0.18% | 0.40 | 0.90 | **0.080** | after G1 (needs 3MB; don’t confound with lr) |
| 3 | G3 horizon 16/25/50/100 | 0.06% | 0.35 | 0.30 | **0.070** | same standalone night as G1 leftover cores |
| 4 | G4 matched tree Adam | 0.07% | 0.28 | 0.35 | **0.056** | only after Adam is matched to gates |
| 5 | G5 lastCW as LSTM symbol | 0.12% | 0.30 | 0.85 | **0.042** | after G2 or in parallel with G2 if 3MB is free |

G2 and G5 are the required non-hyperparam gaps. G1 is the highest *score* because C is a kill-filter sweep, not because it is the largest U.

---

## Explicitly do not run

| item | why |
|---|---|
| E25–E29 cell/block/init repeats (72/76/92/96/100/120, b=2/4/8, initMul) | Done. Width non-monotonic; b=4 won in-pipeline; standalone ranking lied for b=8. |
| 4-layer (E34 in `next_standalone.ps1`) | Depth axis already used (E23/E25). 3L integration overhead was +111 µs vs a 15 µs guess; 4L is likely OVER, not a new information source. Park until a cost win (G2-sized aux must not, skip-BPTT, or similar) reopens budget. |
| E32 as coded (slots 546–549 = linear p, bpos, isMatch, isCode) | E14-class / already mixer contexts. Do not burn a 3MB run. If slots are filled, fill with **G2-style new x** or **hidden probes** (below), not isMatch. |
| E35 L2 skip `stretch(bp)/2` | **Do run** after E30, one axis. Not E32. fx2-cmix L2 residual. |
| Forget-bias grid beyond E30d/e | Standalone already mapped −1…5; 3MB A/B is the only remaining measurement. |
| More SSE/APM/mixer-only recalibration | E14 oracle 0.136%. |
| Page-local, free order, anchored prefix, dict-code *mixer* buckets | Real-regime dead. |
| Standalone → Hutter-hour projections | Wrong five times, always optimistic (E25–E28). |

---

## Parked (not top-5, still legal later)

- **Skip-BPTT / gated learn** on high-confidence fxcm bits, to buy the already-measured **120c/3L/b=4 = 517,464 (+0.716%, 53.9 h OVER)**. That is a budget conversion, not a width search. Run only if G1–G3 are flat *and* 3MB µs/byte is trusted. First: 92c standalone with 30% of `LearnBit`/Backward skipped; if bpb holds, then 120c pipeline.
- **Hidden-state mixer readouts** (8–14 unused slots 546–559 ← linear probes of `hidden_`, not isMatch). E14 does *not* bound this (new features). Cheaper than G2 but likely overlapping G2/G1. Do after G1.
- Digit/record specialist: ceiling quoted ~0.4%, never implemented; E1.3 still applies. Only if G2/G5 die.
- Port of one cmix expert (PPMD/DMC/IndirectHash) to close the ~10% gap to cmix-lex: strategic fork, not this campaign’s next 3MB.

---

## Incumbent / in-flight (do not relitigate)

| | |
|---|---|
| Locked | 517,996 · 92c/3L/b=4/initMul=0.5/fb=1 · 38.5 h proj · 3.9 h margin · MD5 a52a41bd426904afcc48d1b9a99c8f1d |
| Best in-budget verified | 100c same stack 517,942 (+0.625%) · 42.2 h · 0.28 h margin — E29 still prefers 92c for headroom |
| Over-budget quality | 120c 517,464 (+0.716%, 53.9 h) |
| E30 standalone | fb=0 strictly best; gap shrinks 200→400 KB (0.044→0.030 bpb) but does not vanish |
| Ledger | campaign_start LOCKED_FALLBACK; agent1 PROMISING standalone 2.9469 vs 2.9767 @400 KB |

If E30e (fb=0) wins 3MB by ≥100 B and roundtrip is exact, lock it and run **G1 at fb=0**. If it loses or is within noise, keep fb=1 and still run **G1 at fb=1** — lr is untested in both worlds.

Agent 7 γ-gap identity cache vs unigram: **KILLED** (see `work/agent7/IDENTITY.md`). Do not spend 3MB on it.

