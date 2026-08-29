# Forget-bias red team (E30 / E30b / E30c)

**Claim under attack.** Standalone `lstm_stand` says forget-gate last-weight init `0` beats cmix default `1`: 72c/200KB 3.086 vs 3.134 bpb; 92c/200KB 3.060 vs 3.105; 92c/400KB 2.947 vs 2.977. Negatives overshoot. Gap 0.044 → 0.030 from 200KB to 400KB. Therefore ship `FORGET_BIAS=0`.

**Verdict in one line.** Do not accept from standalone. **Run the 3MB pipeline** as a paired MinGW (or, for a lock, Linux) A/B. Kill only if that A/B misses the byte gate below.

Logs used: `log/e30_forget_bias.txt`, `log/e30b_forget_neg.txt`, `log/e30c_400k.txt`, `log/RESEARCH_LOG.md` E14–E16, E28–E30. No 3MB fxcm was run by this agent.

---

## 1. Harness vs fxcm: bit order / `Perceive(0)` — attack fails

`tools/lstm_stand.cpp` and `work/src/fxcm26_bd92.cpp` implement the same byte/bit protocol.

| Step | `lstm_stand` | fxcm `btPredict` / `btLearn` / `Perceive` |
|---|---|---|
| Init | `BtLstm(256, cells, 3, 50, 0.03, 10); Perceive(0)` | `btInit`: same ctor, `g_btCells=92`, `Perceive(0)` |
| Partial byte | `c0 = 1`, then `c0 = (c0<<1)\|bit` | `x.c0 = 1`, then `x.c0 += x.c0 + x.y` |
| Bit order | `for k=7..0: bit = (c>>k)&1` | `compress`: `for i=7..0: code((c>>i)&1)` — MSB first |
| Predict node | `PBit(c0)` before the bit | `btPredict((U32)c0)` with `const int c0=x.c0` |
| Learn node | `LearnBit(c0, bit, p)` then shift `c0` | `btLearn(x.c0, x.y)` **then** `x.c0 += x.c0+x.y` |
| End of byte | `Perceive(c)` | when `x.c0>=256`: `Perceive(x.c0&0xff)` |

`Perceive(0)` is the cmix dummy: `epoch_==0` runs BPTT on zero `bit_err_`, then `Advance(0)`. First real bits are predicted from a hidden state that has already ingested symbol 0. Both programs do this.

`LearnBit` uses the LSTM’s own clamped float `p` in both places (`g_btP` in fxcm, not the mixer’s `p`). Tree index is fxcm’s leading-1 `c0` in `1..255`. `TREE_ADAM` is off in the E30 binary (`btl_adam.cpp` is a separate experiment).

**What does not match (metric, not protocol):**

- Standalone scores **LSTM self-CE** (float `p`, 1e-6 clamp). The pipeline scores **mixed + stretched 12-bit `bp`**, then 18 mixers + APM. `btPredict` quantizes `p*4096` for slots 544/545 only; LSTM weights still train on the float.
- Standalone calls `srand(0)`. fxcm **never calls `srand`**. See §2.
- 14 mixer slots 546–559 stay zero (`ncount` 544→560 for SIMD alignment). Harmless to the protocol; relevant to mixing (§4).

**Falsifier for this attack.** A traced first-byte `c0` sequence that is not `1, 2+b7, 4+…` MSB-first, or a `Perceive` of something other than the completed byte after bit 8. Source does not show that.

The 0.03–0.05 bpb tables are **not** a bit-order or `Perceive(0)` artifact. They are LSTM-only CE on DIC prefixes.

---

## 2. `srand(0)` + forget=0 vs forget=1 — not a split Xavier draw; still a one-seed result

Init in `lstm-layer-bd.cpp`:

```text
for each cell:
  for each weight j:  forget/input/output[j] = Xavier via Rand()
  forget_gate.weights[i][last] = g_forgetBias   // overwrite after the draw
```

The last forget weight still **consumes** a `rand()` call, then is replaced. Forget=0 and forget=1 therefore share **identical** Xavier tensors except that one slot. This is not “lucky seed for 0 vs unlucky seed for 1” **within a single `srand`**.

What remains:

1. **Only one seed was swept.** Monotonicity 0 < 0.25 < 0.5 < 1 < … < 5 and negatives worse than 0 is strong *at that seed*. It does not prove seed 1, MinGW LCG, or glibc `random()`.
2. **Standalone seed ≠ pipeline seed on this machine.** ISO C: `rand()` before `srand` ≡ `srand(1)`. MSVCRT/MinGW: `srand(0)` ≠ `srand(1)`, `RAND_MAX=32767`. E30 standalone is seed **0**; MinGW fxcm is seed **1**.
3. **Linux accidentally collapses the mismatch.** glibc `__srandom_r` maps seed `0` → `1`. Xeon standalone `srand(0)` ≈ pipeline default. Windows E30 numbers are **not** the Linux pipeline draw.
4. **72c / bias=1.0 = 3.1343 is not in `e30_forget_bias.txt`** (that file skips 1.0). E27 was 3.1306 on Xeon. Δ = 0.0037 bpb ≈ 12% of the 400KB gap — already “same harness, different box” noise.

**Falsifier.** Same binary, `srand(1)` and one other seed (e.g. 2), 92c/200KB: if forget=0 does not beat forget=1 on **both**, treat E30 as seed-specific and do not ship. Cheap; optional if the 3MB paired run is happening anyway.

---

## 3. Gap shrinking with scale — kills naive 0.03→archive conversion; does not prove the 3MB gain is zero

Measured LSTM-only bit savings (from log files):

| N (DIC bytes) | cells | C_bits = bits(1)−bits(0) | avg gap (bpb) | LSTM-only bytes |
|---|---:|---:|---:|---:|
| 200,000 | 92 | 8,869 | 0.0443 | 1,109 |
| 400,000 | 92 | 11,926 | 0.0298 | 1,491 |

Incremental CE on the second 200KB: (11926−8869)/200000 = **0.0153 bpb**, about half the 400KB *average*. That is an **init-wash** signature, not a stable architecture gap.

Mechanism (source): last weight is the layer-input bias (`input[last]=1`). RMS-norm is `f / rms(f)` — **no mean subtract** — then `gamma`/`beta`, then sigmoid. Uniform +1 on every cell does *not* get centered out, but it **does** get rescaled; `beta` is trained and can absorb a post-norm offset. Adam still updates that last weight after `update_limit_=3000` (~150KB of BPTT steps) at a frozen nonzero α. So bias=1 vs 0 is primarily **early-file prior**, which matches a shrinking average gap.

Two-point extrapolation of *average* gap is unidentified:

| Model | implied avg gap at 1,814,514 DIC B | LSTM-only bytes if 100% transferred |
|---|---:|---:|
| 1/√N from 200KB | ~0.015 | ~3.3 KB |
| linear in log N (gap −0.0145 / doubling) | ~0 or slightly negative | ~0 |
| saturate `C_bits` (pure prefix init) | — | ~1.5–2 KB (integral, not avg) |

E28 is the prior that matters: **standalone block-count ranking reversed in the 3MB pipeline** (b=8 won 200KB, lost to b=4 at 3MB).

Prefix integral still exists even if later instantaneous gap → 0: first 200KB alone is 8,869 LSTM bits ≈ 1.1 KB LSTM-only. Mixer will not keep all of that (§4). Shrinking **does not** imply the 3MB *archive* delta is 0; it **does** imply you must not write `0.030 × 1.814e6 / 8 ≈ 6.8 KB` on a slide.

**Falsifier for “gain vanishes.”** Paired 3MB archive(forget=0) ≥ archive(forget=1) (no win).  
**Falsifier for “0.03 survives as 0.03.”** Any pipeline delta ≪ 0.03 × 1.814e6 / 8.

---

## 4. Mixer / calibration ceiling — attenuates; does not zero a real LSTM change

Slots 544/545 are two stretched copies of the same 12-bit LSTM `p` among **560** `mxInputs1` entries (544 live CMs + 2 LSTM + 14 structural zeros). Mixers init **every** weight to 129. Zeros do not move the dot product (tx=0); they are not a dilution mechanism. LSTM starts as 2/544 of the unnormalized mix and can be upweighted.

E14 “calibration ceiling” (≤0.136% ≈ 700 B on the 521,198 baseline) is **reweighting the same experts**. Forget=0 changes LSTM *dynamics*, not mixer algebra. Wrong object.

E15–E16: a weak online LSTM still moved the real pipeline (64c 519,263; 128c 518,320 vs 521,198). Offline 2-input mixers **understated** LSTM value (~6×). Mixer does not ignore the LSTM.

E28: standalone **ranking** of LSTM hyperparameters can still flip once CMs+APM see the file.

Quantization: many bits may not even change `int(p*4096)` if the CE gap is many tiny p-shifts. Another attenuator.

**Best red-team prior:** 10–30% of LSTM-only *integral* bits appear in the archive; 0% (flip) is possible; 100% is fantasy. That maps the 400KB 1.5 KB LSTM-only saving to roughly **150–450 B** at 3MB if the integral plateaus, or **0 B** if E28-style reversal happens.

A *better* LSTM would not make the mixer ignore the difference; it would make the mixer **use it more**, with heavy attenuation and possible non-monotonicity.

**Falsifier.** Pipeline delta near the LSTM-only conversion of 0.03 bpb (~6.8 KB) — that would mean the mixer is *not* a ceiling. Pipeline delta ≤ 0 with a clearly better standalone LSTM — mixer/path-dependence ceiling wins.

---

## 5. MinGW vs Linux 517,996 — even forget=1 is not the lock

Locked 517,996 is **Linux Xeon**, `locked/BUILD.sh`: `g++ -O3 -march=native -ffast-math -DUNIX`, glibc `rand` (`RAND_MAX` 2³¹−1). Provenance: 92c/3L/b=4/initMul=0.5, 3 MB enwik8 prefix, DIC 3,000,000 → 1,814,514.

This box: MinGW/MSVC `rand`, `RAND_MAX=32767`, no `srand` in fxcm, different `-march`/`-ffast-math`. Xavier is a different sequence. Fast-math + valarray order can move the arithmetic coder.

**Implication.** A MinGW forget=0 archive must **not** be compared to 517,996 as if that were the control. E30d (forget=1, same compiler, same flags, same DIC) is the only valid control on this machine. If E30d ≠ 517,996, that is expected, not a reason to skip E30e; it is a reason **not to lock** from MinGW numbers.

If E30d is hundreds of bytes off 517,996, a 50–100 B MinGW win for forget=0 can still **lose to the Linux lock**. Replacing the lock requires the **lock toolchain** (Linux `BUILD.sh`), not a Windows delta.

**Falsifier for “MinGW is interchangeable.”** |E30d − 517996| ≤ 20 B. Then MinGW paired deltas can be read against the lock. Until that happens, they cannot.

---

## What would falsify the *hypothesis* (forget=0 is better)

1. **Protocol bug:** bit-order / `c0` / `Perceive` mismatch — **not seen**.
2. **Seed:** forget=0 loses at `srand(1)` or a second seed at 92c/200KB.
3. **Pipeline A/B:** same binary family, forget=0 archive ≥ forget=1 archive on the 3MB DIC slice.
4. **Lock-relevant A/B:** Linux `BUILD.sh` forget=0 does not beat Linux forget=1 by the byte gate, even if MinGW looked good.
5. **Reversal with scale:** 3MB paired delta ≤ 0 while 200/400KB standalone still favors 0 (E28 class).

Negatives overshooting 0 is **consistent** with a real optimum at 0 at seed 0; it does not prove 3MB transfer.

---

## What the 3MB test must show

Run **E30d and E30e as a pair** (forget=1 vs 0), identical compiler flags, identical `english.dic` / DIC output, no other diffs (`lstm_forget1.cpp` vs `lstm_forget0.cpp` only).

Must report:

- Archive bytes both ways, and **paired delta**.
- E30d vs 517,996 (toolchain gap).
- Roundtrip byte-exact for any candidate you would lock.
- ctime; forget=0 is supposed to be free — flag any unexpected slowdown.

Do **not** report “vs 517,996” as the E30e result unless E30d matched 517,996 or the run is on the lock toolchain.

Optional cheap add-on (not a substitute): 92c/200KB `lstm_stand` at `srand(1)`.

---

## Is 0.03 bpb noise?

**As LSTM-only CE at 400KB, seed 0:** no. 11,926 bits, monotonic bias sweep, 72c and 92c same direction. Not a 1-run fluke of the CE estimator.

**As a 3MB *pipeline* forecast:** yes — treat 0.03 bpb as **non-transferable units**. Conversion to archive bytes without mixer/scale/seed/toolchain is advertising. E28 already showed standalone hyperparameter rank can flip. The 0.0037 bpb Xeon vs this-box 72c/bias=1 discrepancy is the same order as a small slice of the 0.030 gap.

Use 0.03 only as **justification to spend one 3MB pair**, not as an expected −6.8 KB.

---

## Recommended acceptance threshold (BYTES, 3MB slice)

DIC stream is 1,814,514 bytes; lock is 517,996.

**Gate A — screen (this machine, paired):** accept forget=0 as “interesting” only if

```text
archive(forget=0) ≤ archive(forget=1) − 100
```

on the same MinGW (or same Linux) build. **100 B** is ~3× the 92c vs 96c gap (30 B) and ~2× 92c vs 100c (54 B), those being real same-machine model moves. It sits at the low end of “10% of a plateaued LSTM-only integral.” Smaller than 100 B: real-looking mixer weather — do not change the lock. CPU is identical, so this is not a runtime trade; it is a **false-positive** bound.

**Gate B — replace the lock:**

```text
archive(forget=0) ≤ 517996 − 100
```

measured with **`locked/BUILD.sh` on Linux** (the provenance toolchain). MinGW Gate A alone is insufficient if |E30d − 517996| > 20.

If Gate A passes and Gate B is not run, keep forget=0 as a **queued Linux patch**, not as LOCKED_FALLBACK.

If Gate A fails (delta > −100 B, including any loss): **kill** forget=0. Standalone 0.03 bpb is then classified as non-transfer.

---

## One-paragraph verdict

**Run 3MB; do not kill; do not accept from standalone.** Bit-order, `c0` tree nodes, `LearnBit` timing, and `Perceive(0)` match fxcm, so E30 is not a harness lie. Forget=0 vs 1 is a clean last-weight overwrite on a shared Xavier stream, but it is one seed, and on MinGW that seed is not even the pipeline’s `srand(1)`. The 0.044→0.030 shrink plus trainable `beta`/last weight says most of the CE is an early-file init prior; two scale points cannot tell 1/√N leftover from a log-linear vanish, and E28 already reversed a standalone LSTM ranking in this pipeline. The mixer will attenuate, not ignore, a real LSTM change; 0.03 bpb is not 6.8 KB. MinGW forget=1 is not 517,996 until proven. Spend the paired E30d/E30e run; ship only if forget=0 wins by **≥100 bytes** on that pair, and only lock it if the Linux binary also beats **517,996 by ≥100 bytes**.
