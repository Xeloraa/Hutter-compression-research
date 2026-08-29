# A1 — tree-head LSTM inside cmix-lex (Linux patch spec)

Not a record. Not a 3 MB number. This file is the splice spec for a
**Linux** A/B: stock cmix-lex softmax LSTM vs the same net with only the
output head replaced by a binary tree. Sources were fetched 2026-08-29
**outside** this repo (`C:\Users\vivi\hutter-refs\`, not vendored):

| tree | HEAD | LSTM constructor |
|---|---|---|
| [byronknoll/cmix](https://github.com/byronknoll/cmix) | `1d95fe9` | `Lstm(vocab, vocab, 200, 2, 100, 0.03, 10)` — `src/mixer/lstm.cpp` |
| [kaitz/fx2-cmix](https://github.com/kaitz/fx2-cmix) | `04c5806` | `Lstm(vocab, vocab, **200, 1, 128**, 0.03, 10)` — `src/predictor.cpp:132` |
| [blahem/cmix-lex](https://github.com/blahem/cmix-lex) | `370e698` | `Lstm(vocab, vocab, **170, 1, 128**, 0.03, 10)` — `src/predictor.cpp:145` |

**Base fork is cmix-lex.** It already has `fxcm_v26`, shipped article order,
PPMD, and `payload_lex`. fx2 is the paid record (S=110,793,128) if lex is
rejected. Do not vendor either tree into this repo.

---

## What the softmax ByteModel actually is

Call chain (cmix-lex = fx2 here except cell count):

1. `Predictor::AddMixers` constructs
   `ByteMixer(1, bit_context, vocab, vocab_size, new Lstm(vocab_size, vocab_size, CELLS, 1, 128, 0.03, 10))`.
2. Each completed byte, `Predictor::Perceive` does
   `byte_model_->BytePredict()` (PPMD, 256-way) →
   `byte_mixer_->SetInput(j, p[j])` for `j=0..255`.
3. `ByteMixer::ByteUpdate` (`src/mixer/byte-mixer.cpp:22`):
   - `inputs_ *= 2 / num_models_` (here `num_models_=1`)
   - **`lstm_->SetInput(inputs_)`** — residual vector of length `vocab_size`
   - `lstm_->Perceive(byte_map_[byte_])` — `byte_map_` remaps the raw byte
     onto the compact vocab index
   - scatter LSTM `output[offset]` back onto `probs_[0..255]`; unused vocab
     slots stay 0
   - `ByteModel::ByteUpdate()` zeros `!vocab_`
4. Every bit, `byte_mixer_->Predict()` (`src/models/byte-model.cpp:8`)
   sums the remaining softmax mass to get P(next bit). **`ex`** = argmax of
   `probs_[bot_..top_]` (not a greedy bit walk).
5. `lstmpr = Discretize(byte_mixer_output)`, `lstmex = byte_mixer_->ex`
   (`src/predictor.cpp:333-334`).

`Lstm::SetInput` (`src/mixer/lstm.hpp:78`) copies that vector into
`layer_input_[epoch_][i][0:input_size_]`. Layer ctor
(`lstm.hpp:27`) is

```text
layers_.emplace_back(layer_input_[0][i].size() + output_size,  // one-hot + aux
                     input_size_,                              // aux width = vocab
                     output_size_,                             // one-hot alphabet
                     num_cells, horizon, clip, lr);
```

`LstmLayer::ForwardPass` (`lstm-layer.hpp:112`) adds **dense aux**
`input[j] * weights[output_size_ + j]` plus a **one-hot** lookup
`weights[input_symbol]`. That aux path is the whole point of the mixer LSTM.

Softmax head (`Lstm::Predict` `lstm.hpp:137-144`):

```text
for i in 0 .. output_size_-1:     # vocab_size, typically ~256
    output[i] = exp(hidden · output_layer_[epoch][i])
output /= sum(output)
```

`output_layer_` shape: `horizon × output_size × (num_cells×num_layers+1)`.
BPTT (`Perceive` `lstm.hpp:94-101`) backprops **all** `output_size` softmax
errors into `hidden_error_`. Online update (`lstm.hpp:113-119`) is SGD on
every softmax row.

`lstmex` in **fx2** is live: `fxcmv1.cpp:4661`
`mxA[9].cxt = (bpos<<8)*4 + (fails&3)*256 + lstmex` and
`stretch(lstmpr)` on L1/L2. In **cmix-lex** `fxcm_v26`, `lstmex`/`lstmpr`
are still assigned but **not read** (`extern` only; mixer 9 is
`lastWT`/`stream3bR`). The outer cmix mixer still consumes
`byte_mixer_output`. Keep the assignment.

---

## MUST KEEP (do not touch)

| object | where | why |
|---|---|---|
| `Lstm::SetInput` + `layer_input_[*][*][0:input_size_]` | `lstm.hpp:78` | residual from PPMD / other byte models |
| Layer ctor aux width = `vocab_size` | `lstm.hpp:27` | deleting this is the aux=0 fatal mistake |
| `ByteMixer::SetInput` / `ByteUpdate` averaging | `byte-mixer.cpp` | fills that residual |
| `lstmex` / `lstmpr` assignment | `predictor.cpp:333-334` | mixer interface; fx2 still uses it |
| `ByteModel::ex` = argmax of remaining `probs_` | `byte-model.cpp:12-18` | definition of `lstmex` |
| PPMD `AddPPMD` | `predictor.cpp:67-68` | `byte_model_` is the SetInput source |
| `fxcm_v26` | `src/models/fxcmv1.cpp` | already the lex gain vs fx2 |
| Article order | `article_reorder.h`, packaged `new_article_order` | shipped permutation |
| `payload_lex` / `r1_reorder_transform.cpp` | hardcoded enwik9 tail | do not rewrite for A1 |
| Constructor cells/layers/horizon/lr/clip | `predictor.cpp:145` | freeze stock geometry |

---

## Replace ONLY the softmax head

Idea: our `BtLstm` (`locked/src/btl-bd.cpp`) — `PBit(c0)=σ(tree_w[c0]·hidden)`,
8 path nodes per byte, 255 internal nodes. **Copy the head, not the object.**

### Fatal drop-in (do not do this)

`work/src/btl-bd.cpp` / `locked/src/btl-bd.cpp` builds every layer with
`auxiliary_input_size = 0` and sets `input_size_ = 0`. It never calls
`SetInput`. Putting **that** class into cmix-lex deletes the residual
byte-mixer. It also swaps 170c/1L/h=128 for **92c/3L/h=50**. E22 (256
zero-aux on our stack) is not a license to ship that into the prize stack.

### Correct splice (cmix-lex tree, outside this repo)

Edit only:

| file | change |
|---|---|
| `src/mixer/lstm.h` | keep `SetInput`; add `tree_w_` (`256 * hsize`), `bit_rows_` / `bit_err_` (`horizon*8`); **do not** remove `output_` (ByteMixer still needs a 256-dist) |
| `src/mixer/lstm.hpp` `Predict` | after `ForwardPass`, fill `output_[epoch]` as products of 8 tree bit-ps (sibling-normalized so leaves sum to 1). **Delete** the `output_size × hidden` exp/softmax loop. Keep the epoch bump. |
| `src/mixer/lstm.hpp` `Perceive` | keep `SetInput` caller; keep layer `BackwardPass`. Replace the `for i in 0..output_size` softmax-error / `output_layer_` SGD with 8 tree-node errors (same as `BtLstm::LearnBit` + the 8-term hidden_error loop). Need the **raw** completed byte for the tree path; compact `byte_map_[byte_]` stays the layer one-hot. Add `SetTargetByte(raw)` or `Perceive(compact, raw)`. |
| `src/mixer/byte-mixer.cpp` | pass `byte_` into that new arg. **Do not** drop `lstm_->SetInput(inputs_)`. |
| `src/mixer/lstm-layer.hpp` | **no change** |
| `src/predictor.cpp` | **no change** to `Lstm(...)` arguments |
| `src/models/byte-model.cpp` | **no change** if `output_` is a 256-dist — `Predict`/`ex` stay softmax-shaped |
| `src/models/fxcmv1.cpp`, PPMD, article order, `r1_reorder_transform.cpp` | **no change** |
| this repo `locked/` | **never** |

Tree is over the **raw 8-bit byte** (c0 = 1..255), then scatter through
`byte_map_` as today. After `ByteModel::ByteUpdate` zeros `!vocab_`,
renormalize `probs_` over the live vocab (one extra sum; cheap).

Do **not** also change 170→200, 1L→3L, or horizon 128→50 in the same patch.

**Freeze for the first A/B vs stock cmix-lex:** `170c / 1L / horizon=128 / lr=0.03 / clip=10` as in `src/predictor.cpp:145`.

fx2 stock is **200c**/1L/h=128. If the A/B is vs stock **fx2-cmix**, freeze
200c instead. Do not widen lex to 200c in the same commit as the head swap.
ByronKnoll cmix is 200c/**2L**/h=**100** — not this experiment.

---

## Why 3 MB fxcm-only cannot measure this

| | 3 MB campaign lock | A1 object |
|---|---|---|
| scoreboard | 517,996 on enwik8.3m DIC | S on enwik9 (or a 10–30 MB **full** stack archive) |
| models | fxcm26 + tree LSTM only | PPMD + match + word + fxcm_v26 + mixer LSTM + SSE |
| LSTM geometry | 92c / 3L / h=50 | 170c / 1L / h=128 (lex) |
| aux / `SetInput` | **0** (E22) | `vocab_size` residual from PPMD |
| alphabet | DIC prefix codes | post-WRT vocab (`byte_map_`) |
| `lstmex` | not wired into a ByteMixer | `ByteModel::ex` over a 256-dist |

E22 already showed a tree head can replace a softmax **on a blind byte
model**. That does not say whether a tree is a good **mixer of other
experts**. The 3 MB instrument cannot see PPMD→LSTM residual, cannot see
WRT vocab, and cannot see `lstmex`. Do not run another 3 MB `cmp` for A1.

---

## Compile / run protocol (Linux only)

This machine is Windows, no WSL. Do not compile cmix-lex here.

```text
# outside this repo, do not commit enwik9 or article-order blobs
git clone https://github.com/blahem/cmix-lex.git
cd cmix-lex
# apply the head-only patch; constructor line stays
#   new Lstm(vocab_size, vocab_size, 170, 1, 128, 0.03, 10)
sudo apt install build-essential libstdc++-14-dev
bash ./install_tools/install_upx.sh
bash ./install_tools/install_clang-17.sh
bash ./build_and_construct_comp.sh    # clang-17, PGO, UPX 5.1.1
```

`makefile` `fast` already compiles `src/mixer/byte-mixer.cpp` and
`src/predictor.cpp` (includes `lstm.h` → `lstm.hpp`). No makefile edit if
the new members stay in those headers.

### Prefix A/B — do **not** use `./cmix -e`

`-e` calls `split4Comp` (enwik9 line cuts), `reorder()` (`NUM_OF_ARTICLES
243425`), PHDA9, then `ReorderEncodedTailFile` which **refuses** any stream
that is not exactly `541126651+45332670`. A 10–30 MB prefix will fail.

Two valid A/B setups (same preprocess on both arms):

**Recommended (codec-only, fairest for the head):**

1. On a Linux box that already has enwik8 (or a 20–30 MB enwik9 prefix):
   `./cmix -c dictionary/english.dic PREFIX stock.out`
2. Same command with the tree binary → `tree.out`
3. `-c` is WRT + full predictor (PPMD, fxcm_v26, LSTM mixer with SetInput).
   Article order / PHDA9 / payload_lex are absent on **both** arms.

**If a full `.ready4cmix` already exists** (enwik8 PHDA9+WRT, or a leftover
enwik9 preprocess): truncate to 20–30 MB and `./cmix -n ready20m out`
on both binaries (`-n` = no second preprocess). Skip `payload_lex` on
prefixes (`FX_PREPARE_ONLY=1` after a patched no-op, or never pass the
side-path). Do **not** download enwik9 for this A/B.

| | |
|---|---|
| corpus | first 20 MB of a WRT stream, or `data/enwik8` via `-c` if that is what is on disk |
| control | stock cmix-lex (170c softmax) |
| treatment | control + tree head only |
| seed / PGO | same `SEED=923`, same `UPDATE_LIMIT=3000`; reuse `pgo_data` or rebuild both with `REUSE_PGO=1` |
| do not | drop in `BtLstm`; change 170c; run enwik9; run 3 MB DIC→fxcm; mix A2 lex into this A/B |

Wall clock: cmix-lex is 43.6 h on 586 MB ready. 20 MB is **hours, not a
day** (not linear — PPM warmup — but nowhere near 43 h). 10 MB is the
impatient floor.

Exact roundtrip on a small file (`-c` / `-d`) before the 20 MB job.

---

## Kill thresholds (bytes)

On a **20 MB** control archive (expect ~3–5 MB compressed after WRT):

| outcome | action |
|---|---|
| treatment **worse by > 500 B** | **KILL** A1 as quality |
| treatment worse by > 0.05% of archive | **KILL** |
| treatment within ±500 B and CPU not ≥ 5% faster | **KILL** as A (quality-neutral, no free hours) |
| treatment within ±500 B and CPU ≥ 5% faster | park as **B**: spend the hours on another expert, not a record claim |
| treatment **better by ≥ 1 KB** | only then consider enwik8-scale, still not enwik9 |

Do not run enwik9 from a 20 MB win. A 1 KB win on 20 MB is ~30–50 KB
linear-scaled to a 586 MB ready stream — still not the 1.1 MB gate.

---

## Honest expected enwik9 ΔS

| effect | expected ΔS | CPU vs ~50 h | P | class |
|---|---|---|---:|---|
| Head quality-neutral; ~16% of LSTM MACs saved (256×H vs 8×H; layer+aux still dominate) | **0 archive** | **−0.5 to −3 h** on lex’s 43.6 h (T=1200, cap 58.3 h). fx2 is 65 h vs 68.2 h (T=1026) — almost no free CPU | 0.40 | **B** unless freed hours buy a new megabyte expert |
| Tree worse as a byte mixer (8 errors vs 256-way softmax credit) | archive **grows 100 KB–1 MB** | similar or slightly faster | 0.30 | kill |
| Tree better because softmax overfits 170c/1L | **50–300 KB**, not 1.1 MB | similar | 0.20 | A-adjacent, **not sufficient alone** |
| Confound 170→200 or drop in 92c/3L | uninterpretable | — | — | do not run |

S1: softmax `output_layer_` is **runtime RAM**
(`128 × vocab × (170+1) × 4 ≈ 22 MB`), not shipped weights. Tree storage is
`256×171×4` plus `horizon×8×171` bit-rows ≈ 1 MB RAM. Compressor **binary**
(S1) moves by a few KB of code after UPX (`cmix-lex` S1 = 459,938;
fx2 S1 = 441,463). Not the 1.1 MB gate.

cmix-lex already sits 35,150 B under the current 1% gate **if accepted**.
A1 cannot be the next 1.1 MB after L moves. It is a head-quality / CPU
option on the stack that actually holds S.

---

## Checklist before anyone types `make`

- [ ] Fork cmix-lex (or fx2), not `locked/`
- [ ] `SetInput` still copies `vocab_size` floats
- [ ] Layer ctor still `aux = input_size_ = vocab_size`
- [ ] `Lstm(vocab, vocab, 170, 1, 128, 0.03, 10)` unchanged (lex)
- [ ] `ByteMixer` still calls `SetInput` then `Perceive`
- [ ] `probs_[256]` still filled; `lstmex = ex` still assigned
- [ ] PPMD / fxcm_v26 / article order / payload_lex untouched
- [ ] No `BtLstm` object, no 92c, no `auxiliary_input_size = 0`
