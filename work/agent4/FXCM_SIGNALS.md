# AGENT 4 — FXCM↔LSTM signal archaeology

Read-only audit of `work/src/fxcm26_bd92.cpp` (+ `btl-bd.cpp`, `lstm-layer-bd.cpp`, `locked/PROVENANCE.md`, `log/RESEARCH_LOG.md`).  
Sibling draft already exists: `work/src/fxcm26_slots.cpp` (fills 546–549).  
Do **not** treat this as a green light to edit `work/src` — notes only.

---

## Architecture snapshot (locked glue)

| Piece | Where | Behavior |
|---|---|---|
| Mixer width | `Inputs::add` / `PredictorInit` | Models `add()` into `n[0..]`. `N` forced to **560** (`ncount=560` at init; reset to 0 each bit in `update`). |
| SIMD rule | `Mixer1::dot_product` ~539–546 | `assert(n == ((n+15)&-16))` — N must be multiple of 16. |
| LSTM → mixer | ~5510–5512 | Direct write (bypasses `add` / `AddPrediction`): `n[544]=clp(stretch(bp))`, `n[545]=clp(stretch((bp+2048)>>1))`. |
| Zero pad | `PredictorInit` ~3657–3658 | `for(i=544;i<560;i++) n[i]=0` once; **546–559 stay zero forever**. |
| LSTM input | `BtLstm::Perceive` / `Advance` | Previous **byte as one-hot** via `weights_[i][input_symbol]` only. `auxiliary_input_size=0` (E22). |
| LSTM learn | `update()` ~5543–5548 | `btLearn(c0,y)` every bit; `Perceive(byte)` on byte boundary. |

Original fxcm mixer width was **544**. Adding 2 LSTM slots → 546 → pad to **560**.  
`544` alone is already divisible by 16 — the pad exists only because of the +2.

---

## Findings

### 1. Values computed then discarded (not fed to mixer **or** LSTM)

| Signal | Site | Fate |
|---|---|---|
| `wasVerb` / `wasNoun` / `wasVerbH` / `wasNounH` | set ~4817–4818, cleared ~4518–4547 | **Never read** for any CM/mixer/LSTM input |
| `wt3b` | decl ~3518 | **Never used** |
| `wt3cxtW1` | written ~4379 | **Never read** (`wt3cxtW` / `wt4cxtW1` are used; this twin is dead) |
| `WordsContext::{codesum,ftype,worInPar,worInLink}` | Update ~1901–1904 | Maintained, **never read** (SimilarSentence uses a *local* `codesum`) |
| `CodeR()`, `LastIdx()` | ~1943, ~1977 | Defined, **never called** |
| `StemmerEN.Stem` return `res` | ~4108 | Discarded; only Type/Hash side effects used |
| Non-best `matchCandidates[i]` | MatchModel2mix ~3998–4002 | Only **best** length/expectedByte → mixer; other candidates’ bytes unused as soft features |
| `mp0..mp3` | ~5622–5632 | Used by `mmmO[]` APM cascade **after** `modelPrediction`; **LSTM never sees** (and can’t on the same bit) |
| LSTM `bp` | ~5510–5512 | Written to `mxInputs1` only — **not** into `model_predictions1` (bypass `AddPrediction`), so `mxA2` does not see LSTM at slots 544/545; those `model_predictions1` indices get later APM `AddPrediction`s instead |

### 2. Dead / near-dead computation still paid for

- **14 permanent zero mixer inputs** `n[546..559]`: every `mxA[0..17].p1()`/`update` dots/trains width 560 → **14×18×(dot+train) zero multiplies per bit**. This is the remaining “multiply by zeros” analogue after E22 killed the 256-wide LSTM aux.
- **Collinear LSTM pair** at 544/545: `stretch(bp)` vs `stretch((bp+2048)>>1)` ≈ stretch of midpoint toward ½. Second slot adds almost no new information.
- `AddPrediction((64))` ~5383: constant bias into `model_predictions1` (intentional; not dead, but fixed).
- `mxA1[1]` context stuck at 0 (`// mxA1[1].cxt=0` ~5387): mixer still runs, context bank size 1.

### 3. Unused fields / latent predictors

Latent (computed, never consumed): `wasVerbH`, `wasNounH`, `wasVerb`, `wasNoun`, `wt3b`, `wt3cxtW1`, `WordsContext` counters above, `CodeR`/`LastIdx`.

Stem / word-type machinery **is** live for fxcm CMs/mixers (`worcxt.*`, `lastWT`, `oldwt1`, `deccode`/`lastCW` → `mxA[8]`), but **opaque to the LSTM**.

### 4. MatchModel outputs LSTM never sees

From `MatchModel2mix` (~3991–4041):

| Output | Goes to mixer? | Goes to LSTM? |
|---|---|---|
| `length` (raw) | Yes: `sign*(length<<5)` ~4019; also drives `isMatch` / skipM1 | **No** |
| `denselength` 0..27 | Yes: via `smA[0]` ctx ~4016 | **No** |
| `expectedByte` / `expectedBit` | Yes: `smA[1]`, delta `smA[2]` | **No** |
| delta flag | Yes: ctx[2] | **No** |
| `isMatch` (=length) | Mixer **contexts** (`mxA[4]`,`mxA[7]`) + CM `sets()` gates | **No** |

LSTM only observes match structure indirectly if it later helps predict the next *byte* — it never gets an explicit match feature.

### 5. Word type / lastCW / stem — LSTM blind spot

LSTM `Perceive(prev_byte)` / one-hot `input_symbol` only (~btl-bd `ForwardPass`).

Fxcm already has, for mixers/CMs only:

- `lastCW` / `deccode` → `mxA[8].cxt` ~5501  
- `lastWT` (nibbles from `getWT`) → `mxA[9]` ~5502  
- `oldwt1=getWT3(...)` → `mxA[12]` ~5505  
- Stem hashes via `worcxt.Word` / `(*pWord).Hash` in many `cmC*.set`  
- `wt3cxt` / `wt3cxtW` / `wt4cxtW1` as CM hashes  

**None** of these enter `layer_input_` (aux size 0).

### 6. Shrink ncount vs fill 546–559

| Option | CPU | Quality risk | Verdict |
|---|---|---|---|
| **Fill 546–559** with real shorts | ≈ **0** (already paying zero MACs) | Low if signals non-collinear | **Preferred** |
| Shrink N **560→544** and **drop** LSTM | Saves ~16/560 ≈ 2.9% mixer SIMD | Lose LSTM gain (~0.6%) | Bad |
| Shrink N→544 by **overwriting** two model slots with LSTM | Same ~2.9% save | Lose those two model channels | Only if those channels are weak |
| N=548 (544+2, no pad) | Illegal (not ÷16) | — | Impossible without changing SIMD |

**Filling beats shrinking** unless you are mixer-SIMD bound *and* can prove two of the original 544 are worthless.

### 7. Compact LSTM aux vs mixer slots

| | Mixer slots 546–559 | LSTM `auxiliary_input_size=K` |
|---|---|---|
| When paid | Every **bit** × 18 mixers | Once per **byte** (Advance/BPTT) |
| Marginal CPU | ~0 if replacing zeros | Roughly `K / (1+2·cells)` on dense gate path × 3 gates × 3 layers ≈ **~5–10% of LSTM** for K=4..8 @ 92c/3L |
| Best for | Bit-local soft evidence (`isMatch`, `expectedBit`, `bpos`, stretch leftovers) | Byte-local semantics (`lastCW`, word type, stem hash bits, match length) that should shape **hidden state** |
| Redundancy vs fxcm | Mixer **contexts** already hash many of these; soft **inputs** are a different path (all weight banks see the same vector) | Recurrent conditioning ≠ context bank select — complementary if compact |

E22 removed aux=256 zeros (huge win). Reintroducing **small** K is not repeating that bug if every aux dim is nonzero and informative.

**Recommendation:** fill mixer zeros first (free); then try K∈{4,8} byte-level aux if margin remains.

### 8. Remaining “256× zeros” analogues

1. **Mixer `n[546..559]`** — 14 zeros × 18 mixers × 8 bits/byte (primary leftover).  
2. **Off-block recurrent weights** — masked to 0 and **skipped** in block-diagonal forward/backward (`lstm-layer-bd.cpp` ~118–128, ~225–236) — already fixed, not a cost.  
3. **`auxiliary_input_size=0`** — fixed in E22; do not regress to 256.  
4. Collinear slot 545 ≈ soft zero information (weights thrash on duplicate).

---

## Ranked patch proposals (smallest change first)

### P1 — Fill zero mixer slots 546–559 (bit-level soft features)
**Change:** After LSTM writes (~5510), assign non-zero shorts into `n[546..559]` (draft already in `fxcm26_slots.cpp` 5513–5516).  
**Suggested fills (prefer orthogonal to existing CM hashes):**

| Slot | Proposal | Why not redundant |
|---|---|---|
| 546 | `clp(bp-2048)` | Linear LSTM logit; 544/545 are stretched/nonlinear |
| 547 | `clp((bpos-3)*400)` | Bit position soft; mixers use bpos mostly inside **contexts** |
| 548 | `isMatch?2047:-2047` | Soft presence; cxt uses binary flags / length buckets |
| 549 | UTF-8 / high-bit flag on `c1` | Coarse script signal |
| 550 | `clp(min(length,63)<<5)` or denselength×scale | Continuous match strength (length already one channel from MatchModel; denselength is different scale) |
| 551 | `expectedBit?2047:-2047` | Explicit match bit guess (smA sees it via ctx, not as a global input) |
| 552 | `skipM1?2047:-2047` | Reflects aggressive CM suppression state |
| 553 | `clp((int)(lastWT&15)*128-1024)` | Current word-type nibble as soft input (mxA[9] only as cxt) |
| 554–559 | `wasVerb`/`wasNoun` flags, `isParagraph`, `FcIdx` soft, `delta` match mode, lagged `mp0` (prev bit) | Activate dead latents / post-mixer lag |

**CPU:** ≈0. **Risk:** collinearity with MatchModel’s existing 7 mixer adds — start with slots.cpp’s 4, A/B the rest.  
**Refs:** `fxcm26_bd92.cpp:3657-3658,5510-5512`; draft `fxcm26_slots.cpp:5510-5516`.

### P2 — Replace collinear LSTM slot 545
**Change:** Keep `n[544]=clp(stretch(bp))`; replace `n[545]=clp(stretch((bp+2048)>>1))` with match length or `expectedBit` soft feature.  
**CPU:** 0. **Why:** second LSTM transform is near-duplicate; frees a paid slot without growing N.  
**Refs:** `fxcm26_bd92.cpp:5510-5512`, MatchModel `4019-4025`.

### P3 — Consume dead `wasVerbH` / `wasNounH` (or boolean flags)
**Change:** Pipe already-updated `wasVerb`/`wasNoun` (or low bits of hashes) into spare mixer slots or one cheap `cmC*.set`.  
**CPU:** negligible (values already computed ~4817–4818).  
**Why:** pure latent today; verb/noun-seen-in-sentence is only weakly present via other type hashes.  
**Refs:** `fxcm26_bd92.cpp:3496-3499,4817-4818` (writes); no readers.

### P4 — Compact LSTM aux (K=4..8), byte-level
**Change:** Restore small `auxiliary_input_size=K` in `BtLstm`/`LstmLayer`; fill at `Advance`/`Perceive` with e.g.  
`{ denselength/27, isMatch?1:0, getWT(Type)/15, lastCW low bits or deccode flag, isParagraph, FcIdx/7, ... }`.  
**CPU:** ~5–10% of LSTM path (far below old 256-zero tax).  
**Why not redundant:** mixer contexts select weight rows; aux conditions **recurrent hidden** across the byte. LSTM currently cannot represent “in a long match / after a verb / dict codeword class” except by hoping the byte stream implies it.  
**Refs:** `btl-bd.cpp:17-29,77-90`; `lstm-layer-bd.cpp:42-54,108-128`; PROVENANCE E22; FRONTIER item 4.

### P5 — Optional shrink N→544 only after P1 proves two slots useless
**Change:** If profiler shows mixer SIMD hot and ablation shows two of {original 544 + pad} ≈0 weight magnitude, set `num_models`/`ncount`/alloc to 544 and place LSTM at 542/543 (or drop pad by merging LSTM into last two live channels).  
**CPU:** ~2.9% mixer width. **Why last:** filling zeros is strictly better until proven otherwise.  
**Refs:** `fxcm26_bd92.cpp:79,163-193,539-546,3657-3674,5510-5512,5832`.

---

## Top 5 patch ideas (file:line)

1. **Fill `n[546..559]` with match/bit/type soft features** — `work/src/fxcm26_bd92.cpp:3657-3658` (zeros), `:5510-5512` (insert after LSTM); draft `: work/src/fxcm26_slots.cpp:5513-5516`. Free CPU; kills remaining zero-multiplies.

2. **Replace collinear `n[545]`** — `fxcm26_bd92.cpp:5511-5512` (`stretch((bp+2048)>>1)` → match/`expectedBit`). Zero size delta.

3. **Wire dead `wasVerb`/`wasNoun`/`wasVerbH`/`wasNounH`** — produced `fxcm26_bd92.cpp:4817-4818`, unused; feed into P1 slots or a CM `set`.

4. **LSTM compact aux (lastCW / getWT / match length)** — `btl-bd.cpp:17-29` (aux=0 today), `lstm-layer-bd.cpp:42-54`; fill in `Advance` `btl-bd.cpp:77-90`. Complements mixer contexts; LSTM is blind to these.

5. **Lag-1 `mp0..mp3` or match `denselength` into mixer/LSTM** — computed `fxcm26_bd92.cpp:4009-4025` (match) and `:5622-5632` (mp*); never seen by LSTM; mp* are post-mixer so only previous-bit lag is causal for same-bit predict.

---

## Explicit non-goals / traps

- Do **not** restore `auxiliary_input_size=256` (E22).  
- Do **not** run compressors from this agent.  
- Shrinking below 560 without relocating LSTM **removes** the LSTM mixer channels.  
- `isMatch` in mixer **context** ≠ soft `isMatch` in mixer **input** ≠ LSTM aux; all three are different inductive biases.
