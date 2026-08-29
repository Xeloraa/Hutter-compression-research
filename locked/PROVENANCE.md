# Locked candidate — provenance and reproduction

## Configuration (LOCKED)
    model    : fxcm v26 (PLAINTEXT undefined) + binary-tree-head block-diagonal LSTM
    cells    : 92
    layers   : 3
    blocks   : 4        (block-diagonal recurrent weights)
    horizon  : 50
    lr       : 0.03
    initMul  : 0.5
    mem scale: MEMDIV 8 (fxcm context maps scaled 1/8 to fit a 4 GB dev box)

## Verified result (3 MB enwik8 prefix, real DIC -> fxcm pipeline)
    baseline fxcm26      : 521,198
    candidate            : 517,996   (+0.614%)
    compression time     : 416 s
    decompression time   : 412 s
    peak RSS             : 2.21 GB
    roundtrip            : BYTE-EXACT (both codec and full pipeline)
    enwik9 projection     : 229 us/DIC byte -> 38.5 h  (cap 42.48 h, margin 3.9 h)

## Upstream sources
- `kaitz/fxcm` (GPL) — fxcm.cpp v26. Four patches required to build on Linux:
  1. comment out `#include <mem.h>`
  2. comment out `#include <windows.h>`
  3. add `#include <stdint.h>`, `<string.h>`, `<stdlib.h>`
  4. compile with `-DUNIX`
  Plus: scale the 35 `.Init(N*4096*4096,...)` context-map args by `/MEMDIV`.
- `byronknoll/cmix` (GPL) — `src/preprocess/dictionary.{cpp,h}`, `dictionary/english.dic`
  (DIC preprocessor), and `src/mixer/lstm-layer.{cpp,h}`, `sigmoid.{cpp,h}`
  (LstmLayer: Adam + layer normalisation + exact BPTT, used verbatim).

## Local contributions in this tree
1. `btl-bd.{cpp,h}` — BtLstm: cmix's Lstm with the 256-way softmax head replaced
   by a BINARY-TREE head indexed by fxcm's `c0`. Exact factorisation
   P(byte)=prod_k P(bit_k|prefix); output cost 8*H instead of 256*H. BPTT
   exactness preserved by storing only the 8 weight rows touched per timestep
   (horizon*8*H = 102 KB) instead of cmix's full per-epoch output-layer copy.
2. `lstm-layer-bd.cpp` — three changes vs upstream:
   - `auxiliary_input_size = 0`: the 256-wide aux block is never populated in
     this integration, so every gate was multiplying 256 zeros per cell (3.9x).
   - block-diagonal recurrent weights with a fast path that SKIPS off-block
     indices in ForwardPass and gradient accumulation (dense inter-layer path
     kept). Masked once in the constructor; off-block gradients are exactly
     zero so Adam never moves those weights.
   - `g_initMul` scaling on the Xavier init (0.5 optimal; larger is worse).
3. `fxcm26_bd92.cpp` — fxcm26 with the LSTM wired into mixer input slots
   544/545 (`ncount` 544 -> 560; N must be a multiple of 16 because
   `dot_product` asserts `n == ((n+15) & -16)`). Writes the array directly to
   bypass `AddPrediction`, leaving `model_predictions1`/`mxA2` untouched.

## Reproduce
    ./BUILD.sh                 # -> ./dicprep ./cmp  (+ english.dic in CWD)
    ./VERIFY.sh <enwik-slice>  # full byte-exact roundtrip + timings

## CRITICAL runtime requirement
`./cmp` calls `fopen("english.dic")` on the CURRENT WORKING DIRECTORY.
It SEGFAULTS if run from a directory without it. BUILD.sh copies it to the
candidate root for this reason.

## Caveat on the result
The baseline is fxcm ALONE, roughly 10% behind the current record holder
cmix-lex, and cmix already ships an LSTM. This is a verified improvement over a
measurable baseline under the real constraints — it is NOT a Hutter Prize record.
Timings are on a 2.1 GHz Xeon; the 42.48 h cap is 70000/T hours where T is the
judging machine's Geekbench5 score, so the projection must be re-measured there.
