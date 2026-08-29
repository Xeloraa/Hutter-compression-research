# A-path: tree-head LSTM inside fx2-cmix / cmix-lex

Official target is **S on enwik9**, not 517,996. Verified 2026-08-29:

| scoreboard | S | status |
|---|---:|---|
| fx2-cmix (paid record) | **110,793,128** | official (Orav & Knoll, 3 Sep 2024) |
| next paid 1% gate | **109,685,197** | need **−1,107,931** vs current L |
| cmix-lex (Marcouch) | **109,650,047** | public candidate; **not** the paid record until accepted |

cmix-lex is already **35,150 B under the current 1% gate** if the committee accepts it. After that, L moves and another ~1.1 MB is required. A 3 MB fxcm-only tweak is not progress toward either number.

Sources (do not vendor into this repo): [kaitz/fx2-cmix](https://github.com/kaitz/fx2-cmix), [blahem/cmix-lex](https://github.com/blahem/cmix-lex).

---

## Why this tree cannot take the prize alone

fx2-cmix **replaced paq8hp with fxcm** and kept cmix’s PPMD, match/indirect/word, SSE, shipped article order, and a **softmax LSTM used as a byte mixer**. cmix-lex adds `fxcm_v26` inside that stack plus `payload_lex` on a 45 MB PHDA9 tail.

This campaign’s compressor is **fxcm26 + tree-head BD-LSTM only**. That is one expert of the record stack. Mixer slots, forget bias, and a 14 KB DIC pointer cannot close 1.1 MB on enwik9.

---

## What fx2’s LSTM actually is

Constructor (`src/predictor.cpp` / `ByteMixer`):

```text
Lstm(vocab_size, vocab_size, 200, 1, 128, 0.03, 10)
```

200 cells, **1 layer**, horizon **128**, output = softmax over vocab.

`Lstm::SetInput` copies a `vocab_size` residual vector into `layer_input_[epoch][i][0:input_size]`. `ByteMixer::ByteUpdate` averages other models into that vector, then `Perceive`. The net is a **byte mixer with auxiliary inputs**, not a blind one-hot byte model.

`Predict` does a dense `output_size × hidden` softmax (~256×201 MACs/byte). Our tree head is 8×hidden.

`lstmex` in fx2 is the LSTM expected byte (cmix `ByteModel::ex` = argmax of remaining softmax). Our `BtLstm::ExpectedByte` is the greedy tree walk — same role **if** the LSTM still outputs a byte distribution.

---

## Fatal mistake: drop-in of *our* BtLstm

`work/src/btl-bd.cpp` builds every layer with `auxiliary_input_size = 0` and never calls `SetInput`. Putting **that** object into fx2-cmix would **delete** the residual byte-mixer path. E22 (256 zero-aux) is not a license to ship aux=0 into the prize stack.

**Correct splice:** keep `SetInput` and `layer_input` layout from fx2 `lstm.hpp`. Replace only the **output head** (softmax `output_layer_` / `Predict` loop) with a binary tree over the same hidden state. `ByteMixer` still needs 256 probabilities: form them as products of tree bit-ps (sibling-normalized).

Do **not** also swap 200c/1L/h=128 for 92c/3L/h=50 on the first A/B. That confounds head, width, depth, and horizon.

---

## File-level plan (fork fx2-cmix or cmix-lex; do not edit `locked/`)

| step | where | change |
|---|---|---|
| 1 | `src/mixer/lstm.hpp` `Predict` / `Perceive` | tree head; keep `SetInput` |
| 2 | `src/mixer/lstm.h` | add `ExpectedByte(c0)` for `lstmex` |
| 3 | `src/mixer/byte-mixer.cpp` | consume tree byte-distribution; no API change |
| 4 | fxcm `lstmex` / `lstmpr` glue | already in fx2; point at tree MAP + stretch(p_bit) |
| 5 | build | `./build_and_construct_comp.sh` on Linux (this Windows box is not the judging path) |

S1: tree weights vs softmax `vocab × hidden` — similar or smaller. Not the 1.1 MB.

---

## Expected full-enwik9 gain (honest)

| effect | expected S | P | class |
|---|---|---|---|
| Tree head quality-neutral, CPU saved | 0 archive; maybe 1–3 h toward another model | 0.4 | **B** unless freed hours buy a new megabyte expert |
| Tree head worse as a byte mixer | archive **grows** (100 KB–1 MB possible) | 0.3 | kill |
| Tree head better because softmax overfits 200c/1L | 50–300 KB, not 1.1 MB | 0.2 | A-adjacent, not sufficient alone |
| Keep softmax; spend effort on **another PHDA9/payload transform** | **≤150 KB** on every analog visible in raw enwik8; r1 already taken | 0.10 | **killed as A** at cheap filter (`A2.md`); leftover hole = Linux post-WRT tail autopsy |

fx2 decompress is **65 h vs 68 h cap** (T=1026). Almost no free CPU. cmix-lex reports **43.6 h CPU vs 58 h cap** (T=1200) and **already includes fxcm_v26**.

**Base fork should be cmix-lex** if the goal is a paid record after lex is accepted. If lex is rejected, fork fx2-cmix; the 1.1 MB hole is still mostly `payload_lex` + v26, not our 92-cell net.

---

## Cheap falsification (Class B, before any enwik9 claim)

1. Clone fx2-cmix **outside** this repo. Do not commit enwik9 or restricted article-order blobs.
2. Swap **only** the softmax head for a tree; freeze 200c/1L/h=128/`SetInput`.
3. Compress a **10–30 MB** enwik prefix through their **full** preprocess (not our DIC→fxcm26).
4. Kill if archive is worse by more than S1 savings. Do not run enwik9.
5. Only then consider spending freed CPU on a second transform.

This machine is Windows without WSL. The B-test is a Linux job. Until then, do not start another 3 MB `cmp`.
