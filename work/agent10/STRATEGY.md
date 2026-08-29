# Campaign strategy (reset 2026-08-29)

**Win condition:** verified **S = compressor + archive9 on enwik9** under official rules that beats the paid record (today **110,793,128**) and then the moving 1% gate.

**Not the win condition:** any 3 MB DIC→fxcm26 number, including 517,996.

## Classification

- **A** — could remove megabytes on enwik9 or unlock a new mechanism of that weight.
- **B** — cheap test that characterizes or kills an A idea.
- **C** — local micro-opt. Run only if it credibly feeds A.

## 3 MB forget-bias series — STOPPED

- E30d forget=1 MinGW: archive **518,095**, compress 2122 s, decompress 1610 s, codec **EXACT**. Class **C**. Not comparable to Linux lock 517,996.
- E30e forget=0 MinGW: archive **517,905**, compress 886 s, decompress 817 s, codec **EXACT**. **−190 B** vs same-compiler E30d (passes the old ≥100 B MinGW gate). Still Class **C**. Do not replace `locked/`. Do not start E32/E35/E41.

## Killed this turn

**E41 OOV pointer** is Class **C**: exact −14,407 DIC bytes, but zlib9 **loses 1,702** and lzma6 **loses 1,092** vs vanilla DIC. A transform generic compressors reject will not move enwik9 S by megabytes. Do not start `tools/run_e41_oovptr.ps1`.

**3 MB exact duplicates** (Class B for A4): extra page-body copies **0.037%** of file; extra long-line copies **0.643%**. Wrong scale for identity. Measure PHDA9 tail at enwik9, not stubs.

## Work now

**A2 is dead.** Cheap filter + PHDA9-lite (E43/E44) killed second-lex / regime-2 as megabyte mechanisms (`A2.md`). Lang/r2 lzma is sublinear 30→100 MB; leftover tail autopsy is diagnostic only, not a prize path.

**Next Linux job: A1** — tree head replacing 256-softmax **only**, keeping `SetInput`, PPMD glue, `lstmex`, article order, and `fxcm_v26` inside cmix-lex. Frozen 200c/1L/h=128. Operator doc: `A1_PATCH.md`. Kill gate: 30 MB full-stack A/B vs stock cmix-lex; need **≥50 KB** ΔS win, else kill (regression **≥50 KB** also kill).

Do not start E32, E35, E36, width sweeps, E41 3 MB fxcm, or paste `work/src/btl-bd.cpp` aux=0 into the prize stack.

---

## A3 — LSTM input symbol from fxcm lastCW on codewords (new)

**Hypothesis.** E19 died putting lastCW buckets into **mixer slots** (+0.024%) because fxcm already exposes word types there. The cmix LSTM still sees only the DIC byte one-hot (`Perceive(c0&255)`) and never the codeword identity `lastCW ∈ [0,44515)`. On bytes with `c≥0x80`, set `input_symbol = 128 + (lastCW % 128)`; literals keep `c0`. That injects word identity at the recurrent input without touching PHDA9, `payload_lex`, or mixer topology — a different channel than A2's tail reorder.

**Kill test (Linux, after A1 frozen or in parallel on stock softmax baseline).** Patch `LstmLayer::ForwardPass` / `BackwardPass` input_symbol only; keep A1 tree head + `SetInput` unchanged. Run 30 MB cmix-lex full preprocess. Kill if ΔS ≤ +30 KB vs the A1-frozen (or stock-softmax) baseline, or if a **shuffled-lastCW** control (permute codeword IDs, same cardinality) matches live within 10 KB — which would prove extra capacity, not information.
