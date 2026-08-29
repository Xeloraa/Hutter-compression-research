# A1 — tree-head splice patch plan (cmix-lex / fx2-cmix)

One-pass operator doc. Fork **[blahem/cmix-lex](https://github.com/blahem/cmix-lex)** (preferred; already has `fxcm_v26` + shipped article order + `payload_lex`). Fallback: **[kaitz/fx2-cmix](https://github.com/kaitz/fx2-cmix)**. Clone **outside** this repo. Do not edit `locked/`. Do not vendor enwik9 or article-order blobs.

---

## 1. Exact files / functions — replace 256-softmax head ONLY

| file | function / region | action |
|---|---|---|
| `src/mixer/lstm.h` | class `Lstm` | Drop `output_layer_` (`horizon × output_size × hidden`). Add `tree_w_` (`256 × hsize`, `hsize = num_cells×num_layers+1`), `bit_rows_`, `bit_node_`, `bit_err_`, `bit_idx_`, `cur_epoch_`. Declare `float PBit(int c0) const`, `int ExpectedByte(int c0) const`, `void LearnBit(int c0, int bit, float p)`. **Keep** `SetInput`, constructor signature, `Predict`, `Perceive`. |
| `src/mixer/lstm.hpp` | `Lstm::Lstm(...)` | Unchanged ctor args. Layers still `layers_.emplace_back(layer_input_[0][i].size() + output_size, input_size_, output_size_, num_cells, horizon, ...)`. Init `tree_w_` to 0 (sigmoid→0.5). **Do not** change `input_size_`, `num_cells_`, `num_layers_`, `horizon_`. |
| `src/mixer/lstm.hpp` | `Lstm::SetInput` | **No change.** Still copies `vocab_size` residual into `layer_input_[epoch_][i][0:input_size_]`. |
| `src/mixer/lstm.hpp` | `Lstm::Predict` | Keep layer forward loop (hidden → next layer). **Delete** the `output_size_` softmax loop (`exp`, normalize). Replace with: (a) fill `output_[epoch_][0..255]` by walking the binary tree — for each byte `b`, multiply sibling-normalized bit-ps along path `1→b`; (b) renormalize `output_[epoch_]` to sum 1; (c) return `output_[epoch]`. Epoch advance unchanged. |
| `src/mixer/lstm.hpp` | `Lstm::Perceive` | Keep `input_history_` / BPTT epoch loop and `layers_[layer].BackwardPass(...)`. **Replace** the inner loop `for (i < output_size_) { error on output_layer_[epoch][i] }` with **8** tree nodes: for each bit slot, `LearnBit(c0, bit, p)` then propagate `bit_rows_[slot] * bit_err_[slot]` into `hidden_error_` (same pattern as `work/src/btl-bd.cpp` `Perceive`, lines 112–119). **Delete** the SGD block that updates `output_layer_[epoch_][i] -= lr * error * hidden_`. |
| `src/mixer/lstm-layer.h` / `lstm-layer.cpp` | `LstmLayer` | **No change.** `auxiliary_input_size = input_size_` (vocab-sized aux) stays wired. |
| `src/mixer/byte-mixer.cpp` | `ByteMixer::ByteUpdate` | **No change.** Still `inputs_ *= 2/num_models_`; `lstm_->SetInput(inputs_)`; `lstm_->Perceive(byte_map_[byte_])`; scatter 256 probs into `probs_`. |
| `src/mixer/byte-mixer.h` | `ByteMixer` | **No change.** |
| `src/models/byte-model.cpp` | `ByteModel::Predict` | **No change.** `ex` stays argmax of `probs_` → feeds global `lstmex`. |
| `src/predictor.cpp` | `Predictor::AddMixers` | **No change** to `new Lstm(vocab_size, vocab_size, 200, 1, 128, 0.03, 10)`. |
| `src/predictor.cpp` | `Predictor::Perceive` | **No change** to PPMD `byte_model_->BytePredict()` → `byte_mixer_->SetInput(j,p[j])` loop or `lstmpr`/`lstmex` globals. |
| PHDA9 / WRT / `payload_lex` / `fxcm_v26` / article order | all transform + fxcm sources | **Touch nothing.** |

**Optional (same PR, head-only):** implement `Lstm::ExpectedByte(int c0)` mirroring `BtLstm::ExpectedByte` for debugging; production `lstmex` still comes from `ByteModel::ex` on the 256-wide `probs_` — no predictor glue change required.

**Reference tree math** (adapt, do not paste class): `work/src/btl-bd.cpp` `PBit`, `LearnBit`, tree backward in `Perceive`. Upstream softmax to delete: fx2 `lstm.hpp` `Predict` lines 95–103 and `Perceive` lines 79–86, 99–104.

---

## 2. Must keep (non-negotiable)

| piece | why |
|---|---|
| `SetInput` + `ByteMixer::ByteUpdate` averaging | LSTM is a **residual byte mixer** fed by PPMD/other stretched ps, not a standalone one-hot model. |
| Mixer `lstmex` / `lstmpr` | `Predictor::Perceive` sets `lstmex=byte_mixer_->ex`, `lstmpr=Discretize(byte_mixer_output)`; fxcm and SSE contexts consume these. |
| PPMD `byte_model_` | Still the source of the 256-wide vector passed into `byte_mixer_->SetInput`. |
| Shipped article order + PHDA9 + WRT + `payload_lex` | cmix-lex record stack; any A/B must use **their** preprocess, not DIC→fxcm26. |
| `fxcm_v26` | Already inside cmix-lex; do not regress to paq8hp fxcm or our `fxcm26_bd92`. |

---

## 3. Must NOT paste our `BtLstm`

`work/src/btl-bd.cpp` is the **wrong object** for this splice:

```27:29:work/src/btl-bd.cpp
    layers_.push_back(std::unique_ptr<LstmLayer>(new LstmLayer(
        layer_input_[0][i].size() + vocab_, 0, vocab_,
        num_cells, horizon, gradient_clip, learning_rate)));
```

- `auxiliary_input_size = 0` — deletes the cmix residual path.
- `BtLstm(256, 92, 3, 50, 0.03, 10)` — wrong width, depth, horizon.
- No `SetInput` API.

**Correct approach:** edit **their** `Lstm` in place; port only the **tree head** math (`PBit` / `LearnBit` / 8-node backward) onto their hidden layout (`200×1+1 = 201`).

---

## 4. Frozen hyperparameters (first A/B)

| param | value | do not sweep |
|---|---:|---|
| cells | 200 | — |
| layers | 1 | — |
| horizon | 128 | — |
| learning_rate | 0.03 | — |
| gradient_clip | 10 | — |
| ctor | `Lstm(vocab_size, vocab_size, 200, 1, 128, 0.03, 10)` | — |
| aux width | `vocab_size` (via `SetInput`) | — |

Confounding width/depth/horizon with head type invalidates the A/B.

---

## 5. Linux cheap A/B (10–30 MB full stack)

**Host:** Linux (same class as judging). This Windows workspace is not the measurement path.

**Baseline:** stock cmix-lex built with `./build_and_construct_comp.sh`.

**Candidate:** same fork, tree-head patch above only.

**Input:** first **10 MB** then **30 MB** of **enwik9** (or enwik8 if enwik9 unavailable) through **full** cmix-lex preprocess (PHDA9 → WRT → `payload_lex` → cmix). Not our 3 MB DIC→fxcm26 slice.

**Metric:** total archive size **S** (compressor + preprocessed payload), same as prize scoreboard.

| outcome on 30 MB | action |
|---|---|
| ΔS ≤ **−50 KB** (candidate larger) | **Kill A1.** Do not run enwik9. |
| **0 < ΔS < 50 KB** | **Kill as insufficient.** Tree head alone will not close 1.1 MB; stop before enwik9. |
| ΔS ≥ **50 KB** | Promising for a **full enwik9** confirm only; still expect sub-megabyte total (§6). |

10 MB run is a smoke test (build, correctness, decompress EXACT); **30 MB is the kill gate.**

---

## 6. Honest full enwik9 ΔS expectation

| scenario | expected ΔS vs stock cmix-lex |
|---|---:|
| Tree head neutral (CPU only) | **0** archive; maybe 1–3 h CPU freed for another expert |
| Tree head worse as byte mixer | **+50 KB … +1 MB** (kill) |
| Tree head better (softmax overfit on 200c/1L) | **−50 KB … −300 KB** |
| Prize gate gap | **−1,107,931 B** to beat current 1% record |

Tree head replacing softmax saves ~**248×201 ≈ 50K** MACs/byte on the output layer and shrinks S1 slightly; it does **not** remove `payload_lex`, PHDA9 tail mass, or mixer-stack gap. Claiming **−1.1 MB** from A1 alone is dishonest. Tens to low hundreds of KB is the honest band if the head helps at all.

---

## 7. Why 3 MB fxcm-only cannot measure A1

| 3 MB path | A1 path |
|---|---|
| DIC → `fxcm26_bd92` standalone | PHDA9 + WRT + article order + `payload_lex` + full cmix ensemble |
| One model: fxcm + our `BtLstm` | PPMD + match + indirect + word + **LSTM-as-mixer** + SSE + 20+ mixer slots |
| `BtLstm` aux=0, 92c/3L/h=50 | 200c/1L/h=128 + `SetInput(vocab)` from PPMD average |
| Measures forget bias, tree on isolated net | Measures whether tree head helps **inside the record stack** |
| Locked floor **517,996** | Official S **~109–111 MB** |

A −190 B win on 3 MB fxcm (E30e forget bias) is Class **C** and says nothing about whether tree+`SetInput` beats softmax inside cmix-lex. The LSTM expert is ~1/N of the mixer input; PPMD feeds it; `lstmex` feeds fxcm contexts — none of that exists in fxcm-only. **Any 3 MB `cmp` is the wrong experiment for A1.**

---

## Build checklist

1. Clone cmix-lex outside repo.
2. Patch `lstm.h` / `lstm.hpp` only (§1).
3. `./build_and_construct_comp.sh` — must compile clean.
4. Decompress EXACT on 1 MB smoke.
5. 10 MB → 30 MB full-stack A/B on Linux.
6. Record ΔS, CPU, MD5 in a local log (do not commit enwik blobs).

See also: `INTEGRATION.md`, `PRIZE.md`, `STRATEGY.md`.
